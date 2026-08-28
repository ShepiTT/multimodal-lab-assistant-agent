import requests
import base64
import fitz  # PyMuPDF
import os
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    load_dotenv()

API_KEY = os.environ.get("BAIDU_OCR_API_KEY")
SECRET_KEY = os.environ.get("BAIDU_OCR_SECRET_KEY")


def get_access_token():
    """
    使用 AK，SK 生成鉴权签名（Access Token）
    :return: access_token，或是None(如果错误)
    """
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {"grant_type": "client_credentials", "client_id": API_KEY, "client_secret": SECRET_KEY}
    return str(requests.post(url, params=params).json().get("access_token"))


def ocr_image(image_base64, access_token):
    """
    对单张图片进行OCR识别
    :param image_base64: 图片的base64编码
    :param access_token: 访问令牌
    :return: 识别的文本内容
    """
    url = "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic?access_token=" + access_token
    
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
    
    response = requests.post(url, headers=headers, data=payload)
    response.encoding = "utf-8"
    result = response.json()
    
    # 提取识别的文字
    text_lines = []
    if 'words_result' in result:
        for item in result['words_result']:
            text_lines.append(item['words'])
    
    return '\n'.join(text_lines)


def pdf_to_images(pdf_path):
    """
    将PDF文件转换为图片列表
    :param pdf_path: PDF文件路径
    :return: 图片base64编码列表
    """
    doc = fitz.open(pdf_path)
    images_base64 = []
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        # 设置缩放比例，提高图片清晰度
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        # 将图片转换为bytes
        img_bytes = pix.tobytes("png")
        # 转换为base64
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        images_base64.append(img_base64)
        
        print(f"已处理第 {page_num + 1}/{len(doc)} 页")
    
    doc.close()
    return images_base64


def ocr_pdf(pdf_path, output_txt_path):
    """
    对PDF文件进行OCR识别并保存为txt
    :param pdf_path: PDF文件路径
    :param output_txt_path: 输出txt文件路径
    """
    print(f"开始处理PDF文件: {pdf_path}")
    
    # 获取access token
    access_token = get_access_token()
    print("已获取access token")
    
    # 将PDF转换为图片
    print("正在将PDF转换为图片...")
    images_base64 = pdf_to_images(pdf_path)
    print(f"PDF共 {len(images_base64)} 页")
    
    # 对每页进行OCR识别
    all_text = []
    for i, img_base64 in enumerate(images_base64):
        print(f"正在识别第 {i + 1}/{len(images_base64)} 页...")
        page_text = ocr_image(img_base64, access_token)
        all_text.append(f"===== 第 {i + 1} 页 =====\n{page_text}")
    
    # 合并所有文本
    final_text = '\n\n'.join(all_text)
    
    # 保存到txt文件
    with open(output_txt_path, 'w', encoding='utf-8') as f:
        f.write(final_text)
    
    print(f"识别完成！结果已保存到: {output_txt_path}")
    return final_text


def main():
    # PDF文件路径
    pdf_path = "d:/lxx_py/毕业设计/test/OCR/ocr_test_file.pdf"
    
    # 输出txt文件路径（与PDF同名，扩展名改为.txt）
    output_txt_path = "d:/lxx_py/毕业设计/test/OCR/PaddleOCR_output.txt"
    
    # 执行OCR识别
    result = ocr_pdf(pdf_path, output_txt_path)
    
    # 打印部分结果预览
    print("\n===== 识别结果预览 =====")
    print(result[:500] + "..." if len(result) > 500 else result)


if __name__ == '__main__':
    main()
