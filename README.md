# Deep Research Agent - 论文深度研究系统

## 系统概述

一个基于多Agent协作的智能论文管理与深度研究系统，支持增量添加论文并自动进行整理、分析和知识图谱构建。

## 核心特性

- 📚 **增量式论文管理**：支持本地PDF上传和arXiv自动下载
- 🤖 **多Agent协作**：专业化分工，深度理解论文内容
- 🔍 **智能整理**：自动分类、标签化、关系发现
- 📊 **知识图谱**：构建论文引用网络和主题关联
- 📝 **自动报告**：生成Markdown研究报告
- 🌐 **交互界面**：Web界面可视化浏览和探索

## 架构设计

### Agent体系

1. **Orchestrator Agent (主控Agent)**
   - 任务调度和工作流管理
   - 维护全局知识图谱
   - 协调各子Agent工作

2. **Paper Ingestion Agent (论文摄入Agent)**
   - PDF解析和文本提取
   - arXiv论文下载
   - 元数据提取（标题、作者、摘要等）

3. **Knowledge Extractor Agent (知识提取Agent)**
   - 核心贡献提取
   - 方法论分析
   - 实验结果总结
   - 关键概念识别

4. **Relation Analyzer Agent (关系分析Agent)**
   - 引用关系追踪
   - 主题相似度计算
   - 研究脉络梳理
   - 对比分析

5. **Report Generator Agent (报告生成Agent)**
   - Markdown报告生成
   - 研究综述撰写
   - 可视化图表生成

### 技术栈

- **LLM**: Claude API / OpenAI GPT-4
- **向量数据库**: ChromaDB / FAISS
- **图数据库**: NetworkX (可扩展到Neo4j)
- **PDF处理**: PyPDF2, pdfplumber
- **Web框架**: FastAPI + Gradio/Streamlit
- **数据源**: arXiv API, Semantic Scholar API

## 项目结构

```
deepresearch/
├── agents/                 # Agent实现
│   ├── base_agent.py      # Agent基类
│   ├── orchestrator.py    # 主控Agent
│   ├── ingestion.py       # 论文摄入Agent
│   ├── extractor.py       # 知识提取Agent
│   ├── analyzer.py        # 关系分析Agent
│   └── reporter.py        # 报告生成Agent
├── core/                  # 核心功能
│   ├── pdf_parser.py     # PDF解析
│   ├── vector_store.py   # 向量存储
│   ├── knowledge_graph.py # 知识图谱
│   └── llm_client.py     # LLM接口
├── data/                  # 数据存储
│   ├── papers/           # PDF文件
│   ├── metadata/         # 论文元数据
│   ├── reports/          # 生成的报告
│   └── vector_db/        # 向量数据库
├── web/                   # Web界面
│   ├── app.py            # FastAPI应用
│   └── frontend/         # 前端资源
├── config/               # 配置文件
│   └── config.yaml
├── requirements.txt
└── main.py              # 入口文件
```

## 快速开始

### 安装依赖
```bash
pip install -r requirements.txt
```

### 配置API密钥
```bash
cp config/config.example.yaml config/config.yaml
# 编辑config.yaml，填入API密钥
```

### 运行系统
```bash
# 启动Web界面
python main.py --mode web

# 命令行模式添加论文
python main.py --add-paper /path/to/paper.pdf

# 从arXiv添加
python main.py --arxiv 2301.00001
```

## 工作流程

1. **添加论文** → 上传PDF或输入arXiv ID
2. **自动解析** → Paper Ingestion Agent提取内容
3. **知识提取** → Knowledge Extractor Agent分析论文
4. **关系建立** → Relation Analyzer Agent发现关联
5. **报告生成** → Report Generator Agent整理输出
6. **可视化** → Web界面展示知识图谱

## 许可证

MIT License
