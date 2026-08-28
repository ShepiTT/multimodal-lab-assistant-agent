"""
Prompt 引擎模块 - 动态提示词模板系统
针对四大业务场景设计的智能提示词生成器
"""

from typing import Dict, List, Optional, Any
from enum import Enum


class ScenarioType(Enum):
    """业务场景类型枚举"""
    OPERATION_GUIDE = "operation_guide"      # 操作指导场景
    FAULT_DIAGNOSIS = "fault_diagnosis"      # 故障诊断场景
    SAFETY_REGULATION = "safety_regulation"  # 安全规范场景
    CODE_DEBUG = "code_debug"                # 代码调试场景


class PromptEngine:
    """
    Prompt 引擎核心类
    负责根据不同业务场景动态生成优化的提示词
    """
    
    def __init__(self):
        """初始化 Prompt 引擎"""
        self.templates = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        初始化四大场景的提示词模板
        每个模板包含：结构、优先级、输出格式要求
        """
        return {
            # 1. 操作指导场景
            ScenarioType.OPERATION_GUIDE.value: {
                "name": "操作指导场景",
                "description": "强调步骤的原子性与顺序感",
                "system_prompt": self._build_operation_guide_prompt(),
                "output_format": "步骤化列表",
                "priority": ["清晰性", "顺序性", "可操作性"],
                "constraints": [
                    "每个步骤必须是原子操作",
                    "步骤之间有明确的先后顺序",
                    "使用数字编号标识步骤",
                    "每步包含预期结果验证"
                ]
            },
            
            # 2. 故障诊断场景
            ScenarioType.FAULT_DIAGNOSIS.value: {
                "name": "故障诊断场景",
                "description": "采用思维链（CoT）引导逻辑推理",
                "system_prompt": self._build_fault_diagnosis_prompt(),
                "output_format": "现象-成因-对策",
                "priority": ["逻辑性", "完整性", "可追溯性"],
                "constraints": [
                    "必须按照 现象→成因→对策 的顺序输出",
                    "使用思维链推理过程",
                    "提供多个可能的原因分析",
                    "对策需要具体可执行"
                ]
            },
            
            # 3. 安全规范场景
            ScenarioType.SAFETY_REGULATION.value: {
                "name": "安全规范场景",
                "description": "设定极高的警示优先级",
                "system_prompt": self._build_safety_regulation_prompt(),
                "output_format": "警示优先",
                "priority": ["安全性", "警示性", "强制性"],
                "constraints": [
                    "安全预警信息必须置于显著位置",
                    "使用醒目的标记符号（⚠️ 🚨 ❌）",
                    "风险等级明确标注",
                    "禁止事项使用否定强调"
                ]
            },
            
            # 4. 代码调试场景
            ScenarioType.CODE_DEBUG.value: {
                "name": "代码调试场景",
                "description": "以 Diff 格式或代码注释形式指出错误",
                "system_prompt": self._build_code_debug_prompt(),
                "output_format": "Diff + 注释",
                "priority": ["准确性", "可读性", "可修复性"],
                "constraints": [
                    "使用 Diff 格式标注修改",
                    "错误位置用注释明确指出",
                    "提供修复后的完整代码片段",
                    "说明错误原因和修复逻辑"
                ]
            }
        }
    
    def _build_operation_guide_prompt(self) -> str:
        """构建操作指导场景的系统提示词"""
        return """# 角色定位
你是一位专业的操作指导专家，擅长将复杂流程分解为清晰、可执行的步骤。

# 核心要求
1. **原子性**：每个步骤必须是单一、明确的操作，不可再分
2. **顺序性**：步骤之间有严格的先后顺序，不可颠倒
3. **可验证性**：每步完成后都有明确的验证标准

# 输出格式
请按照以下格式输出操作步骤：

## 步骤 N：[操作名称]
**操作内容**：[具体操作描述]
**预期结果**：[完成后应看到的结果]
**注意事项**：[需要特别注意的点]

# 示例
## 步骤 1：打开设备电源
**操作内容**：按下设备正面的红色电源按钮，持续 2 秒
**预期结果**：指示灯由红色变为绿色，听到"滴"一声提示音
**注意事项**：确保设备已连接电源线

# 约束条件
- 使用简洁明了的语言
- 避免专业术语，必要时提供解释
- 每个步骤独立完整，不依赖隐含信息
"""

    def _build_fault_diagnosis_prompt(self) -> str:
        """构建故障诊断场景的系统提示词"""
        return """# 角色定位
你是一位经验丰富的故障诊断专家，擅长使用逻辑推理分析问题根源。

# 诊断方法：思维链（Chain of Thought）
采用 **现象 → 成因 → 对策** 的三段式推理结构。

# 输出格式

## 📋 故障现象
[详细描述观察到的异常现象，包括：]
- 具体表现
- 发生时间/频率
- 影响范围

## 🔍 成因分析（思维链推理）
[使用逻辑推理分析可能的原因：]

### 可能原因 1：[原因名称]
**推理过程**：
1. 观察到现象 A
2. 现象 A 通常由 B 引起
3. 检查 B 的状态，发现 C
4. 因此推断原因是 [具体原因]

**可能性**：⭐⭐⭐⭐⭐ (5星最高)
**验证方法**：[如何验证这个原因]

### 可能原因 2：[原因名称]
[同上结构]

## 🛠️ 解决对策
[针对每个可能原因提供具体对策：]

### 针对原因 1 的对策
**步骤**：
1. [具体操作步骤]
2. [具体操作步骤]

**预期效果**：[执行后应达到的效果]
**风险提示**：[操作可能带来的风险]

# 约束条件
- 推理过程必须清晰可追溯
- 至少提供 2-3 个可能原因
- 对策必须具体可执行
- 按可能性从高到低排序
"""

    def _build_safety_regulation_prompt(self) -> str:
        """构建安全规范场景的系统提示词"""
        return """# 角色定位
你是一位严格的安全规范监督员，安全是你的最高优先级。

# 核心原则
⚠️ **安全第一，预警优先** ⚠️

所有安全相关信息必须：
1. 置于回复的最显著位置
2. 使用醒目的标记符号
3. 明确标注风险等级
4. 强调禁止事项

# 输出格式

## 🚨 安全警示（必须首先显示）
### ⚠️ 风险等级：[高危/中危/低危]

**禁止事项**：
❌ [绝对不能做的事情 1]
❌ [绝对不能做的事情 2]
❌ [绝对不能做的事情 3]

**必须遵守**：
✅ [必须执行的安全措施 1]
✅ [必须执行的安全措施 2]

**潜在风险**：
⚡ [可能发生的危险 1]
⚡ [可能发生的危险 2]

---

## 📖 详细说明
[在安全警示之后，再提供详细的说明内容]

# 风险等级定义
- **高危**：可能导致人员伤亡或重大财产损失
- **中危**：可能导致设备损坏或轻微伤害
- **低危**：可能导致操作失败或数据丢失

# 约束条件
- 安全警示必须在第一屏显示
- 使用红色/黄色等警示色彩标记（通过符号体现）
- 禁止事项使用否定强调（"绝对不能"、"严禁"）
- 风险描述具体明确，不使用模糊表述
"""

    def _build_code_debug_prompt(self) -> str:
        """构建代码调试场景的系统提示词"""
        # 使用原始字符串避免转义问题
        prompt = '''# 角色定位
你是一位资深的代码审查专家，擅长快速定位并修复代码错误。

# 输出格式

## 🐛 错误诊断

### 错误位置
**文件**：[文件名]
**行号**：[具体行号]
**错误类型**：[语法错误/逻辑错误/性能问题/安全漏洞]

### 错误代码
```python
# ❌ 错误代码
def calculate_total(items):
    total = 0
    for item in items:
        total += item.price  # 错误: 未检查 item 是否为 None
    return total
```

### 错误原因
[详细说明为什么这段代码有问题]
1. 未对 item 进行空值检查
2. 当 items 列表中包含 None 时会抛出 AttributeError
3. 缺少异常处理机制

---

## ✅ 修复方案

### 修复后代码
```python
# ✅ 修复后代码
def calculate_total(items):
    total = 0
    for item in items:
        # 添加空值检查
        if item is not None and hasattr(item, 'price'):
            total += item.price
        else:
            print(f"警告: 跳过无效商品 {item}")
    return total
```

### Diff 格式
```diff
def calculate_total(items):
    total = 0
    for item in items:
-       total += item.price
+       # 添加空值检查
+       if item is not None and hasattr(item, 'price'):
+           total += item.price
+       else:
+           print(f"警告: 跳过无效商品 {item}")
    return total
```

### 修复说明
1. **空值检查**: 使用 if item is not None 防止空指针
2. **属性检查**: 使用 hasattr 确保对象有 price 属性
3. **异常处理**: 添加警告日志便于调试

### 测试用例
```python
# 测试修复后的代码
items = [Product(price=10.0), None, Product(price=20.0)]
total = calculate_total(items)
assert total == 30.0
```

# 约束条件
- 必须同时提供错误代码和修复代码
- 使用 Diff 格式清晰标注修改
- 错误原因分析要深入到根本原因
- 提供可运行的测试用例
- 代码注释要详细说明修复逻辑
'''
        return prompt

    def generate_prompt(
        self,
        scenario: ScenarioType,
        user_context: Optional[Dict[str, Any]] = None,
        custom_constraints: Optional[List[str]] = None
    ) -> str:
        """
        根据场景类型生成动态提示词
        
        Args:
            scenario: 业务场景类型
            user_context: 用户上下文信息(可选)
            custom_constraints: 自定义约束条件(可选)
        
        Returns:
            str: 生成的完整提示词
        """
        template = self.templates.get(scenario.value)
        if not template:
            raise ValueError(f"不支持的场景类型: {scenario}")
        
        # 基础提示词
        prompt = template["system_prompt"]
        
        # 添加用户上下文
        if user_context:
            prompt += "\n\n# 当前上下文\n"
            for key, value in user_context.items():
                prompt += f"- **{key}**: {value}\n"
        
        # 添加自定义约束
        if custom_constraints:
            prompt += "\n\n# 额外约束\n"
            for i, constraint in enumerate(custom_constraints, 1):
                prompt += f"{i}. {constraint}\n"
        
        return prompt
    
    def get_scenario_info(self, scenario: ScenarioType) -> Dict[str, Any]:
        """
        获取场景的详细信息
        
        Args:
            scenario: 业务场景类型
        
        Returns:
            Dict: 场景信息字典
        """
        return self.templates.get(scenario.value, {})
    
    def list_scenarios(self) -> List[Dict[str, str]]:
        """
        列出所有支持的场景
        
        Returns:
            List[Dict]: 场景列表
        """
        return [
            {
                "type": scenario_type,
                "name": info["name"],
                "description": info["description"],
                "output_format": info["output_format"]
            }
            for scenario_type, info in self.templates.items()
        ]
    
    def enhance_user_message(
        self,
        user_message: str,
        scenario: ScenarioType,
        knowledge_base_context: Optional[str] = None
    ) -> str:
        """
        增强用户消息，添加场景特定的引导
        
        Args:
            user_message: 原始用户消息
            scenario: 业务场景类型
            knowledge_base_context: 知识库上下文(可选)
        
        Returns:
            str: 增强后的用户消息
        """
        template = self.templates.get(scenario.value)
        if not template:
            return user_message
        
        enhanced = f"# 场景类型：{template['name']}\n\n"
        enhanced += f"# 用户问题\n{user_message}\n\n"
        
        if knowledge_base_context:
            enhanced += f"# 参考资料\n{knowledge_base_context}\n\n"
        
        enhanced += f"# 输出要求\n"
        enhanced += f"请按照 **{template['output_format']}** 格式输出，"
        enhanced += f"重点关注：{', '.join(template['priority'])}\n"
        
        return enhanced


# 全局单例
_prompt_engine_instance = None


def get_prompt_engine() -> PromptEngine:
    """获取 Prompt 引擎单例"""
    global _prompt_engine_instance
    if _prompt_engine_instance is None:
        _prompt_engine_instance = PromptEngine()
    return _prompt_engine_instance
