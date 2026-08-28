"""
故障诊断知识库构建脚本
使用方法: python build_kb.py [--chunk_method semantic] [--chunk_size 500] [--device cpu]

数据源: knowledge_base/fault_diagnosis/data/
解析服务: parsing_service/
"""
import argparse
import os
import sys

# 添加项目根目录到路径，确保能导入 parsing_service
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.dirname(current_dir))

from vector_store import FaultDiagnosisKnowledgeBase


def main():
    parser = argparse.ArgumentParser(description="构建故障诊断知识库")
    parser.add_argument(
        "--chunk_method",
        type=str,
        default="smart",
        choices=["fixed", "sentence", "semantic", "recursive", "hybrid", "smart"],
        help="文本切分方法: fixed(固定大小), sentence(句子), semantic(语义), recursive(递归), hybrid(混合), smart(智能-推荐)"
    )
    parser.add_argument(
        "--chunk_size",
        type=int,
        default=500,
        help="切分块大小（字符数）"
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=100,
        help="切分块重叠大小（仅 fixed 方法有效）"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        choices=["cpu", "cuda"],
        help="运行设备"
    )
    parser.add_argument(
        "--model_path",
        type=str,
        default=None,
        help="BGE-M3 模型路径（可选，默认自动下载）"
    )
    parser.add_argument(
        "--source_dir",
        type=str,
        default=None,
        help="源文档目录（可选，默认为 data 子目录）"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="构建完成后进行测试搜索"
    )
    
    args = parser.parse_args()
    
    # 默认源目录
    default_source_dir = os.path.join(current_dir, "data")
    source_dir = args.source_dir or default_source_dir
    
    print("=" * 60)
    print("故障诊断知识库构建")
    print("=" * 60)
    print(f"源文档目录: {source_dir}")
    print(f"切分方法: {args.chunk_method}")
    print(f"切分大小: {args.chunk_size}")
    print(f"运行设备: {args.device}")
    print(f"模型路径: {args.model_path or '自动下载'}")
    print("=" * 60)
    
    # 检查源目录
    if not os.path.exists(source_dir):
        print(f"错误: 源文档目录不存在: {source_dir}")
        return
    
    # 列出源目录中的文件
    files = os.listdir(source_dir)
    doc_files = [f for f in files if os.path.isfile(os.path.join(source_dir, f))]
    print(f"\n发现 {len(doc_files)} 个文档文件:")
    for f in doc_files:
        file_path = os.path.join(source_dir, f)
        size = os.path.getsize(file_path) / 1024  # KB
        print(f"  - {f} ({size:.1f} KB)")
    
    if not doc_files:
        print("错误: 源目录中没有文档文件")
        return
    
    print("\n开始构建知识库...")
    
    # 构建知识库
    kb = FaultDiagnosisKnowledgeBase(
        data_dir=current_dir,
        model_path=args.model_path,
        chunk_method=args.chunk_method,
        chunk_size=args.chunk_size,
        device=args.device
    )
    
    try:
        kb.build_index(source_dir=source_dir)
        
        print("\n" + "=" * 60)
        print("知识库构建完成！")
        print(f"索引保存位置: {kb.index_dir}")
        print(f"文档总数: {kb.vector_store.index.ntotal}")
        print("=" * 60)
        
        # 测试搜索
        if args.test:
            print("\n测试搜索功能...")
            test_queries = [
                "如何上传图像进行问答？",
                "语音识别不准确怎么办？",
                "账号无法登录如何处理？",
                "多模态融合问答怎么使用？"
            ]
            
            for query in test_queries:
                print(f"\n查询: {query}")
                results = kb.search(query, top_k=2)
                for i, result in enumerate(results):
                    print(f"  {i+1}. [相似度: {result['score']:.4f}]")
                    print(f"     来源: {result['metadata'].get('source', 'unknown')}")
                    print(f"     内容: {result['document'][:80]}...")
    
    except Exception as e:
        print(f"\n构建失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
