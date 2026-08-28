"""
OCR 解析服务 - 使用百度 OCR API 解析文档
支持: docx, pdf
"""
import os
import base64
import requests
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class OCRParser:
    """使用百度 OCR API 解析文档类文件"""
    
    SUPPORTED_EXTENSIONS = {'.docx', '.pdf'}
    
    # 百度 OCR API 配置
    API_KEY = os.getenv("BAIDU_OCR_API_KEY", "")
    SECRET_KEY = os.getenv("BAIDU_OCR_SECRET_KEY", "")
    TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
    OCR_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic"
    
    _access_token = None
    
    @classmethod
    def get_access_token(cls) -> str:
        """获取百度 OCR 的 access_token"""
        if cls._access_token:
            return cls._access_token
        
        if not cls.API_KEY or not cls.SECRET_KEY:
            raise RuntimeError("缺少百度 OCR API 密钥，请在 .env 中配置 BAIDU_OCR_API_KEY 和 BAIDU_OCR_SECRET_KEY")
        
        params = {
            "grant_type": "client_credentials",
            "client_id": cls.API_KEY,
            "client_secret": cls.SECRET_KEY
        }
        response = requests.post(cls.TOKEN_URL, params=params, timeout=10)
        result = response.json()
        
        if "access_token" not in result:
            raise RuntimeError(f"获取百度 OCR token 失败: {result}")
        
        cls._access_token = result["access_token"]
        return cls._access_token
    
    @classmethod
    def can_parse(cls, file_path: str) -> bool:
        ext = Path(file_path).suffix.lower()
        return ext in cls.SUPPORTED_EXTENSIONS
    
    @classmethod
    def parse(cls, file_path: str) -> str:
        """解析文档，返回文本内容"""
        path = Path(file_path)
        ext = path.suffix.lower()
        
        if ext == '.docx':
            return cls._parse_docx(path)
        elif ext == '.pdf':
            return cls._parse_pdf(path)
        else:
            raise ValueError(f"不支持的文件类型: {ext}")
    
    @classmethod
    def _ocr_image(cls, image_base64: str) -> str:
        """对单张图片进行 OCR 识别"""
        access_token = cls.get_access_token()
        url = f"{cls.OCR_URL}?access_token={access_token}"
        
        payload = {
            'image': image_base64,
            'detect_direction': 'false',
            'detect_language': 'false',
            'paragraph': 'false',
            'probability': 'false'
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        response = requests.post(url, headers=headers, data=payload, timeout=30)
        response.encoding = "utf-8"
        result = response.json()
        
        # 提取识别的文字
        text_lines = []
        if 'words_result' in result:
            for item in result['words_result']:
                text_lines.append(item['words'])
        
        return '\n'.join(text_lines)
    
    @classmethod
    def _parse_docx(cls, path: Path) -> str:
        """解析 Word 文档"""
        try:
            from docx import Document
        except ImportError:
            raise ImportError("请安装 python-docx: pip install python-docx")
        
        doc = Document(path)
        paragraphs = []
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append(text)
        
        # 读取表格内容（处理合并单元格，避免重复）
        for table in doc.tables:
            table_rows = []
            for row in table.rows:
                # 使用集合去重，处理合并单元格导致的重复
                seen_texts = []
                for cell in row.cells:
                    cell_text = cell.text.strip()
                    # 跳过空单元格和重复内容
                    if cell_text and cell_text not in seen_texts:
                        seen_texts.append(cell_text)
                
                if seen_texts:
                    row_text = ' | '.join(seen_texts)
                    # 避免整行重复
                    if row_text not in table_rows:
                        table_rows.append(row_text)
            
            # 将表格内容添加到段落
            if table_rows:
                paragraphs.append('\n'.join(table_rows))
        
        return '\n'.join(paragraphs)
    
    @classmethod
    def _parse_pdf(cls, path: Path) -> str:
        """解析 PDF 文档，优先提取文本，失败则 OCR"""
        # 先尝试直接提取文本
        text = cls._extract_pdf_text(path)
        
        # 检查文本质量：
        # 1. 文本长度要足够（至少 500 字符）
        # 2. 不能是试读版提示文字
        is_trial_version = any(keyword in text for keyword in ['试读', 'ertongbook', '需要完整PDF'])
        
        if text and len(text.strip()) > 500 and not is_trial_version:
            return text
        
        # 文本太少或是试读版，使用 OCR
        print(f"[OCR] PDF 文本提取不足（{len(text.strip())} 字符）或检测到试读版，启用 OCR 识别...")
        return cls._ocr_pdf(path)
    
    @classmethod
    def _extract_pdf_text(cls, path: Path) -> str:
        """直接提取 PDF 文本"""
        try:
            import pdfplumber
            text_parts = []
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            return '\n'.join(text_parts)
        except ImportError:
            pass
        
        try:
            import PyPDF2
            text_parts = []
            with open(path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
            return '\n'.join(text_parts)
        except ImportError:
            pass
        
        # 都没有安装，直接用 OCR
        return ""
    
    @classmethod
    def _ocr_pdf(cls, path: Path) -> str:
        """使用百度 OCR 识别 PDF（扫描件）"""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ImportError("PDF OCR 需要安装: pip install PyMuPDF")
        
        doc = fitz.open(path)
        text_parts = []
        
        for i, page in enumerate(doc):
            # 渲染页面为图片
            pix = page.get_pixmap(dpi=200)
            img_bytes = pix.tobytes("png")
            img_base64 = base64.b64encode(img_bytes).decode('utf-8')
            
            # OCR 识别
            page_text = cls._ocr_image(img_base64)
            if page_text.strip():
                text_parts.append(f"--- 第 {i+1} 页 ---\n{page_text}")
        
        doc.close()
        return '\n'.join(text_parts)
