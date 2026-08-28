import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# 0. 读取项目根目录下的 .env
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    # 回落到默认查找（当前目录及父级）
    load_dotenv()

# 1. 准备工作：初始化客户端
api_key = os.getenv("ALI_API_KEY") or os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("请先设置环境变量 ALI_API_KEY / DASHSCOPE_API_KEY / OPENAI_API_KEY 之一")

client = OpenAI(
    api_key=api_key,
    # API Key 与地域强绑定，请确保 base_url 与 API Key 的地域一致。
    base_url=os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
)

# 2. 发起流式请求
completion = client.chat.completions.create(
    model="qwen-flash",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "请介绍一下自己"}
    ],
    stream=True,
    stream_options={"include_usage": True}
)

# 3. 处理流式响应
# 用列表暂存响应片段，最后 join 比逐次 += 字符串更高效
content_parts = []
print("AI: ", end="", flush=True)

for chunk in completion:
    if chunk.choices:
        content = chunk.choices[0].delta.content or ""
        print(content, end="", flush=True)
        content_parts.append(content)
    elif chunk.usage:
        print("\n--- 请求用量 ---")
        print(f"输入 Tokens: {chunk.usage.prompt_tokens}")
        print(f"输出 Tokens: {chunk.usage.completion_tokens}")
        print(f"总计 Tokens: {chunk.usage.total_tokens}")

full_response = "".join(content_parts)
# print(f"\n--- 完整回复 ---\n{full_response}")