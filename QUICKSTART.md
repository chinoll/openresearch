# Deep Research Agent - 快速开始指南

## 🚀 5分钟快速上手

### 1. 安装依赖

```bash
cd /mnt/d/GenAICode/deepresearch
pip install -r requirements.txt
```

### 2. 配置（可选）

如果你想使用 AI 分析功能，需要配置 API 密钥：

```bash
# 复制配置模板
cp config/config.example.yaml config/config.yaml

# 编辑配置文件
nano config/config.yaml
```

在 `config.yaml` 中设置你的 API 密钥：

```yaml
llm:
  provider: "anthropic"
  api_key: "YOUR_ANTHROPIC_API_KEY_HERE"
  # 或使用 OpenAI
  # provider: "openai"
  # api_key: "YOUR_OPENAI_API_KEY_HERE"
```

**提示**：如果没有 API 密钥，系统仍可运行，但会跳过 AI 分析部分。

### 3. 开始使用

#### 添加第一篇论文

```bash
# 从 arXiv 添加论文（推荐 - 自动下载 TeX 源文件）
python main.py --arxiv 2301.00001

# 或使用完整 URL
python main.py --arxiv https://arxiv.org/abs/2401.12345

# 从本地添加 TeX 文件
python main.py --local /path/to/paper.tex

# 从本地添加 PDF 文件
python main.py --local /path/to/paper.pdf
```

#### 快速模式（仅摄入，不做深度分析）

```bash
python main.py --arxiv 2301.00001 --quick
```

#### 查看已添加的论文

```bash
python main.py --list
```

#### 查看系统统计

```bash
python main.py --stats
```

#### 搜索论文

```bash
python main.py --search "transformer attention mechanism"
```

---

## 📊 系统工作流程

当你添加一篇论文时，系统会自动执行以下流程：

```
1️⃣ 论文摄入 (Paper Ingestion)
   ├─ 尝试下载 TeX 源文件 ✨
   ├─ 如果失败，下载 PDF
   └─ 解析并提取结构化信息

2️⃣ 知识提取 (Knowledge Extraction)
   ├─ 提取核心贡献
   ├─ 识别研究方法
   ├─ 总结主要发现
   ├─ 识别局限性
   └─ 提取关键词和概念

3️⃣ 知识库构建
   ├─ 添加到向量数据库（语义搜索）
   └─ 添加到知识图谱（关系网络）

4️⃣ 关系分析 (Relation Analysis)
   ├─ 分析引用关系
   ├─ 发现相似论文
   ├─ 识别研究主题
   └─ 评估影响力
```

---

## 💡 使用示例

### 示例 1: 研究某个主题

```bash
# 添加几篇相关论文
python main.py --arxiv 1706.03762  # Attention Is All You Need
python main.py --arxiv 1810.04805  # BERT
python main.py --arxiv 2005.14165  # GPT-3

# 查看系统发现的关系
python main.py --stats

# 搜索相关主题
python main.py --search "pre-training language models"
```

### 示例 2: 追踪研究脉络

添加一篇论文后，系统会自动：
- 识别它引用的论文
- 发现语义相似的论文
- 分析它在研究时间线中的位置

### 示例 3: 快速浏览论文集合

```bash
# 快速添加多篇论文（跳过深度分析，节省时间）
python main.py --arxiv 2301.00001 --quick
python main.py --arxiv 2302.12345 --quick
python main.py --arxiv 2303.54321 --quick

# 然后查看列表
python main.py --list

# 对感兴趣的论文进行深度分析（TODO: 未来功能）
# python main.py --analyze 2301.00001
```

---

## 🎯 TeX 源文件的优势

系统优先使用 TeX 源文件，因为它提供：

1. **更准确的结构**
   - 章节层级：`\section`, `\subsection`
   - 引用关系：`\cite{key}`
   - 公式标记：`\equation`, `\align`

2. **更丰富的元数据**
   - 图表说明：`\caption{}`
   - 交叉引用：`\ref{}`
   - 作者注释：`% comments`

3. **更高的准确性**
   - 避免 PDF 格式问题
   - 无需 OCR
   - 保留原始语义

**覆盖率**：约 70% 的计算机科学论文提供 TeX 源文件。
**降级策略**：如果 TeX 不可用，自动降级到 PDF。

---

## 📁 数据存储

系统会在 `data/` 目录下存储所有数据：

```
data/
├── papers/
│   ├── tex_sources/     # TeX 源文件（按论文 ID 分组）
│   │   └── 2301_00001/
│   │       ├── main.tex
│   │       ├── figures/
│   │       └── ...
│   └── pdfs/            # PDF 文件
│       └── 2301_00001.pdf
│
├── metadata/            # 论文元数据（JSON）
│   └── 2301_00001.json
│
├── vector_db/           # 向量数据库（ChromaDB）
│   └── ...
│
└── knowledge_graph.pkl  # 知识图谱
```

---

## 🔧 常见问题

### Q1: 没有 API 密钥可以使用吗？

可以！系统会跳过 AI 分析部分，但仍会：
- 下载和解析论文
- 提取结构化信息（章节、引用、公式）
- 构建向量数据库和知识图谱（使用开源嵌入模型）

### Q2: TeX 源文件下载失败怎么办？

系统会自动降级到 PDF。不影响使用。

### Q3: 如何查看某篇论文的详细分析？

查看 `data/metadata/<paper_id>.json` 文件，包含完整的分析结果。

### Q4: 如何删除论文？

目前需要手动删除：
- `data/papers/` 中的源文件
- `data/metadata/` 中的 JSON 文件
- 可选：重新初始化向量数据库和知识图谱

### Q5: 支持哪些论文源？

目前支持：
- ✅ arXiv（推荐）
- ✅ 本地 TeX 文件
- ✅ 本地 PDF 文件
- 🚧 Semantic Scholar（计划中）
- 🚧 PubMed（计划中）

---

## 🎓 进阶使用

### Python API 使用

```python
import asyncio
from pathlib import Path
from main import DeepResearchSystem

async def main():
    # 初始化系统
    system = DeepResearchSystem(config_path=Path("config/config.yaml"))

    # 添加论文
    result = await system.add_paper_from_arxiv("2301.00001")

    # 搜索
    results = await system.search_papers("transformer", top_k=5)

    # 查看统计
    stats = system.orchestrator.get_statistics()
    print(stats)

asyncio.run(main())
```

### 直接使用 Orchestrator

```python
from agents.orchestrator import OrchestratorAgent
from agents.base_agent import AgentConfig

config = AgentConfig(
    name="MyOrchestrator",
    model="claude-sonnet-4-5-20250929",
    api_key="your-api-key"
)

orchestrator = OrchestratorAgent(
    config=config,
    data_dir=Path("./data/papers"),
    vector_db_path=Path("./data/vector_db"),
    graph_path=Path("./data/knowledge_graph.pkl")
)

# 添加论文
result = await orchestrator.add_paper(
    source='arxiv',
    identifier='2301.00001',
    full_analysis=True
)

# 对比论文
comparison = await orchestrator.compare_papers([
    'paper1_id',
    'paper2_id'
])
```

---

## 📚 下一步

- 📖 阅读 [ARCHITECTURE.md](ARCHITECTURE.md) 了解系统架构
- 🔍 查看 [README.md](README.md) 了解完整功能
- 💻 探索 `agents/` 目录了解各个 Agent 的实现

---

## 🆘 获取帮助

- 查看文档：`README.md` 和 `ARCHITECTURE.md`
- 查看示例代码：每个模块的 `__main__` 部分
- 检查配置：`config/config.example.yaml`

祝你研究愉快！🎉
