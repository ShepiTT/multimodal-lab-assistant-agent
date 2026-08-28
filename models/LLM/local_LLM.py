import sys
import time
import torch
import threading
from pathlib import Path
from modelscope import AutoModelForCausalLM, AutoTokenizer
from transformers import TextIteratorStreamer
from dotenv import load_dotenv

# 0. 读取项目根目录下的 .env
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

ENV_PATH = PROJECT_ROOT / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    load_dotenv()

from config import get_local_model_config  # noqa: E402

# 使用本地模型路径（优先读取 .env 配置）
_local_cfg = get_local_model_config() or {}
model_name = _local_cfg.get("model_path") or r"D:\lxx_py\毕业设计\models\Qwen3-1.7B"
if not model_name:
    raise RuntimeError("本地模型路径未配置，请在 .env 中设置 LOCAL_MODEL_PATH，或修改 config.py")

# 检查GPU是否可用
print("=" * 50)
if torch.cuda.is_available():
    print(f"✓ GPU 可用: {torch.cuda.get_device_name(0)}")
    print(f"  显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
else:
    print("✗ GPU 不可用，将使用 CPU（速度较慢）")
print("=" * 50)

# load the tokenizer and the model
print("\n正在加载模型，请稍候...")
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16,       # 使用半精度，减少显存占用并加速
    device_map="auto"                # 自动分配到GPU
)

# 打印模型所在设备
print(f"模型加载完成！运行设备: {model.device}")
print("输入 'exit' 或 'quit' 退出对话\n")

# 保存对话历史
messages = []

def _clean_think(text: str) -> str:
    """移除思考标签，返回纯助手文本。"""
    if "<think>" in text:
        start = text.find("<think>")
        end = text.find("</think>", start + 7)
        if end != -1:
            text = text[end + len("</think>") :]
        else:
            text = text[:start]
    if "<|assistant|>" in text:
        text = text.split("<|assistant|>", 1)[-1]
    return text.strip()


def local_generate_once(user_message: str, system_prompt: str = "", max_new_tokens: int = 4096, enable_thinking: bool = False) -> str:
    """无打印的单轮生成，供其他模块调用。"""
    local_msgs = []
    if system_prompt:
        local_msgs.append({"role": "system", "content": system_prompt})
    local_msgs.append({"role": "user", "content": user_message})
    prompt = tokenizer.apply_chat_template(
        local_msgs, 
        tokenize=False, 
        add_generation_prompt=True,
        enable_thinking=enable_thinking
    )
    inputs = tokenizer([prompt], return_tensors="pt").to(model.device)
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
        )
    text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return _clean_think(text)


def local_generate_stream(user_message: str, system_prompt: str = "", max_new_tokens: int = 4096, enable_thinking: bool = False):
    """流式生成的生成器，返回增量文本，不打印。"""
    print(f"[local_generate_stream] enable_thinking={enable_thinking}")
    local_msgs = []
    if system_prompt:
        local_msgs.append({"role": "system", "content": system_prompt})
    local_msgs.append({"role": "user", "content": user_message})
    prompt = tokenizer.apply_chat_template(
        local_msgs, 
        tokenize=False, 
        add_generation_prompt=True,
        enable_thinking=enable_thinking
    )
    print(f"[local_generate_stream] prompt 前100字符: {prompt[:100]}...")
    inputs = tokenizer([prompt], return_tensors="pt").to(model.device)

    streamer = TextIteratorStreamer(
        tokenizer,
        skip_prompt=True,
        skip_special_tokens=False,
    )
    generation_kwargs = dict(
        **inputs,
        max_new_tokens=max_new_tokens,
        streamer=streamer,
        do_sample=True,
        temperature=0.7,
        top_p=0.9,
    )
    thread = threading.Thread(target=model.generate, kwargs=generation_kwargs)
    thread.start()

    buffer = ""
    last_clean = ""
    for new_text in streamer:
        buffer += new_text
        
        if enable_thinking:
            # 思考模式：保留 <think> 内容，直接输出
            yield new_text
        else:
            # 非思考模式：清理 <think> 内容
            temp = _clean_think(buffer)
            new_part = temp[len(last_clean):]
            if new_part:
                yield new_part
                last_clean = temp
    thread.join()

def chat_stream(user_input, enable_thinking=False):
    """进行一轮对话（流式输出）"""
    # 添加用户消息到历史
    messages.append({"role": "user", "content": user_input})
    
    # 应用聊天模板
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=enable_thinking
    )
    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)
    
    # 创建流式输出器
    streamer = TextIteratorStreamer(
        tokenizer, 
        skip_prompt=True, 
        skip_special_tokens=False  # 保留特殊标记以便检测思考标签
    )
    
    # 在后台线程中运行生成
    generation_kwargs = dict(
        **model_inputs,
        max_new_tokens=2048,
        streamer=streamer
    )
    # 记录生成开始时间
    start_time = time.time()
    thread = threading.Thread(target=model.generate, kwargs=generation_kwargs)
    thread.start()
    
    # 状态变量
    full_response = ""
    thinking_content = ""
    response_content = ""
    in_thinking = False
    thinking_ended = False
    printed_thinking_header = False
    printed_response_header = False
    
    # 流式输出
    for new_text in streamer:
        full_response += new_text
        
        if enable_thinking:
            # 检测思考开始标签 <think>
            if "<think>" in full_response and not in_thinking and not thinking_ended:
                in_thinking = True
                if not printed_thinking_header:
                    print("\n💭 思考过程:", flush=True)
                    printed_thinking_header = True
            
            # 检测思考结束标签 </think>
            if "</think>" in full_response and in_thinking:
                in_thinking = False
                thinking_ended = True
                # 提取完整思考内容
                think_start = full_response.find("<think>") + len("<think>")
                think_end = full_response.find("</think>")
                thinking_content = full_response[think_start:think_end].strip()
                print()  # 思考部分结束，换行
                continue
            
            # 在思考模式中输出
            if in_thinking:
                # 移除 <think> 标签后输出
                temp = full_response.replace("<think>", "")
                # 只输出新增内容
                if len(temp) > len(thinking_content):
                    new_part = temp[len(thinking_content):]
                    print(new_part, end="", flush=True)
                    thinking_content = temp
            elif thinking_ended:
                # 思考结束后，输出正常回复
                # 获取 </think> 后的内容
                after_think = full_response.split("</think>")[-1]
                # 清理特殊标记
                clean_after = after_think.replace("<|im_end|>", "").replace("<|endoftext|>", "")
                
                if not printed_response_header and clean_after.strip():
                    print("助手: ", end="", flush=True)
                    printed_response_header = True
                
                if len(clean_after) > len(response_content):
                    new_part = clean_after[len(response_content):]
                    print(new_part, end="", flush=True)
                    response_content = clean_after
        else:
            # 非思考模式，直接输出
            if not printed_response_header:
                print("助手: ", end="", flush=True)
                printed_response_header = True
            
            # 清理特殊标记
            clean_response = full_response.replace("<|im_end|>", "").replace("<|endoftext|>", "")
            if len(clean_response) > len(response_content):
                new_part = clean_response[len(response_content):]
                print(new_part, end="", flush=True)
                response_content = clean_response
    
    thread.join()
    duration = max(time.time() - start_time, 1e-6)  # 避免除以零
    print("\n")  # 输出结束，换行
    
    # 清理最终内容
    if enable_thinking and "</think>" in full_response:
        final_content = full_response.split("</think>")[-1]
    else:
        final_content = full_response
    
    # 移除特殊标记
    final_content = final_content.replace("<|im_end|>", "").replace("<|endoftext|>", "").strip()
    # 基于最终助手文本计算 tokens 数量
    token_count = len(tokenizer.encode(response_content or final_content))
    speed = token_count / duration
    print(f"[统计] 输出 {token_count} tokens，用时 {duration:.2f}s，平均 {speed:.2f} tokens/s\n")
    
    # 添加助手回复到历史
    messages.append({"role": "assistant", "content": final_content})
    
    return thinking_content.strip() if thinking_content else None, final_content

def main():
    print("=" * 50)
    print("欢迎使用 Qwen3 聊天助手！（流式输出）")
    print("提示：输入 '/think' 开启思考模式，'/clear' 清空对话历史")
    print("=" * 50 + "\n")
    
    enable_thinking = False
    
    while True:
        try:
            user_input = input("你: ").strip()
        except KeyboardInterrupt:
            print("\n再见！")
            break
            
        if not user_input:
            continue
            
        # 特殊命令处理
        if user_input.lower() in ['exit', 'quit', '退出']:
            print("再见！")
            break
        elif user_input.lower() == '/think':
            enable_thinking = not enable_thinking
            status = "开启" if enable_thinking else "关闭"
            print(f"[系统] 思考模式已{status}\n")
            continue
        elif user_input.lower() == '/clear':
            messages.clear()
            print("[系统] 对话历史已清空\n")
            continue
        
        # 进行流式对话
        chat_stream(user_input, enable_thinking)

if __name__ == "__main__":
    main()
