import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 0. 读取项目根目录下的 .env
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    load_dotenv()

# 安装依赖：pip install 'volcengine-python-sdk[ark]'
from volcenginesdkarkruntime import Ark 

# 初始化客户端
client = Ark(
    base_url="https://ark.cn-beijing.volces.com/api/v3",  # 模型调用基础 URL
    api_key=os.getenv('ARK_API_KEY'),  # 从环境变量获取 API Key（需替换为实际值）
)

# 调用模型（支持多图+文本输入）
completion = client.chat.completions.create(
    model="doubao-seed-1-6-vision-250815",  # 模型 ID（需替换为实际版本）
    messages=[
        {
            "role": "user",
            "content": [
                # 图片 1：公网可访问 URL
                {"type": "image_url", "image_url": {"url": "https://example.com/image1.png"}},
                # 图片 2：公网可访问 URL（支持多图输入）
                {"type": "image_url", "image_url": {"url": "https://example.com/image2.png"}},
                # 文本指令
                {"type": "text", "text": "请描述这两张图片的内容，并比较它们的异同。"}
            ],
        }
    ],
    max_tokens=2048,  # 最大输出长度（可选，默认 4k）
)

# 打印结果
print("模型回复：", completion.choices[0].message.content)