"""
音频格式转换工具
将 webm/其他格式 转换为 wav 格式（16kHz, 单声道）
用于百度 ASR 等需要特定格式的语音识别服务
"""
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple
import os


def check_ffmpeg() -> bool:
    """检查 ffmpeg 是否可用"""
    try:
        subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def convert_to_wav(
    input_path: str,
    output_path: Optional[str] = None,
    sample_rate: int = 16000,
    channels: int = 1
) -> Tuple[bool, str]:
    """
    将音频文件转换为 WAV 格式
    
    Args:
        input_path: 输入音频文件路径
        output_path: 输出 WAV 文件路径，如果为 None 则自动生成
        sample_rate: 采样率，默认 16000Hz（百度 ASR 要求）
        channels: 声道数，默认 1（单声道）
    
    Returns:
        (success, output_path or error_message)
    """
    if not check_ffmpeg():
        return False, "ffmpeg 未安装，请先安装 ffmpeg"
    
    input_file = Path(input_path)
    if not input_file.exists():
        return False, f"输入文件不存在: {input_path}"
    
    # 生成输出路径
    if output_path is None:
        output_path = str(input_file.with_suffix('.wav'))
    
    try:
        # 使用 ffmpeg 转换
        cmd = [
            'ffmpeg',
            '-y',  # 覆盖输出文件
            '-i', str(input_path),
            '-ar', str(sample_rate),  # 采样率
            '-ac', str(channels),  # 声道数
            '-acodec', 'pcm_s16le',  # 16位 PCM 编码
            '-f', 'wav',
            str(output_path)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            encoding='utf-8',
            errors='ignore'  # 忽略编码错误
        )
        
        if result.returncode != 0:
            return False, f"转换失败: {result.stderr}"
        
        return True, output_path
        
    except subprocess.TimeoutExpired:
        return False, "转换超时"
    except Exception as e:
        return False, f"转换出错: {str(e)}"


def convert_bytes_to_wav(
    audio_bytes: bytes,
    input_format: str = 'webm',
    sample_rate: int = 16000,
    channels: int = 1
) -> Tuple[bool, bytes, str]:
    """
    将音频字节数据转换为 WAV 格式
    
    Args:
        audio_bytes: 输入音频字节数据
        input_format: 输入格式（webm, mp3, ogg 等）
        sample_rate: 采样率
        channels: 声道数
    
    Returns:
        (success, wav_bytes or None, error_message or "")
    """
    if not check_ffmpeg():
        return False, None, "ffmpeg 未安装"
    
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=f'.{input_format}', delete=False) as tmp_in:
            tmp_in.write(audio_bytes)
            tmp_in_path = tmp_in.name
        
        tmp_out_path = tmp_in_path.rsplit('.', 1)[0] + '.wav'
        
        # 转换
        success, result = convert_to_wav(
            tmp_in_path,
            tmp_out_path,
            sample_rate,
            channels
        )
        
        if success:
            with open(tmp_out_path, 'rb') as f:
                wav_bytes = f.read()
            # 清理临时文件
            os.unlink(tmp_in_path)
            os.unlink(tmp_out_path)
            return True, wav_bytes, ""
        else:
            os.unlink(tmp_in_path)
            if os.path.exists(tmp_out_path):
                os.unlink(tmp_out_path)
            return False, None, result
            
    except Exception as e:
        return False, None, str(e)


def get_audio_info(file_path: str) -> Optional[dict]:
    """
    获取音频文件信息
    
    Returns:
        {
            'duration': float,  # 时长（秒）
            'sample_rate': int,
            'channels': int,
            'format': str
        }
    """
    if not check_ffmpeg():
        return None
    
    try:
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            str(file_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return None
        
        import json
        data = json.loads(result.stdout)
        
        audio_stream = None
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'audio':
                audio_stream = stream
                break
        
        if not audio_stream:
            return None
        
        return {
            'duration': float(data.get('format', {}).get('duration', 0)),
            'sample_rate': int(audio_stream.get('sample_rate', 0)),
            'channels': int(audio_stream.get('channels', 0)),
            'format': data.get('format', {}).get('format_name', '')
        }
        
    except Exception:
        return None


if __name__ == '__main__':
    # 测试
    print(f"ffmpeg 可用: {check_ffmpeg()}")
