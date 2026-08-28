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

from openai import OpenAI

client = OpenAI(
    # Make sure the environment variable "ARK_API_KEY" has been set.
    api_key=os.environ.get("ARK_API_KEY"), 
    # The base URL for model invocation .
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    )
completion = client.chat.completions.create(
    # Replace with Model ID .
    model="doubao-seed-1-6-251015",
    messages=[
        {"role": "user", "content": "hello"}
    ]
)
print(completion.choices[0].message)