"""
统一 OCR 调用入口
支持: 百度OCR、PaddleOCR、Tesseract
"""
import os
import sys
import json
import base64
from pathlib import Path
from typing import Dict, Any, Optional

import requests
from dotenv import load_dotenv

# 加载环境变量
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    load_dotenv()

CONFIG_PATH = PROJECT_ROOT / "models" / "models_config.json"


def load_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {"providers": []}
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def find_provider(cfg: Dict, provider_id: Optional[str], provider_type: str = "ocr") -> Dict:
    """查找指定类型的 provider"""
    providers = [p for p in cfg.get("providers", []) if p.get("type") == provider_type]
    if provider_id:
        for p in providers:
            if p.get("id") == provider_id:
                return p
        raise ValueError(f"OCR provider 未找到: {provider_id}")
    if not providers:
        raise ValueError("配置中没有 OCR providers")
    return providers[0]


# ---- 百度 OCR ----
class BaiduOCR:
    """百度通用文字识别"""
    
    _access_token = None
    
    @classmethod
    def get_access_token(cls, api_key: str, secret_key: str) -> str:
        if cls._access_token:
            return cls._access_token
        
        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": api_key,
            "client_secret": secret_key
        }
        resp = requests.post(url, params=params, timeout=10)
        result = resp.json()
        if "access_token" not in result:
            raise RuntimeError(f"获取百度 OCR token 失败: {result}")
        cls._access_token = result["access_token"]
        return cls._access_token
    
    @classmethod
    def recognize_image(cls, image_bytes: bytes, api_key: str, secret_key: str) -> str:
        """识别图片中的文字"""
        token = cls.get_access_token(api_key, secret_key)
        url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic?access_token={token}"
        
        payload = {
            'image': base64.b64encode(image_bytes).decode('utf-8'),
            'detect_direction': 'false',
            'paragraph': 'false',
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        resp = requests.post(url, headers=headers, data=payload, timeout=30)
        result = resp.json()
        
        if 'error_code' in result:
            raise RuntimeError(f"百度 OCR 失败: {result}")
        
        lines = []
        for item in result.get('words_result', []):
            lines.append(item.get('words', ''))
        
        return '\n'.join(lines)
    
    @classmethod
    def recognize_pdf(cls, pdf_path: str, api_key: str, secret_key: str) -> str:
        """识别 PDF 文档"""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ImportError("PDF OCR 需要安装: pip install PyMuPDF")
        
        doc = fitz.open(pdf_path)
        text_parts = []
        
        for i, page in enumerate(doc):
            pix = page.get_pixmap(dpi=200)
            img_bytes = pix.tobytes("png")
            page_text = cls.recognize_image(img_bytes, api_key, secret_key)
            if page_text.strip():
                text_parts.append(f"--- 第 {i+1} 页 ---\n{page_text}")
        
        doc.close()
        return '\n'.join(text_parts)


# ---- PaddleOCR ----
class PaddleOCREngine:
    """PaddleOCR 本地识别"""
    
    _ocr = None
    
    @classmethod
    def get_ocr(cls):
        if cls._ocr is None:
            try:
                from paddleocr import PaddleOCR
                cls._ocr = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)
            except ImportError:
                raise ImportError("PaddleOCR 需要安装: pip install paddleocr paddlepaddle")
        return cls._ocr
    
    @classmethod
    def recognize(cls, image_path: str) -> str:
        """识别图片"""
        ocr = cls.get_ocr()
        result = ocr.ocr(image_path, cls=True)
        
        lines = []
        if result and result[0]:
            for line in result[0]:
                text = line[1][0] if line[1] else ""
                if text:
                    lines.append(text)
        
        return '\n'.join(lines)


# ---- Tesseract OCR ----
class TesseractOCR:
    """Tesseract OCR"""
    
    @classmethod
    def recognize(cls, image_path: str, lang: str = "chi_sim+eng") -> str:
        """识别图片"""
        try:
            import pytesseract
            from PIL import Image
        except ImportError:
            raise ImportError("Tesseract OCR 需要安装: pip install pytesseract pillow")
        
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang=lang)
        return text


# ---- 统一入口 ----
def recognize(
    input_path: str,
    provider_id: Optional[str] = None,
) -> str:
    """
    统一 OCR 入口
    
    Args:
        input_path: 图片或 PDF 文件路径
        provider_id: 指定 provider，默认使用第一个 OCR provider
    
    Returns:
        识别的文本
    """
    cfg = load_config()
    provider = find_provider(cfg, provider_id, "ocr")
    client = provider.get("client", "baidu")
    
    path = Path(input_path)
    ext = path.suffix.lower()
    
    if client == "baidu":
        api_key = os.getenv("BAIDU_OCR_API_KEY", "")
        secret_key = os.getenv("BAIDU_OCR_SECRET_KEY", "")
        if not api_key or not secret_key:
            raise RuntimeError("缺少百度 OCR 密钥，请配置 BAIDU_OCR_API_KEY 和 BAIDU_OCR_SECRET_KEY")
        
        if ext == ".pdf":
            return BaiduOCR.recognize_pdf(input_path, api_key, secret_key)
        else:
            image_bytes = path.read_bytes()
            return BaiduOCR.recognize_image(image_bytes, api_key, secret_key)
    
    elif client == "paddle":
        return PaddleOCREngine.recognize(input_path)
    
    elif client == "tesseract":
        return TesseractOCR.recognize(input_path)
    
    else:
        raise ValueError(f"不支持的 OCR client: {client}")


def recognize_bytes(
    image_bytes: bytes,
    provider_id: Optional[str] = None,
) -> str:
    """识别图片字节"""
    cfg = load_config()
    provider = find_provider(cfg, provider_id, "ocr")
    client = provider.get("client", "baidu")
    
    if client == "baidu":
        api_key = os.getenv("BAIDU_OCR_API_KEY", "")
        secret_key = os.getenv("BAIDU_OCR_SECRET_KEY", "")
        return BaiduOCR.recognize_image(image_bytes, api_key, secret_key)
    else:
        # 保存到临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(image_bytes)
            temp_path = f.name
        try:
            return recognize(temp_path, provider_id)
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        text = recognize(image_path)
        print(f"识别结果:\n{text}")
