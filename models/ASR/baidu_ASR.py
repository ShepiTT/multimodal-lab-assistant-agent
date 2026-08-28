import base64
import os
import sys
import wave
from io import BytesIO
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    load_dotenv()

# 百度语音识别配置
API_KEY = os.environ.get("BAIDU_API_KEY")
SECRET_KEY = os.environ.get("BAIDU_SECRET_KEY")

# 需要识别的本地音频（16k 单声道 PCM/WAV）
AUDIO_PATH = r"D:\lxx_py\毕业设计\test\ASR\baidu_tts_output.wav"


def main(audio_path=None):
    url = "https://vop.baidu.com/server_api"
    audio_path = audio_path or AUDIO_PATH

    # 读取 wav，获取 PCM 数据
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()
    with BytesIO(audio_bytes) as bio:
        wf = wave.open(bio, "rb")
        nchannels, sampwidth, framerate, nframes = wf.getparams()[:4]
        pcm_data = wf.readframes(nframes)

    token = get_access_token()
    if not token:
        raise RuntimeError("获取 access_token 失败")

    # 构造请求：speech 为 base64 编码的 PCM 数据，len 为原始字节长度
    payload = {
        "format": "pcm",
        "rate": framerate,
        "channel": nchannels,
        "cuid": "asr_local_test",
        "token": token,
        "speech": base64.b64encode(pcm_data).decode("utf-8"),
        "len": len(pcm_data),
        "dev_pid": 1537,  # 普通话输入法模型，16k
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    resp = requests.post(url, headers=headers, json=payload)
    resp.encoding = "utf-8"
    print(resp.text)
    return resp.json()


def get_access_token():
    """使用 AK/SK 获取百度 Access Token"""
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {
        "grant_type": "client_credentials",
        "client_id": API_KEY,
        "client_secret": SECRET_KEY,
    }
    return str(requests.post(url, params=params).json().get("access_token"))


if __name__ == "__main__":
    cli_audio_path = sys.argv[1] if len(sys.argv) > 1 else None
    main(cli_audio_path)
