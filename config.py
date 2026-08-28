import dotenv
import os

dotenv.load_dotenv()

def get_env(key):
    return os.environ.get(key)

# 通义千问模型配置
def get_aliyun_model_config():
    return {
        "api_key": get_env("ALI_API_KEY"),
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model_name": "qwen-flash"
    }

# 通义千问多模态模型配置
def get_aliyun_vl_model_config():
    return {
        "api_key": get_env("ALI_VL_API_KEY"),
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model_name": "qwen3-vl-plus"
    }

# 深度求索模型配置
def get_deepseek_model_config():
    return {
        "base_url": get_env("DEEPSEEK_BASE_URL"),
        "model_name": "deepseek-chat"
    }

# 火山方舟模型配置
def get_volcengine_model_config():
    return {
        "base_url": get_env("ARK_BASE_URL"),
        "model_name": "doubao-seed-1-6-251015"
    }

# 火山方舟多模态模型配置
def get_volcengine_vl_model_config():
    return {
        "base_url": get_env("ARK_BASE_URL"),
        "model_name": "doubao-seed-1-6-vision-250815"
    }

# 本地模型配置
def get_local_model_config():
    return {
        "model_path": get_env("LOCAL_MODEL_PATH")
    }

# 语音识别模型配置
def get_asr_model_config():
    return {
       "baidu_api_key": get_env("BAIDU_API_KEY"),
       "baidu_secret_key": get_env("BAIDU_SECRET_KEY"),
       "baidu_token_url": get_env("BAIDU_TOKEN_URL"),
       "baidu_asr_url": get_env("BAIDU_ASR_URL"),
       "baidu_tts_url": get_env("BAIDU_TTS_URL")
    }

