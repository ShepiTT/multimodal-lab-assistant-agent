"""
媒体解析服务 - Base64 编码图片和视频
支持: jpg, jpeg, png, mp4, avi, mov, flv
"""
import base64
import mimetypes
from pathlib import Path
from typing import Dict, Optional, Tuple


class MediaParser:
    """图片和视频的 Base64 编码处理"""
    
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png'}
    VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.flv'}
    SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
    
    # MIME 类型映射
    MIME_TYPES = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.mp4': 'video/mp4',
        '.avi': 'video/x-msvideo',
        '.mov': 'video/quicktime',
        '.flv': 'video/x-flv',
    }
    
    @classmethod
    def can_parse(cls, file_path: str) -> bool:
        ext = Path(file_path).suffix.lower()
        return ext in cls.SUPPORTED_EXTENSIONS
    
    @classmethod
    def is_image(cls, file_path: str) -> bool:
        ext = Path(file_path).suffix.lower()
        return ext in cls.IMAGE_EXTENSIONS
    
    @classmethod
    def is_video(cls, file_path: str) -> bool:
        ext = Path(file_path).suffix.lower()
        return ext in cls.VIDEO_EXTENSIONS
    
    @classmethod
    def parse(cls, file_path: str) -> Dict:
        """
        解析媒体文件，返回 Base64 编码和元信息
        
        Returns:
            {
                'type': 'image' | 'video',
                'mime_type': str,
                'base64': str,
                'data_url': str,  # 可直接用于 HTML/API
                'size': int,
                'filename': str
            }
        """
        path = Path(file_path)
        ext = path.suffix.lower()
        
        if ext not in cls.SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的文件类型: {ext}")
        
        # 读取文件并编码
        file_bytes = path.read_bytes()
        b64_str = base64.b64encode(file_bytes).decode('utf-8')
        
        # 获取 MIME 类型
        mime_type = cls.MIME_TYPES.get(ext, mimetypes.guess_type(str(path))[0])
        
        # 构建 data URL
        data_url = f"data:{mime_type};base64,{b64_str}"
        
        return {
            'type': 'image' if ext in cls.IMAGE_EXTENSIONS else 'video',
            'mime_type': mime_type,
            'base64': b64_str,
            'data_url': data_url,
            'size': len(file_bytes),
            'filename': path.name
        }
    
    @classmethod
    def parse_for_llm(cls, file_path: str) -> Dict:
        """
        解析媒体文件，返回适合发送给多模态大模型的格式
        
        Returns:
            {
                'type': 'image_url' | 'video_url',
                'image_url': {'url': data_url} | None,
                'video_url': {'url': data_url} | None
            }
        """
        result = cls.parse(file_path)
        
        if result['type'] == 'image':
            return {
                'type': 'image_url',
                'image_url': {
                    'url': result['data_url']
                }
            }
        else:
            return {
                'type': 'video_url',
                'video_url': {
                    'url': result['data_url']
                }
            }
    
    @classmethod
    def extract_video_frames(cls, file_path: str, max_frames: int = 10) -> list:
        """
        从视频中提取关键帧，返回 Base64 编码的图片列表
        用于不支持视频的模型，可以用图片代替
        """
        try:
            import cv2
        except ImportError:
            raise ImportError("视频帧提取需要安装: pip install opencv-python")
        
        path = Path(file_path)
        cap = cv2.VideoCapture(str(path))
        
        if not cap.isOpened():
            raise ValueError(f"无法打开视频文件: {file_path}")
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames == 0:
            raise ValueError("视频没有帧")
        
        # 计算采样间隔
        interval = max(1, total_frames // max_frames)
        
        frames = []
        frame_idx = 0
        
        while len(frames) < max_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            
            if not ret:
                break
            
            # 编码为 JPEG
            _, buffer = cv2.imencode('.jpg', frame)
            b64_str = base64.b64encode(buffer).decode('utf-8')
            
            frames.append({
                'type': 'image_url',
                'image_url': {
                    'url': f"data:image/jpeg;base64,{b64_str}"
                }
            })
            
            frame_idx += interval
        
        cap.release()
        return frames
