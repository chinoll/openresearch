# Deep Research Agent 架构设计文档

## 一、系统概述

Deep Research Agent 是一个基于多 Agent 协作的智能论文管理与深度研究系统。核心特点是**优先使用 TeX 源文件**进行论文分析，从而获取比 PDF 更丰富的结构化信息。

## 二、核心设计理念

### 2.1 TeX 源文件优先策略

**为什么优先 TeX？**

1. **结构化信息丰富**
   - 章节层级：`\section`, `\subsection`, `\subsubsection`
   - 语义标记：`\cite{}`, `\label{}`, `\ref{}`
   - 公式环境：`\equation`, `\align`, `\gather`
   - 图表说明：`\caption{}`, `\label{}`

2. **元数据完整**
   - 直接提取引用关系（`\cite{}`）
   - 保留作者的组织逻辑
   - 包含注释中的思考过程

3. **解析准确性高**
   - 避免 PDF 格式问题（列、表格、公式）
   - 无需 OCR 或复杂的布局分析
   - 保留原始语义

**降级策略**：当 TeX 源不可用时（约 30% 的论文），自动降级到 PDF 解析。

---

## 三、系统架构

### 3.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     用户交互层                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ CLI 命令行   │  │  Web 界面    │  │  API 接口    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                   主控层 (Orchestrator)                      │
│  - 任务调度  - 工作流管理  - 知识图谱维护                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼────┐  ┌──────▼────┐  ┌─────▼──────┐
│  Paper     │  │ Knowledge │  │ Relation   │
│  Ingestion │  │ Extractor │  │ Analyzer   │
│  Agent     │  │ Agent     │  │ Agent      │
└────────────┘  └───────────┘  └────────────┘
     │               │                │
     │ TeX/PDF       │ 提取核心信息    │ 构建关系
     │ 解析          │                │
     ▼               ▼                ▼
┌─────────────────────────────────────────────────────────────┐
│                      数据存储层                              │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌──────────┐  │
│  │ 原始文件 │  │ 向量数据库│  │ 知识图谱 │  │ 元数据库 │  │
│  │ TeX/PDF  │  │ ChromaDB  │  │ NetworkX │  │   JSON   │  │
│  └──────────┘  └───────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Agent 分工

#### Agent 1: Paper Ingestion Agent（论文摄入 Agent）

**职责**：
- 下载论文（arXiv、本地上传）
- 优先获取 TeX 源文件
- 解析 TeX/PDF 内容
- 初步结构化

**输入**：
```json
{
  "source": "arxiv",
  "identifier": "2301.00001"
}
```

**输出**：
```json
{
  "title": "论文标题",
  "authors": ["作者1", "作者2"],
  "abstract": "摘要内容",
  "sections": [...],
  "citations": [...],
  "equations": [...],
  "source_type": "tex",
  "file_path": "/path/to/source"
}
```

#### Agent 2: Knowledge Extractor Agent（知识提取 Agent）

**职责**：
- 深度分析论文内容
- 提取核心贡献
- 识别方法论
- 总结实验结果
- 识别局限性

**关键提示词模板**：
```
分析以下论文，提取：
1. 核心研究问题
2. 主要贡献（创新点）
3. 使用的方法和技术
4. 实验设置和结果
5. 局限性和未来工作
```

#### Agent 3: Relation Analyzer Agent（关系分析 Agent）

**职责**：
- 分析引用关系
- 计算论文相似度
- 识别研究脉络
- 发现主题聚类
- 对比分析

**分析维度**：
- **引用网络**：构建前向/后向引用图
- **主题相似度**：基于向量化的语义相似度
- **时间演进**：研究领域的发展时间线
- **方法对比**：不同论文的方法异同

#### Agent 4: Report Generator Agent（报告生成 Agent）

**职责**：
- 生成 Markdown 报告
- 创建可视化图表
- 撰写研究综述
- 生成知识图谱视图

**输出格式**：
1. **单篇论文报告**：详细分析单篇论文
2. **主题综述报告**：多篇论文的对比分析
3. **研究脉络报告**：领域发展历程
4. **可视化报告**：交互式图表和知识图谱

---

## 四、核心技术组件

### 4.1 TeX 解析器 (`core/tex_parser.py`)

**功能**：
- 查找主 `.tex` 文件
- 提取文档结构（章节、段落）
- 解析数学公式
- 提取引用和标签
- 提取图表说明
- 捕获作者注释

**关键方法**：
```python
class TeXParser:
    def find_main_tex_file(source_dir) -> Path
    def parse_file(tex_path) -> TexDocument
    def _extract_title(content) -> str
    def _extract_sections(content) -> List[Dict]
    def _extract_citations(content) -> List[str]
    def _extract_equations(content) -> List[str]
```

### 4.2 arXiv 下载器 (`core/arxiv_downloader.py`)

**功能**：
- 支持多种 arXiv ID 格式识别
- 优先下载 TeX 源文件（.tar.gz）
- 自动解压和文件管理
- 获取论文元数据
- PDF 降级下载

**下载流程**：
```
输入 arXiv ID
    ↓
提取规范化 ID (2301.00001)
    ↓
获取元数据 (title, authors, abstract)
    ↓
尝试下载 TeX 源 (https://arxiv.org/e-print/ID)
    ↓
   成功？
    ├─ 是 → 解压 .tar.gz → 返回 TeX 目录
    └─ 否 → 下载 PDF → 返回 PDF 路径
```

### 4.3 向量数据库（Vector Store）

**选择**：ChromaDB（轻量级）或 FAISS（高性能）

**用途**：
- 论文向量化存储
- 语义相似度搜索
- 主题聚类
- 相关论文推荐

**嵌入模型**：`sentence-transformers/all-MiniLM-L6-v2`

### 4.4 知识图谱（Knowledge Graph）

**实现**：NetworkX（可扩展到 Neo4j）

**节点类型**：
- **论文节点**：包含元数据、摘要、关键词
- **作者节点**：作者信息、合作关系
- **概念节点**：研究主题、方法、技术

**边类型**：
- **引用边**：A 引用 B
- **相似边**：主题相似度
- **作者边**：合著关系
- **演进边**：技术演进

---

## 五、数据流

### 5.1 增量添加论文流程

```
用户输入 arXiv ID
    ↓
Paper Ingestion Agent
    ├─ 下载 TeX 源（优先）或 PDF
    ├─ 解析内容 → TexDocument
    ├─ LLM 分析 → AI Insights
    └─ 保存元数据 → JSON
    ↓
Knowledge Extractor Agent
    ├─ 提取核心概念
    ├─ 识别方法论
    └─ 生成向量嵌入
    ↓
Relation Analyzer Agent
    ├─ 查找引用论文
    ├─ 计算相似度
    └─ 更新知识图谱
    ↓
Report Generator Agent
    ├─ 生成单篇报告
    └─ 更新总体知识库
```

### 5.2 查询和分析流程

```
用户查询
    ↓
向量数据库检索
    ├─ 语义搜索相关论文
    └─ 返回 Top-K 结果
    ↓
知识图谱遍历
    ├─ 查找引用网络
    └─ 识别研究路径
    ↓
LLM 综合分析
    ├─ 对比多篇论文
    ├─ 总结研究趋势
    └─ 生成综述报告
```

---

## 六、文件结构

```
deepresearch/
├── agents/                   # Agent 实现
│   ├── __init__.py
│   ├── base_agent.py        # Agent 基类
│   ├── orchestrator.py      # 主控 Agent（待实现）
│   ├── ingestion.py         # ✓ 论文摄入 Agent
│   ├── extractor.py         # 知识提取 Agent（待实现）
│   ├── analyzer.py          # 关系分析 Agent（待实现）
│   └── reporter.py          # 报告生成 Agent（待实现）
│
├── core/                     # 核心功能模块
│   ├── __init__.py
│   ├── tex_parser.py        # ✓ TeX 解析器
│   ├── arxiv_downloader.py  # ✓ arXiv 下载器
│   ├── pdf_parser.py        # PDF 解析器（待实现）
│   ├── vector_store.py      # 向量数据库（待实现）
│   ├── knowledge_graph.py   # 知识图谱（待实现）
│   └── llm_client.py        # LLM 客户端（待实现）
│
├── data/                     # 数据存储
│   ├── papers/
│   │   ├── tex_sources/     # TeX 源文件目录
│   │   └── pdfs/            # PDF 文件目录
│   ├── metadata/            # 论文元数据（JSON）
│   ├── reports/             # 生成的报告
│   └── vector_db/           # 向量数据库文件
│
├── web/                      # Web 界面（待实现）
│   ├── app.py               # FastAPI 应用
│   └── frontend/            # 前端资源
│
├── config/                   # 配置文件
│   └── config.example.yaml  # ✓ 配置示例
│
├── tests/                    # 测试用例
│   └── ...
│
├── main.py                   # ✓ 主入口
├── requirements.txt          # ✓ 依赖列表
├── README.md                 # ✓ 项目说明
└── ARCHITECTURE.md           # ✓ 本文档
```

---

## 七、使用场景示例

### 场景 1：单篇论文深度分析

```bash
# 添加论文
python main.py --arxiv 2301.00001

# 系统自动：
# 1. 下载 TeX 源文件
# 2. 解析结构（章节、公式、引用）
# 3. AI 分析（核心贡献、方法、局限）
# 4. 生成报告
```

### 场景 2：研究领域综述

```python
# 批量添加相关论文
papers = [
    "2301.00001",
    "2302.12345",
    "2303.54321"
]

for paper_id in papers:
    system.add_paper_from_arxiv(paper_id)

# 生成综述报告
report = system.generate_survey_report(
    topic="Transformer Architecture",
    papers=papers
)
```

### 场景 3：引用网络分析

```python
# 分析某篇论文的引用网络
network = system.analyze_citation_network(
    arxiv_id="2301.00001",
    depth=2  # 二跳引用
)

# 可视化引用图
network.visualize()
```

---

## 八、技术选型理由

### 8.1 为什么选择多 Agent 架构？

1. **专业化分工**：每个 Agent 专注特定任务
2. **可扩展性**：易于添加新功能 Agent
3. **并行处理**：多个 Agent 可并行工作
4. **模块化**：便于测试和维护

### 8.2 为什么优先 TeX？

1. **信息完整性**：TeX 包含更多语义信息
2. **解析准确性**：避免 PDF 格式问题
3. **作者意图**：保留原始组织逻辑
4. **可用性**：约 70% 的 CS 论文提供 TeX 源

### 8.3 LLM 选择

- **Claude API**：长上下文、强推理能力
- **适合**：复杂论文分析、综述撰写
- **可替换**：支持 OpenAI、本地模型

---

## 九、未来扩展方向

### 9.1 功能扩展

- [ ] 支持更多论文源（Semantic Scholar、PubMed）
- [ ] 多语言论文支持
- [ ] 自动化文献综述生成
- [ ] 研究空白识别
- [ ] 实验结果对比分析

### 9.2 性能优化

- [ ] 异步并发处理
- [ ] 缓存机制
- [ ] 增量更新知识图谱
- [ ] GPU 加速向量计算

### 9.3 用户体验

- [ ] 交互式 Web 界面
- [ ] 可视化知识图谱浏览
- [ ] 自然语言查询
- [ ] 个性化推荐

---

## 十、总结

Deep Research Agent 通过**优先使用 TeX 源文件**和**多 Agent 协作**，实现了比传统方法更深入、更准确的论文分析。系统采用增量式设计，支持逐步添加论文并自动构建知识网络，为研究人员提供智能化的文献管理和深度研究工具。
