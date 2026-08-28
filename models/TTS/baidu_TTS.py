import os
import requests

# 尝试加载 .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

API_KEY = os.getenv("BAIDU_API_KEY", "")
SECRET_KEY = os.getenv("BAIDU_SECRET_KEY", "")

def main():
        
    url = os.getenv("BAIDU_TTS_URL", "https://tsn.baidu.com/text2audio")
    
    payload='tex=%E4%BD%A0%E5%A5%BD%EF%BC%8C%E6%88%91%E6%98%AF%E5%B0%8F%E5%BA%A6%E5%B0%8F%E5%BA%A6&tok='+ get_access_token() +'&cuid=kIgiqVJu1PovxS0uwki0iPIvZdDdcofW&ctp=1&lan=zh&spd=5&pit=5&vol=5&per=4194&aue=3'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': '*/*',
        'cuid': 'yjlFYfUzFubbIilS2l0ltwTYEuXEsDN9'
    }
    
    response = requests.request("POST", url, headers=headers, data=payload.encode("utf-8"))
    
    response.encoding = "utf-8"
    print(response.text)
    

def get_access_token():
    """
    使用 AK，SK 生成鉴权签名（Access Token）
    :return: access_token，或是None(如果错误)
    """
    url = os.getenv("BAIDU_TOKEN_URL", "https://aip.baidubce.com/oauth/2.0/token")
    params = {"grant_type": "client_credentials", "client_id": API_KEY, "client_secret": SECRET_KEY}
    return str(requests.post(url, params=params).json().get("access_token"))

if __name__ == '__main__':
    main()
