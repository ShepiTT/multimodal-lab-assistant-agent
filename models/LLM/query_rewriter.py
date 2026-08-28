"""
查询改写模块 (Query Rewriter)
将用户口语化的查询转换为专业的知识库检索语句
"""
import os
from openai import OpenAI
from typing import Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 默认配置
DEFAULT_MODEL = "qwen3-30b-a3b-instruct-2507"
DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# 查询改写的系统提示词
REWRITE_SYSTEM_PROMPT = """你是一个专业的查询改写助手。你的任务是将用户口语化、模糊的问题转换为更专业、精确的知识库检索查询。

改写规则：
1. 提取核心关键词和专业术语
2. 去除口语化表达（如"怎么"、"啥"、"咋"等）
3. 补充可能的同义词或相关术语
4. 保持查询简洁，不超过50字
5. 如果问题涉及多个方面，拆分为多个查询（用 | 分隔）

示例：
- 输入: "这个图片咋上传啊，有啥要求不"
  输出: "图片上传 格式要求 文件大小限制"

- 输入: "基尔霍夫那个定律是啥来着"
  输出: "基尔霍夫定律 KCL KVL 电流定律 电压定律"

- 输入: "电脑配置不够怎么办"
  输出: "系统配置要求 硬件要求 最低配置"

- 输入: "语音识别老是不准"
  输出: "语音识别 准确率 ASR 识别优化 录音技巧"

只输出改写后的查询，不要任何解释。"""


def create_client(api_key: Optional[str] = None, base_url: Optional[str] = None) -> OpenAI:
    """创建 OpenAI 客户端"""
    key = api_key or os.getenv("ALI_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
    if not key:
        raise ValueError("未配置 API Key，请设置 ALI_API_KEY 环境变量")
    return OpenAI(
        api_key=key,
        base_url=base_url or DEFAULT_BASE_URL
    )


def rewrite_query(
    query: str,
    model: str = DEFAULT_MODEL,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None
) -> str:
    """
    将口语化查询改写为专业检索查询
    
    Args:
        query: 用户原始查询
        model: 使用的模型
        api_key: API Key（可选，默认从环境变量读取）
        base_url: API Base URL（可选）
    
    Returns:
        改写后的查询字符串
    """
    if not query or not query.strip():
        return query
    
    client = create_client(api_key, base_url)
    
    try:
        # 构建消息，禁用思考模式
        messages = [
            {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
            {"role": "user", "content": query}
        ]
        
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=100,
            temperature=0.3,  # 低温度，更确定性的输出
            extra_body={"enable_thinking": False}  # 禁用思考模式
        )
        
        result = completion.choices[0].message.content.strip()
        
        # 清理可能的思考标签
        if "<think>" in result:
            result = result.split("</think>")[-1].strip()
        
        return result if result else query
        
    except Exception as e:
        print(f"[query_rewriter] 查询改写失败: {e}")
        return query  # 失败时返回原查询


def rewrite_query_stream(
    query: str,
    model: str = DEFAULT_MODEL,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None
):
    """
    流式改写查询（用于需要实时显示的场景）
    """
    if not query or not query.strip():
        yield query
        return
    
    client = create_client(api_key, base_url)
    
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
                {"role": "user", "content": query}
            ],
            max_tokens=100,
            temperature=0.3,
            stream=True,
            extra_body={"enable_thinking": False}  # 禁用思考模式
        )
        
        for chunk in completion:
            content = chunk.choices[0].delta.content or ""
            if content:
                yield content
                
    except Exception as e:
        print(f"[query_rewriter] 流式改写失败: {e}")
        yield query


def expand_query(query: str, rewritten: str) -> str:
    """
    合并原始查询和改写查询，用于混合检索
    
    Args:
        query: 原始查询
        rewritten: 改写后的查询
    
    Returns:
        合并后的查询
    """
    if query == rewritten:
        return query
    
    # 去重合并
    original_terms = set(query.split())
    rewritten_terms = set(rewritten.replace("|", " ").split())
    all_terms = original_terms | rewritten_terms
    
    return " ".join(all_terms)


# 测试代码
if __name__ == "__main__":
    test_queries = [
        "这个图片咋上传啊，有啥要求不",
        "基尔霍夫那个定律是啥来着",
        "电脑配置不够怎么办",
        "语音识别老是不准怎么搞",
        "怎么登录这个系统",
        "叠加定理咋验证",
    ]
    
    print("=" * 60)
    print("查询改写测试")
    print("=" * 60)
    
    for q in test_queries:
        print(f"\n原始查询: {q}")
        rewritten = rewrite_query(q)
        print(f"改写结果: {rewritten}")
        print("-" * 40)
