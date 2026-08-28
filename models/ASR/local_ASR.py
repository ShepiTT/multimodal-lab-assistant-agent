from funasr import AutoModel

# 使用本地缓存的模型路径，避免每次联网检查或重新下载
model = AutoModel(
    model=r"C:\Users\56445\.cache\modelscope\hub\models\iic\speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",  # ASR
    vad_model=r"C:\Users\56445\.cache\modelscope\hub\models\iic\speech_fsmn_vad_zh-cn-16k-common-pytorch",                              # VAD
    punc_model=r"C:\Users\56445\.cache\modelscope\hub\models\iic\punc_ct-transformer_cn-en-common-vocab471067-large",                   # 标点
    disable_update=True,  # 关闭版本检查
)

def main(audio_path):
    """识别音频文件并返回结果"""
    res = model.generate(input=audio_path)
    return res

if __name__ == "__main__":
    # 仅在直接运行时执行测试
    res = model.generate(input=r"D:\lxx_py\毕业设计\test\ASR\test_data\长视频测试.wav")

    # 写入文本文件（UTF-8）
    output_txt = r"D:\lxx_py\毕业设计\test\ASR\test_data\长视频测试.txt"
    with open(output_txt, "w", encoding="utf-8") as f:
        f.write(res[0]["text"])

    print(f"识别文本已保存到：{output_txt}")
