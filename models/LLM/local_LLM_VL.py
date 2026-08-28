"""
本地多模态大模型 (Qwen2-VL)
支持图片理解和视频理解
"""
import os
import base64
from pathlib import Path
from typing import List, Dict, Any, Optional, Generator

# 设置环境变量
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['CUDA_VISIBLE_DEVICES'] = '0'  # 使用第一块 GPU

# 全局模型实例（单例模式）
_model = None
_processor = None
_model_path = "Qwen/Qwen2-VL-2B-Instruct"


def get_model():
    """获取或加载模型（单例模式），强制使用 GPU"""
    global _model, _processor
    
    if _model is None:
        import torch
        
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA 不可用，本地多模态模型需要 GPU")
        
        print(f"[Local VL] 正在加载模型: {_model_path}")
        print(f"[Local VL] GPU: {torch.cuda.get_device_name(0)}, 显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB")
        
        from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
        
        # 使用 float16 减少显存占用，强制加载到 GPU
        _model = Qwen2VLForConditionalGeneration.from_pretrained(
            _model_path,
            torch_dtype=torch.float16,  # 使用半精度减少显存
            device_map="cuda:0",  # 强制使用 GPU
            low_cpu_mem_usage=True  # 减少 CPU 内存使用
        )
        _processor = AutoProcessor.from_pretrained(_model_path)
        
        # 打印显存使用情况
        allocated = torch.cuda.memory_allocated(0) / 1024**3
        print(f"[Local VL] 模型加载完成，显存占用: {allocated:.2f}GB")
    
    return _model, _processor


def preload_model():
    """预加载模型"""
    get_model()
    print("[Local VL] 模型预加载完成")


def _encode_image_to_base64(image_path: str) -> str:
    """将图片编码为 base64"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _get_image_mime_type(image_path: str) -> str:
    """获取图片的 MIME 类型"""
    ext = Path(image_path).suffix.lower()
    mime_map = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.bmp': 'image/bmp'
    }
    return mime_map.get(ext, 'image/jpeg')


def build_messages(
    user_message: str,
    image_path: Optional[str] = None,
    image_url: Optional[str] = None,
    system_prompt: str = ""
) -> List[Dict[str, Any]]:
    """
    构建消息格式
    
    Args:
        user_message: 用户文本消息
        image_path: 本地图片路径
        image_url: 图片 URL
        system_prompt: 系统提示词
    """
    messages = []
    
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    content = []
    
    # 添加图片
    if image_path and os.path.exists(image_path):
        # 本地图片转 base64
        mime_type = _get_image_mime_type(image_path)
        base64_data = _encode_image_to_base64(image_path)
        content.append({
            "type": "image",
            "image": f"data:{mime_type};base64,{base64_data}"
        })
    elif image_url:
        content.append({
            "type": "image",
            "image": image_url
        })
    
    # 添加文本
    content.append({"type": "text", "text": user_message})
    
    messages.append({"role": "user", "content": content})
    
    return messages


def generate(
    user_message: str,
    image_path: Optional[str] = None,
    image_url: Optional[str] = None,
    system_prompt: str = "",
    max_new_tokens: int = 1024
) -> str:
    """
    生成回复（非流式）
    
    Args:
        user_message: 用户消息
        image_path: 本地图片路径
        image_url: 图片 URL
        system_prompt: 系统提示词
        max_new_tokens: 最大生成 token 数
    
    Returns:
        生成的文本
    """
    model, processor = get_model()
    
    messages = build_messages(user_message, image_path, image_url, system_prompt)
    
    inputs = processor.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors="pt"
    )
    inputs = inputs.to(model.device)
    
    generated_ids = model.generate(**inputs, max_new_tokens=max_new_tokens)
    generated_ids_trimmed = [
        out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    
    output_text = processor.batch_decode(
        generated_ids_trimmed,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False
    )
    
    return output_text[0] if output_text else ""


def generate_stream(
    user_message: str,
    image_path: Optional[str] = None,
    image_url: Optional[str] = None,
    system_prompt: str = "",
    max_new_tokens: int = 1024
) -> Generator[str, None, None]:
    """
    流式生成回复
    
    Args:
        user_message: 用户消息
        image_path: 本地图片路径
        image_url: 图片 URL
        system_prompt: 系统提示词
        max_new_tokens: 最大生成 token 数
    
    Yields:
        生成的文本片段
    """
    model, processor = get_model()
    
    messages = build_messages(user_message, image_path, image_url, system_prompt)
    
    inputs = processor.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors="pt"
    )
    inputs = inputs.to(model.device)
    
    # 记录输入的 token 长度，用于截取新生成的内容
    input_length = inputs.input_ids.shape[1]
    
    # 使用 TextIteratorStreamer 实现流式输出
    from transformers import TextIteratorStreamer
    from threading import Thread
    
    streamer = TextIteratorStreamer(
        processor.tokenizer,  # 使用 tokenizer 而不是 processor
        skip_special_tokens=True,
        skip_prompt=True  # 跳过输入的 prompt 部分
    )
    
    generation_kwargs = {
        **inputs,
        "max_new_tokens": max_new_tokens,
        "streamer": streamer
    }
    
    thread = Thread(target=model.generate, kwargs=generation_kwargs)
    thread.start()
    
    for text in streamer:
        if text:
            yield text
    
    thread.join()


# 兼容 llm_runner 的接口
def local_vl_generate_once(
    user_message: str,
    system_prompt: str = "",
    image_path: Optional[str] = None,
    max_new_tokens: int = 1024
) -> str:
    """兼容接口：非流式生成"""
    return generate(user_message, image_path=image_path, system_prompt=system_prompt, max_new_tokens=max_new_tokens)


def local_vl_generate_stream(
    user_message: str,
    system_prompt: str = "",
    image_path: Optional[str] = None,
    max_new_tokens: int = 1024
) -> Generator[str, None, None]:
    """兼容接口：流式生成"""
    yield from generate_stream(user_message, image_path=image_path, system_prompt=system_prompt, max_new_tokens=max_new_tokens)


if __name__ == "__main__":
    # 测试代码
    import sys
    
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        prompt = sys.argv[2] if len(sys.argv) > 2 else "请描述这张图片"
        
        print(f"图片: {image_path}")
        print(f"问题: {prompt}")
        print("回答: ", end="", flush=True)
        
        for chunk in generate_stream(prompt, image_path=image_path):
            print(chunk, end="", flush=True)
        print()
    else:
        print("用法: python local_LLM_VL.py <图片路径> [问题]")
