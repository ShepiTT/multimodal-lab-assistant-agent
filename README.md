# 智能实验助手系统 (Intelligent Experiment Assistant)

本系统是一个面向实验教学与故障诊断场景的多模态智能问答系统。基于大语言模型（LLM）、检索增强生成（RAG）、多模态解析及代码执行引擎，系统旨在为用户提供涵盖实验操作指导、设备故障诊断、代码调试及文档图像解析的全方位智能辅助。

## 🌟 核心功能特性

- **🤖 多模型统一接入与调度**
  - 支持对接多种大语言模型（通义千问、火山豆包、DeepSeek、ChatGPT 等）。
  - 支持部署本地模型（如 Qwen3-1.7B）。
  - 支持多模态视觉模型（Qwen-VL 等），实现“图片+文本”的联合推理。
  - 支持模型自动降级（Fallback）机制与流式（Stream）输出。

- **📚 检索增强生成 (RAG) 知识库**
  - **智能文档解析**：支持 TXT、Markdown、PDF、DOCX、图片及视频等多种格式。
  - **OCR 与视觉提取**：集成百度 OCR、PaddleOCR、Tesseract 进行文本提取，支持视频关键帧截取。
  - **智能文本切分 (Smart Chunking)**：基于文档结构（如 Markdown 标题）、代码块保护与句子边界的智能重叠切分。
  - **高效向量检索**：基于 BGE-M3 模型进行文本嵌入（Embedding），使用 FAISS 构建高性能本地向量索引。
  - **增强查询与重排**：内置用户 Query 改写机制与基于同义词/关键词的匹配加分重排（Keyword Boost）。

- **🎤 语音交互闭环**
  - **语音识别 (ASR)**：支持百度 ASR、豆包 ASR 及本地 FunASR 模型，实现语音转文本。
  - **语音合成 (TTS)**：支持百度 TTS 与本地系统 TTS，实现回答结果的语音播报。

- **💻 内置代码执行引擎 (IDE)**
  - 基于 Docker 与 Piston 构建的沙盒代码执行环境。
  - 支持 Python、C++、Java、JS 等多种编程语言的安全在线运行。
  - 提供智能代码审查与自动 Debug 辅助。

- **🌐 联网搜索增强**
  - 接入外部搜索引擎，为大模型提供实时外部知识补充，解决知识库覆盖盲区。

## 🛠️ 技术栈

- **后端框架**: Python 3.11+, Flask
- **大模型接口**: OpenAI 兼容 API, Transformers, PyTorch
- **向量数据库**: FAISS
- **向量化模型**: BGE-M3 (`BAAI/bge-base-zh-v1.5`)
- **文档解析**: pdfplumber, PyMuPDF, python-docx, OpenCV
- **前端交互**: HTML5, CSS3, JavaScript (流式响应处理)
- **沙盒运行**: Docker, Piston API

## 📁 项目结构

```text
.
├── app.py                      # 后端主入口，路由注册与核心调度
├── config/                     # 系统提示词与全局配置文件
├── models/                     # 模型接入层
│   ├── ASR/                    # 语音识别接入模块
│   ├── TTS/                    # 语音合成接入模块
│   ├── OCR/                    # 光学字符识别模块
│   ├── LLM/                    # 大语言模型接入与调度模块
│   ├── IDE/                    # 代码执行引擎与沙盒管理
│   └── models_config.json      # 全局模型接口配置文件
├── knowledge_base/             # RAG 知识库模块
│   ├── chunking/               # 智能分块算法实现
│   ├── fault_diagnosis/        # 向量库构建与检索核心 (FAISS)
│   └── */data/                 # 各垂类知识库原始文档存放处
├── parsing_service/            # 多模态文件统一解析模块
│   ├── parser.py               # 解析调度与路由分发
│   ├── ocr_parser.py           # 文档与扫描件解析
│   └── media_parser.py         # 图像与视频关键帧解析
├── prompt_engine/              # 场景化 Prompt 动态生成引擎
├── web_search/                 # 联网搜索模块
├── ui/                         # 前端静态资源与图标
├── data/                       # 运行期产生的数据 (上传、历史记录等)
└── requirements.txt            # Python 依赖清单
```

## 🚀 快速开始

### 1. 环境准备

确保已安装 Python 3.11 及以上版本。克隆项目后，安装必要的依赖：

```bash
pip install -r requirements.txt
```

*(可选)* 如果需要运行本地大模型或本地 ASR/OCR，请安装 PyTorch 及对应深度学习库：
```bash
pip install torch torchvision torchaudio
pip install transformers sentence-transformers
```

### 2. 配置环境变量

复制 `.env.example` 文件并重命名为 `.env`，填入你需要的 API 密钥：

```env
# 通义千问
ALI_API_KEY=your_ali_key_here
# 深度求索 DeepSeek
DEEPSEEK_API_KEY=your_deepseek_key_here
# 百度语音/OCR
BAIDU_API_KEY=your_baidu_key
BAIDU_SECRET_KEY=your_baidu_secret
...
```

### 3. 启动系统

直接运行主程序即可启动 Flask 服务：

```bash
python app.py
```
*提示：系统启动时会自动尝试拉起 Docker Desktop 及 Piston 容器以支持代码执行功能。*

启动成功后，在浏览器访问：`http://127.0.0.1:5000`

## 📖 核心模块使用说明

### 知识库构建与检索
将参考文档（PDF/Word/TXT）放入对应的知识库类别目录（如 `knowledge_base/fault_diagnosis/data`）。通过前端界面触发或调用构建接口，系统会自动完成文本切分、向量化并生成 FAISS 索引。检索时会自动触发 Query 改写及重排。

### 代码沙盒调试
在交互界面中输入代码并选择执行，后端将代码交由 Piston 容器安全执行。若代码抛出异常，系统会自动提取 `stderr` 和退出码，触发 `IDE/error_handler.py` 并结合大模型给出修改建议。

## ⚠️ 注意事项

1. **依赖外部组件**：本地 ASR 需配置 `ffmpeg`；代码执行需提前安装并启动 `Docker`。
2. **显存消耗**：若在 `models_config.json` 中启用了本地 LLM 或 Qwen2-VL 多模态模型，请确保机器具备足够的 GPU 显存（建议 12GB 以上）。
3. **安全限制**：上传的文档与视频受严格的大小限制（文档 50MB，图片 10MB），请勿上传超大文件。

## 📄 许可证

本项目为学术与毕业设计研究用途开发。未经允许，请勿用于商业生产环境。
