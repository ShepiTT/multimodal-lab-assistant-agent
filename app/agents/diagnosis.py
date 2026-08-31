"""故障诊断多轮状态机。

不再一次性输出大量建议，而是按固定流程逐步推进：

    confirm_device   确认设备型号
        ↓
    collect_symptoms 收集故障现象
        ↓
    safety_check     安全风险检查（硬规则，代码判定）
        ↓
    step             每次只给一个排查步骤
        ↕ （用户反馈 → 更新诊断分支，最多 MAX_STEPS 轮）
    report           输出诊断报告

状态转移由代码控制；大模型只负责在各状态下生成话术/排查步骤/报告
（generator 可注入，测试时用 stub）。会话状态持久化为 JSON 文件。
"""
import json
import uuid
from pathlib import Path
from typing import Callable, Dict, List, Optional

from ..config import DATA_DIR, timestamp
from ..observability import get_logger
from ..security.safety_rules import assess_risk, build_safety_preamble
from ..security.validation import validate_session_id

logger = get_logger()

SESSIONS_DIR = DATA_DIR / "diagnosis_sessions"

STATE_CONFIRM_DEVICE = "confirm_device"
STATE_COLLECT_SYMPTOMS = "collect_symptoms"
STATE_STEP = "step"
STATE_REPORT = "report"
STATE_DONE = "done"

MAX_STEPS = 5

# 各状态下发给大模型的指令模板
_PROMPTS = {
    STATE_COLLECT_SYMPTOMS: (
        "你是实验室故障诊断助手。用户的设备是：{device}。\n"
        "请用一段简短的话，引导用户描述故障现象（何时出现、报错信息、异常表现、"
        "已尝试过什么）。只提问，不要给出任何诊断结论。"
    ),
    STATE_STEP: (
        "你是实验室故障诊断助手。\n"
        "设备：{device}\n故障现象：{symptoms}\n"
        "已执行的排查步骤与结果：\n{history}\n"
        "请给出下一个【单独一步】最有价值的排查步骤（只给一步，说明怎么做、"
        "预期观察什么），并请用户执行后反馈结果。不要一次给多步。"
    ),
    STATE_REPORT: (
        "你是实验室故障诊断助手。请根据以下完整排查过程输出诊断报告：\n"
        "设备：{device}\n故障现象：{symptoms}\n"
        "排查过程：\n{history}\n"
        "报告格式：1) 最可能原因（按可能性排序）；2) 建议的修复方案；"
        "3) 若需教师/专业人员介入，明确说明。"
    ),
}


def _default_generator(prompt: str, provider_id=None, model_id=None) -> str:
    """默认用统一模型入口生成话术。"""
    from .. import runtime
    if runtime.call_model is None:
        raise RuntimeError("llm_runner 未加载，无法生成诊断话术")
    return runtime.call_model(
        message=prompt, provider_id=provider_id, model_id=model_id,
        system_prompt="你是严谨的实验室故障诊断助手，回答简洁、一次只推进一步。",
    )


class DiagnosisSession:
    """单个诊断会话的状态容器 + 状态机逻辑。"""

    def __init__(self, session_id: str, data: Dict = None):
        self.session_id = session_id
        d = data or {}
        self.state: str = d.get("state", STATE_CONFIRM_DEVICE)
        self.device: str = d.get("device", "")
        self.symptoms: str = d.get("symptoms", "")
        self.steps: List[Dict] = d.get("steps", [])  # [{'instruction', 'feedback'}]
        self.risk: Dict = d.get("risk", {})
        self.created_at: str = d.get("created_at", timestamp())

    # ---- 持久化 ----

    @staticmethod
    def _file(session_id: str) -> Path:
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        return SESSIONS_DIR / f"{session_id}.json"

    @classmethod
    def load(cls, session_id: str) -> Optional["DiagnosisSession"]:
        if not validate_session_id(session_id):
            raise ValueError("非法的 session_id")
        f = cls._file(session_id)
        if not f.exists():
            return None
        with f.open(encoding="utf-8") as fh:
            return cls(session_id, json.load(fh))

    def save(self):
        data = {
            "state": self.state,
            "device": self.device,
            "symptoms": self.symptoms,
            "steps": self.steps,
            "risk": self.risk,
            "created_at": self.created_at,
            "updated_at": timestamp(),
        }
        with self._file(self.session_id).open("w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)

    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "state": self.state,
            "device": self.device,
            "symptoms": self.symptoms,
            "steps": self.steps,
            "risk": self.risk,
        }

    # ---- 状态机 ----

    def _history_text(self) -> str:
        if not self.steps:
            return "（尚无）"
        lines = []
        for i, s in enumerate(self.steps, 1):
            lines.append(f"步骤{i}: {s['instruction']}")
            lines.append(f"  用户反馈: {s.get('feedback') or '（待反馈）'}")
        return "\n".join(lines)

    def advance(self, user_message: str, generator: Callable = None,
                provider_id=None, model_id=None) -> Dict:
        """输入用户消息，推进一步状态机，返回 {'state', 'message', ...}。"""
        gen = generator or _default_generator
        user_message = (user_message or "").strip()

        if self.state == STATE_CONFIRM_DEVICE:
            if not user_message:
                return self._reply("请先告诉我出现故障的设备名称/型号（例如：示波器 DS1054Z）。")
            self.device = user_message
            self.state = STATE_COLLECT_SYMPTOMS
            msg = gen(_PROMPTS[STATE_COLLECT_SYMPTOMS].format(device=self.device),
                      provider_id, model_id)
            return self._reply(msg)

        if self.state == STATE_COLLECT_SYMPTOMS:
            if not user_message:
                return self._reply("请描述一下故障现象（何时出现、报错信息、异常表现）。")
            self.symptoms = user_message

            # 安全风险检查：硬规则判定，不依赖大模型
            self.risk = assess_risk(f"{self.device} {self.symptoms}")
            preamble = build_safety_preamble(self.risk)

            self.state = STATE_STEP
            step_msg = gen(_PROMPTS[STATE_STEP].format(
                device=self.device, symptoms=self.symptoms,
                history=self._history_text()), provider_id, model_id)
            self.steps.append({"instruction": step_msg, "feedback": None})
            return self._reply(preamble + step_msg)

        if self.state == STATE_STEP:
            # 记录上一步反馈
            if self.steps and self.steps[-1].get("feedback") is None:
                self.steps[-1]["feedback"] = user_message

            # 达到步数上限 → 输出报告
            if len(self.steps) >= MAX_STEPS or self._user_wants_report(user_message):
                return self._make_report(gen, provider_id, model_id)

            step_msg = gen(_PROMPTS[STATE_STEP].format(
                device=self.device, symptoms=self.symptoms,
                history=self._history_text()), provider_id, model_id)
            self.steps.append({"instruction": step_msg, "feedback": None})
            return self._reply(step_msg)

        if self.state in (STATE_REPORT, STATE_DONE):
            return self._reply("本次诊断已结束。如需新的诊断请重新开始会话。")

        raise RuntimeError(f"未知状态: {self.state}")

    @staticmethod
    def _user_wants_report(message: str) -> bool:
        return any(kw in (message or "") for kw in ("出报告", "生成报告", "总结", "结束诊断", "解决了"))

    def _make_report(self, gen, provider_id, model_id) -> Dict:
        report = gen(_PROMPTS[STATE_REPORT].format(
            device=self.device, symptoms=self.symptoms,
            history=self._history_text()), provider_id, model_id)
        self.state = STATE_DONE
        return self._reply(report, extra={"report": True})

    def _reply(self, message: str, extra: Dict = None) -> Dict:
        self.save()
        result = {"session_id": self.session_id, "state": self.state, "message": message}
        if self.risk.get("level") in ("high", "medium"):
            result["risk"] = self.risk
        if extra:
            result.update(extra)
        return result


def start_session() -> DiagnosisSession:
    session = DiagnosisSession(f"diag_{uuid.uuid4().hex[:16]}")
    session.save()
    return session
