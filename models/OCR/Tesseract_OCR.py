#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF OCR 工具
使用PyMuPDF和Tesseract进行PDF文本识别
将PDF内容转换为中文文本并保存到文件

作者：Lxx
更新时间：2025-09-25
"""

import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import time
doc = fitz.open("d:/lxx_py/毕业设计/test/OCR/ocr_test_file.pdf")
text = ""
start_time = time.time()
for i, page in enumerate(doc):
    pix = page.get_pixmap(dpi=300)  # 渲染
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    page_text = pytesseract.image_to_string(img, lang="chi_sim")
    text += f"\n--- Page {i+1} ---\n{page_text}"
end_time = time.time()
print(f"识别时间: {end_time - start_time:.2f} 秒")
with open("d:/lxx_py/毕业设计/test/OCR/Tesseract_OCR_output.txt", "w", encoding="utf-8") as f:
    f.write(text)
