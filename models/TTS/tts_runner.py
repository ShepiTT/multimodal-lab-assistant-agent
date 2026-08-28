"""
统一语音合成调用入口
支持: 百度TTS、系统TTS
"""
import os
import sys
import json
import urllib.parse
from pathlib import Path
from typing import Dict, Any, Optional

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


def find_provider(cfg: Dict, provider_id: Optional[str], provider_type: str = "tts") -> Dict:
    """查找指定类型的 provider"""
    providers = [p for p in cfg.get("providers", []) if p.get("type") == provider_type]
    if provider_id:
        for p in providers:
            if p.get("id") == provider_id:
                return p
        raise ValueError(f"TTS provider 未找到: {provider_id}")
    if not providers:
        raise ValueError("配置中没有 TTS providers")
    return providers[0]


# ---- 百度 TTS ----
class BaiduTTS:
    """百度语音合成"""
    
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
            raise RuntimeError(f"获取百度 TTS token 失败: {result}")
        cls._access_token = result["access_token"]
        return cls._access_token
    
    @classmethod
    def synthesize(
        cls,
        text: str,
        api_key: str,
        secret_key: str,
        spd: int = 5,      # 语速 0-15
        pit: int = 5,      # 音调 0-15
        vol: int = 5,      # 音量 0-15
        per: int = 0,      # 发音人 0-女声 1-男声 3-情感男 4-情感女
        aue: int = 3,      # 格式 3-mp3 4-pcm 5-pcm-16k 6-wav
    ) -> bytes:
        """合成语音，返回音频字节"""
        token = cls.get_access_token(api_key, secret_key)
        url = "https://tsn.baidu.com/text2audio"
        
        # URL 编码文本
        encoded_text = urllib.parse.quote(text)
        
        payload = f"tex={encoded_text}&tok={token}&cuid=tts_runner&ctp=1&lan=zh&spd={spd}&pit={pit}&vol={vol}&per={per}&aue={aue}"
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': '*/*'
        }
        
        resp = requests.post(url, headers=headers, data=payload.encode("utf-8"), timeout=30)
        
        # 检查是否返回错误
        content_type = resp.headers.get('Content-Type', '')
        if 'json' in content_type or 'text' in content_type:
            try:
                error = resp.json()
                raise RuntimeError(f"百度 TTS 失败: {error}")
            except:
                raise RuntimeError(f"百度 TTS 失败: {resp.text}")
        
        return resp.content


# ---- 系统 TTS ----
class SystemTTS:
    """使用系统 TTS (pyttsx3)"""
    
    _engine = None
    
    @classmethod
    def get_engine(cls):
        if cls._engine is None:
            try:
                import pyttsx3
                cls._engine = pyttsx3.init()
            except ImportError:
                raise ImportError("系统 TTS 需要安装: pip install pyttsx3")
        return cls._engine
    
    @classmethod
    def synthesize(cls, text: str, output_path: str, rate: int = 150) -> str:
        """合成语音并保存到文件"""
        engine = cls.get_engine()
        engine.setProperty('rate', rate)
        engine.save_to_file(text, output_path)
        engine.runAndWait()
        return output_path
    
    @classmethod
    def speak(cls, text: str, rate: int = 150):
        """直接播放语音"""
        engine = cls.get_engine()
        engine.setProperty('rate', rate)
        engine.say(text)
        engine.runAndWait()


# ---- 统一入口 ----
def synthesize(
    text: str,
    output_path: Optional[str] = None,
    provider_id: Optional[str] = None,
    **kwargs
) -> bytes:
    """
    统一语音合成入口
    
    Args:
        text: 要合成的文本
        output_path: 输出文件路径（可选）
        provider_id: 指定 provider，默认使用第一个 TTS provider
        **kwargs: 其他参数（如 spd, pit, vol, per）
    
    Returns:
        音频字节
    """
    cfg = load_config()
    provider = find_provider(cfg, provider_id, "tts")
    client = provider.get("client", "baidu")
    
    if client == "baidu":
        api_key = os.getenv("BAIDU_API_KEY", "")
        secret_key = os.getenv("BAIDU_SECRET_KEY", "")
        if not api_key or not secret_key:
            raise RuntimeError("缺少百度 TTS 密钥，请配置 BAIDU_API_KEY 和 BAIDU_SECRET_KEY")
        
        audio_bytes = BaiduTTS.synthesize(
            text, api_key, secret_key,
            spd=kwargs.get('spd', 5),
            pit=kwargs.get('pit', 5),
            vol=kwargs.get('vol', 5),
            per=kwargs.get('per', 0),
            aue=kwargs.get('aue', 3),
        )
        
        if output_path:
            Path(output_path).write_bytes(audio_bytes)
        
        return audio_bytes
    
    elif client == "local":
        if not output_path:
            import tempfile
            output_path = tempfile.mktemp(suffix=".wav")
        
        SystemTTS.synthesize(text, output_path, rate=kwargs.get('rate', 150))
        return Path(output_path).read_bytes()
    
    else:
        raise ValueError(f"不支持的 TTS client: {client}")


def speak(text: str, provider_id: Optional[str] = None):
    """直接播放语音（仅支持本地 TTS）"""
    cfg = load_config()
    provider = find_provider(cfg, provider_id, "tts")
    client = provider.get("client", "local")
    
    if client == "local":
        SystemTTS.speak(text)
    else:
        # 其他 provider 先合成再播放
        audio_bytes = synthesize(text, provider_id=provider_id)
        # 使用临时文件播放
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name
        
        try:
            # 尝试使用 playsound 播放
            try:
                from playsound import playsound
                playsound(temp_path)
            except ImportError:
                print(f"音频已保存到: {temp_path}")
        finally:
            pass  # 保留文件供用户播放


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        text = sys.argv[1]
        output = sys.argv[2] if len(sys.argv) > 2 else "output.mp3"
        synthesize(text, output)
        print(f"音频已保存到: {output}")
