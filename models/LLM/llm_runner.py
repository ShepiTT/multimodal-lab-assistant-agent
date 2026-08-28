"""
统一大模型调用入口：
  - 读取项目根目录的 llm_config.json
  - 根据 provider/model 选择远程(OpenAI兼容)或本地模型
  - 可在命令行快速切换模型调用

依赖：
  pip install openai python-dotenv
  本地模型需要：pip install transformers torch
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
import sys
from dotenv import load_dotenv
from openai import OpenAI

# 0. 读取项目根目录下的 .env
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

ENV_PATH = PROJECT_ROOT / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    load_dotenv()

CONFIG_PATH = PROJECT_ROOT / "models" / "models_config.json"

# Import local_LLM with fallback
try:
    from models.LLM.local_LLM import local_generate_once, local_generate_stream
except ImportError:
    try:
        from LLM.local_LLM import local_generate_once, local_generate_stream
    except ImportError:
        from local_LLM import local_generate_once, local_generate_stream

# Import local_LLM_VL (多模态) with fallback
try:
    from models.LLM.local_LLM_VL import local_vl_generate_once, local_vl_generate_stream
except ImportError:
    try:
        from LLM.local_LLM_VL import local_vl_generate_once, local_vl_generate_stream
    except ImportError:
        try:
            from local_LLM_VL import local_vl_generate_once, local_vl_generate_stream
        except ImportError:
            local_vl_generate_once = None
            local_vl_generate_stream = None

def _clean_think(text: str) -> str:
    """移除 <think>…</think> 和 <|assistant|>，流式场景下如未闭合则截断后续。"""
    if "<think>" in text:
        start = text.find("<think>")
        end = text.find("</think>", start + 7)
        if end != -1:
            text = text[end + len("</think>") :]
        else:
            text = text[:start]  # 未闭合时直接截掉思考片段
    if "<|assistant|>" in text:
        text = text.split("<|assistant|>", 1)[-1]
    return text.strip()


# ---- 配置相关 ----
def load_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"未找到配置文件: {CONFIG_PATH}")
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def find_provider(cfg: Dict[str, Any], provider_id: Optional[str]) -> Dict[str, Any]:
    providers = cfg.get("providers", [])
    if provider_id:
        for p in providers:
            if p.get("id") == provider_id:
                return p
        raise ValueError(f"provider 未找到: {provider_id}")
    if not providers:
        raise ValueError("配置中没有 providers")
    return providers[0]


def find_model(provider: Dict[str, Any], model_id: Optional[str]) -> Dict[str, Any]:
    models = provider.get("models", [])
    if model_id:
        for m in models:
            if m.get("id") == model_id:
                return m
        raise ValueError(f"model 未找到: {model_id}")
    # 无指定则取 default 或第一个
    for m in models:
        if m.get("default"):
            return m
    if not models:
        raise ValueError(f"provider {provider.get('id')} 无模型配置")
    return models[0]


def resolve_api_key(provider: Dict[str, Any], override: Optional[str]) -> str:
    if override:
        return override
    for env_name in provider.get("api_key_env", []):
        val = os.getenv(env_name)
        if val:
            return val
    return ""


def resolve_base_url(provider: Dict[str, Any], override: Optional[str]) -> Optional[str]:
    if override:
        return override
    base = provider.get("base_url")
    if isinstance(base, dict):
        return base.get("default")
    return base


# ---- 本地模型（委托 local_LLM.py） ----
def call_local(user_message: str, system_prompt: str, model_path: str, max_new_tokens: int = 4096) -> str:
    return local_generate_once(user_message, system_prompt, max_new_tokens=max_new_tokens)


def call_local_stream(user_message: str, system_prompt: str, model_path: str, max_new_tokens: int = 4096, enable_thinking: bool = False):
    print(f"[call_local_stream] enable_thinking={enable_thinking}")
    yield from local_generate_stream(user_message, system_prompt, max_new_tokens=max_new_tokens, enable_thinking=enable_thinking)


# ---- 本地多模态模型（委托 local_LLM_VL.py） ----
def call_local_vl(user_message: str, system_prompt: str, image_path: str = None, max_new_tokens: int = 1024) -> str:
    if local_vl_generate_once is None:
        raise RuntimeError("本地多模态模型未加载，请检查 local_LLM_VL.py")
    return local_vl_generate_once(user_message, system_prompt, image_path=image_path, max_new_tokens=max_new_tokens)


def call_local_vl_stream(user_message: str, system_prompt: str, image_path: str = None, max_new_tokens: int = 2048):
    if local_vl_generate_stream is None:
        raise RuntimeError("本地多模态模型未加载，请检查 local_LLM_VL.py")
    yield from local_vl_generate_stream(user_message, system_prompt, image_path=image_path, max_new_tokens=max_new_tokens)


# ---- 远程模型 (OpenAI 兼容) ----
def call_remote(
    user_message,  # str 或 list (多模态消息)
    system_prompt: str,
    provider: Dict[str, Any],
    model_id: str,
    api_key_override: Optional[str],
    base_url_override: Optional[str],
) -> str:
    api_key = resolve_api_key(provider, api_key_override)
    if not api_key:
        raise RuntimeError("缺少 API Key，请在环境变量或参数中提供")
    base_url = resolve_base_url(provider, base_url_override)
    client = OpenAI(api_key=api_key, base_url=base_url or None)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    # 支持多模态消息格式
    if isinstance(user_message, list):
        messages.append({"role": "user", "content": user_message})
    else:
        messages.append({"role": "user", "content": user_message})

    resp = client.chat.completions.create(
        model=model_id,
        messages=messages,
        stream=True,  # 开启流式
    )
    parts = []
    for chunk in resp:
        if chunk.choices and chunk.choices[0].delta:
            piece = chunk.choices[0].delta.content or ""
            parts.append(piece)
    text = "".join(parts)
    return _clean_think(text)


def call_remote_stream(
    user_message,  # str 或 list (多模态消息)
    system_prompt: str,
    provider: Dict[str, Any],
    model_id: str,
    api_key_override: Optional[str],
    base_url_override: Optional[str],
    enable_thinking: bool = False,  # 新增：思考模式
):
    api_key = resolve_api_key(provider, api_key_override)
    if not api_key:
        raise RuntimeError("缺少 API Key，请在环境变量或参数中提供")
    base_url = resolve_base_url(provider, base_url_override)
    client = OpenAI(api_key=api_key, base_url=base_url or None)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    # 支持多模态消息格式
    if isinstance(user_message, list):
        messages.append({"role": "user", "content": user_message})
    else:
        messages.append({"role": "user", "content": user_message})

    # 构建请求参数
    request_params = {
        "model": model_id,
        "messages": messages,
        "stream": True,
    }
    
    # 检测是否是 DeepSeek 模型
    provider_id = provider.get("id", "").lower()
    is_deepseek = "deepseek" in provider_id or "deepseek" in model_id.lower()
    
    # 对于 DeepSeek reasoner 模型，需要特殊处理
    is_reasoner = "reasoner" in model_id.lower() or "r1" in model_id.lower()
    
    resp = client.chat.completions.create(**request_params)
    buffer = ""
    last_clean = ""
    reasoning_started = False
    content_started = False
    
    for chunk in resp:
        if chunk.choices and chunk.choices[0].delta:
            delta = chunk.choices[0].delta
            
            # DeepSeek reasoner 模型的思考内容在 reasoning_content 字段
            if enable_thinking and is_deepseek and hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                if not reasoning_started:
                    yield "<think>"
                    reasoning_started = True
                yield delta.reasoning_content
            
            # 正常内容
            piece = delta.content or ""
            if piece:
                # 如果之前有思考内容，先关闭思考标签
                if reasoning_started and not content_started:
                    yield "</think>"
                    content_started = True
                
                buffer += piece
                
                # 如果开启思考模式，保留思考内容（针对返回 <think> 标签的模型）
                if enable_thinking:
                    yield piece
                else:
                    # 不开启思考模式，清理思考内容
                    temp = _clean_think(buffer)
                    new_part = temp[len(last_clean):]
                    if new_part:
                        yield new_part
                        last_clean = temp
    
    # 确保思考标签闭合
    if reasoning_started and not content_started:
        yield "</think>"


# ---- 总入口 ----
def call_model(
    message: str,
    provider_id: Optional[str] = None,
    model_id: Optional[str] = None,
    system_prompt: str = "",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> str:
    cfg = load_config()
    provider = find_provider(cfg, provider_id)
    model = find_model(provider, model_id)

    if provider.get("client") == "local":
        model_path = provider.get("model_path")
        if not model_path:
            raise RuntimeError(f"本地模型缺少 model_path: {provider.get('id')}")
        return call_local(message, system_prompt, model_path)

    return call_remote(
        user_message=message,
        system_prompt=system_prompt,
        provider=provider,
        model_id=model.get("id"),
        api_key_override=api_key,
        base_url_override=base_url,
    )


def call_model_stream(
    message: str,
    provider_id: Optional[str] = None,
    model_id: Optional[str] = None,
    system_prompt: str = "",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    image_path: Optional[str] = None,  # 新增：图片路径（用于本地多模态）
    enable_thinking: bool = False,  # 新增：思考模式
):
    cfg = load_config()
    provider = find_provider(cfg, provider_id)
    model = find_model(provider, model_id)

    client_type = provider.get("client")
    
    if client_type == "local":
        model_path = provider.get("model_path")
        if not model_path:
            raise RuntimeError(f"本地模型缺少 model_path: {provider.get('id')}")
        yield from call_local_stream(message, system_prompt, model_path, enable_thinking=enable_thinking)
    elif client_type == "local_vl":
        # 本地多模态模型
        yield from call_local_vl_stream(message, system_prompt, image_path=image_path)
    else:
        yield from call_remote_stream(
            user_message=message,
            system_prompt=system_prompt,
            provider=provider,
            model_id=model.get("id"),
            api_key_override=api_key,
            base_url_override=base_url,
            enable_thinking=enable_thinking,
        )


# ---- CLI ----
def main():
    import argparse

    parser = argparse.ArgumentParser(description="统一大模型调用")
    parser.add_argument("message", help="用户输入内容")
    parser.add_argument("--provider", "-p", help="provider id (见 llm_config.json)")
    parser.add_argument("--model", "-m", help="model id (见 llm_config.json)")
    parser.add_argument("--system", "-s", default="", help="system prompt")
    parser.add_argument("--api_key", help="覆盖 API Key")
    parser.add_argument("--base_url", help="覆盖 Base URL")
    args = parser.parse_args()

    try:
        result = call_model(
            message=args.message,
            provider_id=args.provider,
            model_id=args.model,
            system_prompt=args.system,
            api_key=args.api_key,
            base_url=args.base_url,
        )
        print(result)
    except Exception as e:
        print(f"[Error] {e}")


if __name__ == "__main__":
    main()

