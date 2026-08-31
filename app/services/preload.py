"""模型预加载：加速首次请求响应。仅由入口脚本调用，不阻塞测试与工具导入。"""
from .. import runtime
from .kb import get_kb_instance


def preload_models(preload_vl: bool = False):
    """
    预加载模型，加速首次请求响应

    Args:
        preload_vl: 是否预加载本地多模态模型（占用较多显存）
    """
    print("\n" + "=" * 50)
    print("正在预加载模型...")
    print("=" * 50)

    # 1. 预加载知识库（包括向量化模型）
    if runtime.KB_AVAILABLE:
        print("\n[预加载] 知识库模块...")
        for kb_type in ['guide', 'diagnosis', 'safety']:
            try:
                kb = get_kb_instance(kb_type)
                if kb and kb.vector_store and kb.vector_store.index.ntotal > 0:
                    print(f"  ✓ {kb_type}: 已加载 {kb.vector_store.index.ntotal} 个文档块")
                else:
                    print(f"  - {kb_type}: 索引为空或未构建")
            except Exception as e:
                print(f"  ✗ {kb_type}: 加载失败 - {e}")
    else:
        print("\n[预加载] 知识库模块不可用")

    # 2. 预加载语音识别模型
    if runtime.asr_recognize:
        print("\n[预加载] 语音识别模型...")
        try:
            from models.ASR.asr_runner import preload_model
            preload_model()
            print("  ✓ ASR 模型加载成功")
        except ImportError:
            print("  - ASR 模型无预加载函数，将在首次使用时加载")
        except Exception as e:
            print(f"  ✗ ASR 模型加载失败: {e}")
    else:
        print("\n[预加载] 语音识别模块不可用")

    # 3. 预加载本地多模态模型（可选，占用较多显存）
    if preload_vl:
        print("\n[预加载] 本地多模态模型...")
        try:
            from models.LLM.local_LLM_VL import preload_model as preload_vl_model
            preload_vl_model()
            print("  ✓ 本地多模态模型加载成功")
        except ImportError:
            print("  - 本地多模态模型模块未安装")
        except Exception as e:
            print(f"  ✗ 本地多模态模型加载失败: {e}")
    else:
        print("\n[预加载] 本地多模态模型: 跳过（首次使用时加载）")

    print("\n" + "=" * 50)
    print("预加载完成！")
    print("=" * 50 + "\n")
