"""
统一解析入口 - 根据文件类型自动选择解析器
"""
from pathlib import Path
from typing import Dict, Union

from .text_parser import TextParser
from .ocr_parser import OCRParser
from .media_parser import MediaParser


# 文件大小限制 (字节)
SIZE_LIMITS = {
    'document': 50 * 1024 * 1024,   # 50MB
    'image': 10 * 1024 * 1024,      # 10MB
    'video': 50 * 1024 * 1024,      # 50MB
}

# 文件类型分类
DOCUMENT_EXTENSIONS = {'.docx', '.txt', '.pdf', '.md', '.html', '.htm', '.csv', '.xlsx', '.py', '.js', '.java', '.c', '.cpp', '.h', '.json', '.xml', '.yaml', '.yml'}
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png'}
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.flv'}
ALL_EXTENSIONS = DOCUMENT_EXTENSIONS | IMAGE_EXTENSIONS | VIDEO_EXTENSIONS


def get_file_category(file_path: str) -> str:
    """获取文件分类"""
    ext = Path(file_path).suffix.lower()
    if ext in DOCUMENT_EXTENSIONS:
        return 'document'
    elif ext in IMAGE_EXTENSIONS:
        return 'image'
    elif ext in VIDEO_EXTENSIONS:
        return 'video'
    return 'unknown'


def validate_file(file_path: str) -> tuple:
    """
    验证文件是否符合要求
    Returns: (is_valid, error_message)
    """
    path = Path(file_path)
    
    if not path.exists():
        return False, "文件不存在"
    
    ext = path.suffix.lower()
    if ext not in ALL_EXTENSIONS:
        return False, f"不支持的文件类型: {ext}"
    
    category = get_file_category(file_path)
    size_limit = SIZE_LIMITS.get(category, 0)
    file_size = path.stat().st_size
    
    if file_size > size_limit:
        limit_mb = size_limit / (1024 * 1024)
        return False, f"文件大小超过限制 ({limit_mb}MB)"
    
    return True, ""


def parse_file(file_path: str) -> Dict:
    """
    统一解析入口
    
    Returns:
        {
            'success': bool,
            'type': 'text' | 'image' | 'video',
            'content': str | dict,  # 文本内容或媒体信息
            'error': str | None
        }
    """
    # 验证文件
    is_valid, error = validate_file(file_path)
    if not is_valid:
        return {'success': False, 'type': None, 'content': None, 'error': error}
    
    path = Path(file_path)
    ext = path.suffix.lower()
    
    try:
        # 文本类文件 - 直接读取
        if TextParser.can_parse(file_path):
            content = TextParser.parse(file_path)
            return {
                'success': True,
                'type': 'text',
                'content': content,
                'error': None
            }
        
        # 文档类文件 - OCR 解析
        if OCRParser.can_parse(file_path):
            content = OCRParser.parse(file_path)
            return {
                'success': True,
                'type': 'text',
                'content': content,
                'error': None
            }
        
        # 媒体文件 - Base64 编码
        if MediaParser.can_parse(file_path):
            content = MediaParser.parse_for_llm(file_path)
            media_type = 'image' if MediaParser.is_image(file_path) else 'video'
            return {
                'success': True,
                'type': media_type,
                'content': content,
                'error': None
            }
        
        return {
            'success': False,
            'type': None,
            'content': None,
            'error': f"无法解析文件类型: {ext}"
        }
        
    except Exception as e:
        return {
            'success': False,
            'type': None,
            'content': None,
            'error': str(e)
        }


def parse_for_chat(file_path: str, user_question: str = "") -> Dict:
    """
    解析文件并构建适合发送给 LLM 的消息格式
    
    Returns:
        {
            'success': bool,
            'messages': list,  # 可直接发送给 LLM 的消息列表
            'error': str | None
        }
    """
    result = parse_file(file_path)
    
    if not result['success']:
        return {'success': False, 'messages': [], 'error': result['error']}
    
    filename = Path(file_path).name
    
    if result['type'] == 'text':
        # 文本内容，构建文本消息
        content = result['content']
        if len(content) > 30000:
            content = content[:30000] + "\n...(内容过长，已截断)"
        
        prompt = f"以下是文件 [{filename}] 的内容：\n\n{content}"
        if user_question:
            prompt += f"\n\n用户问题：{user_question}"
        
        return {
            'success': True,
            'messages': [{'type': 'text', 'text': prompt}],
            'error': None
        }
    
    elif result['type'] == 'image':
        # 图片，构建多模态消息
        messages = []
        if user_question:
            messages.append({'type': 'text', 'text': f"关于图片 [{filename}]：{user_question}"})
        else:
            messages.append({'type': 'text', 'text': f"请描述这张图片 [{filename}]"})
        messages.append(result['content'])
        
        return {
            'success': True,
            'messages': messages,
            'error': None
        }
    
    elif result['type'] == 'video':
        # 视频，提取关键帧
        try:
            frames = MediaParser.extract_video_frames(file_path, max_frames=5)
            messages = []
            if user_question:
                messages.append({'type': 'text', 'text': f"关于视频 [{filename}]（以下是关键帧）：{user_question}"})
            else:
                messages.append({'type': 'text', 'text': f"请描述这个视频 [{filename}]（以下是关键帧）"})
            messages.extend(frames)
            
            return {
                'success': True,
                'messages': messages,
                'error': None
            }
        except ImportError:
            # 没有 opencv，直接返回视频 URL
            messages = []
            if user_question:
                messages.append({'type': 'text', 'text': f"关于视频 [{filename}]：{user_question}"})
            messages.append(result['content'])
            
            return {
                'success': True,
                'messages': messages,
                'error': None
            }
    
    return {'success': False, 'messages': [], 'error': '未知文件类型'}
