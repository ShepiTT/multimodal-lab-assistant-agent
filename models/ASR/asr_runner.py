"""
统一语音识别调用入口
支持: 百度ASR、火山引擎ASR、本地FunASR
"""
import os
import sys
import json
import base64
import wave
from pathlib import Path
from typing import Dict, Any, Optional
from io import BytesIO

import requests
from dotenv import load_dotenv

# 加载环境变量
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    load_dotenv()

CONFIG_PATH = PROJECT_ROOT / "models" / "models_config.json"


def load_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {"providers": []}
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def find_provider(cfg: Dict, provider_id: Optional[str], provider_type: str = "asr") -> Dict:
    """查找指定类型的 provider"""
    providers = [p for p in cfg.get("providers", []) if p.get("type") == provider_type]
    if provider_id:
        for p in providers:
            if p.get("id") == provider_id:
                return p
        raise ValueError(f"ASR provider 未找到: {provider_id}")
    if not providers:
        raise ValueError("配置中没有 ASR providers")
    return providers[0]


def resolve_api_key(provider: Dict, key_name: str) -> str:
    """从环境变量获取 API Key"""
    env_names = provider.get("api_key_env", [])
    for env_name in env_names:
        if key_name.lower() in env_name.lower():
            val = os.getenv(env_name)
            if val:
                return val
    # 尝试直接匹配
    for env_name in env_names:
        val = os.getenv(env_name)
        if val:
            return val
    return ""


# ---- 百度 ASR ----
class BaiduASR:
    """百度语音识别"""
    
    _access_token = None
    
    @classmethod
    def get_access_token(cls, api_key: str, secret_key: str) -> str:
        if cls._access_token:
            return cls._access_token
        
        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": api_key,
            "client_secret": secret_key
        }
        resp = requests.post(url, params=params, timeout=10)
        result = resp.json()
        if "access_token" not in result:
            raise RuntimeError(f"获取百度 ASR token 失败: {result}")
        cls._access_token = result["access_token"]
        return cls._access_token
    
    @classmethod
    def recognize(cls, audio_bytes: bytes, api_key: str, secret_key: str,
                  format: str = "pcm", rate: int = 16000) -> str:
        """识别音频，返回文本"""
        token = cls.get_access_token(api_key, secret_key)
        url = "https://vop.baidu.com/server_api"
        
        # 如果是 wav，提取 pcm 数据
        if format.lower() == "wav":
            with BytesIO(audio_bytes) as bio:
                wf = wave.open(bio, "rb")
                rate = wf.getframerate()
                audio_bytes = wf.readframes(wf.getnframes())
                wf.close()
            format = "pcm"
        
        payload = {
            "format": format,
            "rate": rate,
            "channel": 1,
            "cuid": "asr_runner",
            "token": token,
            "speech": base64.b64encode(audio_bytes).decode("utf-8"),
            "len": len(audio_bytes),
            "dev_pid": 1537,  # 普通话
        }
        
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        result = resp.json()
        
        if result.get("err_no") != 0:
            raise RuntimeError(f"百度 ASR 失败: {result}")
        
        return result.get("result", [""])[0]


# ---- 本地 FunASR ----
class LocalASR:
    """本地 FunASR 模型"""
    
    _model = None
    
    @classmethod
    def get_model(cls):
        if cls._model is None:
            try:
                from funasr import AutoModel
                cls._model = AutoModel(
                    model="iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
                    vad_model="iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
                    punc_model="iic/punc_ct-transformer_cn-en-common-vocab471067-large",
                    disable_update=True,
                )
            except ImportError:
                raise ImportError("本地 ASR 需要安装: pip install funasr")
        return cls._model
    
    @classmethod
    def recognize(cls, audio_path: str) -> str:
        """识别音频文件，返回文本"""
        model = cls.get_model()
        result = model.generate(input=audio_path)
        if result and len(result) > 0:
            return result[0].get("text", "")
        return ""


# ---- 统一入口 ----
def recognize(
    audio_input,  # bytes 或文件路径
    provider_id: Optional[str] = None,
    format: str = "wav",
    rate: int = 16000,
) -> str:
    """
    统一语音识别入口
    
    Args:
        audio_input: 音频字节或文件路径
        provider_id: 指定 provider，默认使用第一个 ASR provider
        format: 音频格式 (wav/pcm/mp3)
        rate: 采样率
    
    Returns:
        识别的文本
    """
    cfg = load_config()
    provider = find_provider(cfg, provider_id, "asr")
    client = provider.get("client", "baidu")
    
    if client == "baidu":
        api_key = os.getenv("BAIDU_API_KEY", "")
        secret_key = os.getenv("BAIDU_SECRET_KEY", "")
        if not api_key or not secret_key:
            raise RuntimeError("缺少百度 ASR 密钥，请配置 BAIDU_API_KEY 和 BAIDU_SECRET_KEY")
        
        if isinstance(audio_input, str):
            audio_bytes = Path(audio_input).read_bytes()
        else:
            audio_bytes = audio_input
        
        return BaiduASR.recognize(audio_bytes, api_key, secret_key, format, rate)
    
    elif client == "local":
        if isinstance(audio_input, bytes):
            # 保存到临时文件
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as f:
                f.write(audio_input)
                temp_path = f.name
            try:
                return LocalASR.recognize(temp_path)
            finally:
                os.unlink(temp_path)
        else:
            return LocalASR.recognize(audio_input)
    
    else:
        raise ValueError(f"不支持的 ASR client: {client}")


def preload_model(provider_id: Optional[str] = None):
    """预加载 ASR 模型"""
    cfg = load_config()
    try:
        provider = find_provider(cfg, provider_id, "asr")
        client = provider.get("client", "baidu")
        
        if client == "local":
            print("  正在加载本地 FunASR 模型...")
            LocalASR.get_model()
            print("  本地 ASR 模型加载完成")
        elif client == "baidu":
            # 百度 ASR 是云端服务，预热获取 token
            api_key = os.getenv("BAIDU_API_KEY", "")
            secret_key = os.getenv("BAIDU_SECRET_KEY", "")
            if api_key and secret_key:
                BaiduASR.get_access_token(api_key, secret_key)
                print("  百度 ASR token 获取成功")
            else:
                print("  百度 ASR 未配置密钥")
        else:
            print(f"  ASR client: {client}")
    except Exception as e:
        print(f"  ASR 预加载失败: {e}")


if __name__ == "__main__":
    # 测试
    import sys
    if len(sys.argv) > 1:
        audio_path = sys.argv[1]
        text = recognize(audio_path)
        print(f"识别结果: {text}")
