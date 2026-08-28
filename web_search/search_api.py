"""
联网搜索模块 - 使用 Metaso API
"""
import http.client
import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

# 从环境变量读取 API Key
METASO_API_KEY = os.getenv("METASO_API_KEY", "mk-3DFAA704F7D31C6A1184428FC35B1F84")


def search_web(
    query: str,
    size: int = 10,
    include_summary: bool = True,
    include_raw_content: bool = False,
    scope: str = "webpage"
) -> Dict[str, Any]:
    """
    使用 Metaso API 进行网页搜索
    
    Args:
        query: 搜索关键词
        size: 返回结果数量，默认 10
        include_summary: 是否包含摘要，默认 True
        include_raw_content: 是否包含原始内容，默认 False
        scope: 搜索范围，默认 "webpage"
    
    Returns:
        Dict: 搜索结果
            {
                "success": bool,
                "data": List[Dict],  # 搜索结果列表
                "error": str  # 错误信息（如果有）
            }
    """
    try:
        conn = http.client.HTTPSConnection("metaso.cn", timeout=15)
        
        payload = json.dumps({
            "q": query,
            "scope": scope,
            "includeSummary": include_summary,
            "size": str(size),
            "includeRawContent": include_raw_content,
            "conciseSnippet": False
        })
        
        headers = {
            'Authorization': f'Bearer {METASO_API_KEY}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        conn.request("POST", "/api/v1/search", payload, headers)
        res = conn.getresponse()
        data = res.read()
        
        # 解析响应
        result = json.loads(data.decode("utf-8"))
        
        # 检查是否成功
        if res.status == 200:
            # Metaso API 返回的数据在 webpages 字段中
            webpages = result.get("webpages", [])
            
            # 转换为统一格式
            data_list = []
            for page in webpages:
                data_list.append({
                    "title": page.get("title", ""),
                    "url": page.get("link", ""),
                    "snippet": page.get("snippet", ""),
                    "summary": page.get("summary", ""),
                    "score": page.get("score", "")
                })
            
            return {
                "success": True,
                "data": data_list,
                "query": query
            }
        else:
            return {
                "success": False,
                "error": f"API 返回错误: {res.status}",
                "data": []
            }
            
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"JSON 解析失败: {str(e)}",
            "data": []
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"搜索失败: {str(e)}",
            "data": []
        }
    finally:
        if 'conn' in locals():
            conn.close()


def format_search_results(search_data: List[Dict[str, Any]], max_results: int = 5) -> str:
    """
    格式化搜索结果为适合发送给大模型的文本
    
    Args:
        search_data: 搜索结果数据
        max_results: 最多使用的结果数量
    
    Returns:
        str: 格式化后的文本
    """
    if not search_data:
        return "未找到相关搜索结果。"
    
    formatted_text = "以下是联网搜索到的相关信息：\n\n"
    
    for idx, item in enumerate(search_data[:max_results], 1):
        title = item.get("title", "无标题")
        url = item.get("url", "")
        snippet = item.get("snippet", "")
        summary = item.get("summary", "")
        
        formatted_text += f"【结果 {idx}】\n"
        formatted_text += f"标题: {title}\n"
        if url:
            formatted_text += f"来源: {url}\n"
        if summary:
            formatted_text += f"摘要: {summary}\n"
        elif snippet:
            formatted_text += f"内容: {snippet}\n"
        formatted_text += "\n"
    
    return formatted_text


def search_and_format(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    搜索并格式化结果（便捷方法）
    
    Args:
        query: 搜索关键词
        max_results: 最多返回的结果数量
    
    Returns:
        Dict: 包含格式化文本和原始数据
            {
                "success": bool,
                "formatted_text": str,  # 格式化后的文本
                "raw_data": List[Dict],  # 原始搜索结果
                "error": str  # 错误信息（如果有）
            }
    """
    result = search_web(query, size=max_results * 2)  # 多搜索一些以备筛选
    
    if result["success"]:
        formatted = format_search_results(result["data"], max_results)
        return {
            "success": True,
            "formatted_text": formatted,
            "raw_data": result["data"][:max_results],
            "query": query
        }
    else:
        return {
            "success": False,
            "formatted_text": "",
            "raw_data": [],
            "error": result.get("error", "未知错误")
        }


# 测试代码
if __name__ == "__main__":
    # 测试搜索功能
    test_query = "Python 最新版本"
    print(f"搜索: {test_query}\n")
    
    result = search_and_format(test_query, max_results=3)
    
    if result["success"]:
        print(result["formatted_text"])
        print(f"\n共找到 {len(result['raw_data'])} 条结果")
    else:
        print(f"搜索失败: {result.get('error')}")