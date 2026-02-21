# OpenResearch - 论文深度研究系统

基于多 Agent 协作的智能论文管理与深度研究系统。支持 arXiv 论文自动下载（TeX 源文件优先）、LLM 驱动的知识提取与关系分析、向量数据库 + 知识图谱双存储，并通过 CLI、REST API、终端 TUI 和 Web UI 四种方式提供交互。

## 核心特性

- **TeX-First 解析** — 优先下载 arXiv TeX 源文件（覆盖约 70%），提取结构化内容（章节、公式、引用、注释），PDF 作为降级方案
- **多 Agent 流水线** — Orchestrator 协调 Ingestion → Extraction → Analysis 三阶段，每个 Agent 独立负责特定任务
- **插件注册系统** — 所有 Agent、Core Service、Manager、Router 通过声明 `REGISTRATION` 类属性自动发现、依赖注入、暴露为 API 工具
- **双存储引擎** — ChromaDB 向量数据库（语义搜索）+ NetworkX 知识图谱（引用关系、相似度、主题聚类）
- **洞察 / 疑问 / 想法** — 阅读过程中记录 Insights、Questions、Ideas，支持版本演进和 AI 综合分析
- **多端界面** — CLI、FastAPI REST API（`/docs` 自动文档）、Ink.js 终端 TUI、React + Vite Web UI

## 项目结构

```
deepresearch/
├── main.py                    # CLI 入口
├── config/
│   └── config.example.yaml    # 配置模板
├── plugins/                   # 按领域组织的插件（服务 + Agent + 路由共存）
│   ├── papers/                # 论文领域
│   │   ├── downloader.py      # arXiv 下载器（TeX 优先）
│   │   ├── tex_parser.py      # TeX 解析器（结构化提取）
│   │   ├── agent.py           # 论文摄入 Agent
│   │   └── router.py          # /api/papers
│   ├── knowledge/             # 知识库领域
│   │   ├── vector_store.py    # ChromaDB 向量存储
│   │   ├── knowledge_graph.py # NetworkX 知识图谱
│   │   ├── extractor_agent.py # 知识提取 Agent
│   │   └── analyzer_agent.py  # 关系分析 Agent
│   ├── insights/              # 洞察领域
│   │   ├── manager.py         # 洞察管理
│   │   └── router.py          # /api/insights
│   ├── questions/             # 疑问领域
│   │   ├── manager.py         # 疑问管理
│   │   └── router.py          # /api/questions
│   ├── ideas/                 # 想法领域
│   │   ├── manager.py         # 想法管理
│   │   ├── structured.py      # 结构化想法
│   │   ├── agent.py           # 洞察 Agent
│   │   └── router.py          # /api/ideas
├── core/                      # 共享基础设施 + 编排
│   ├── registry.py            # 模块注册中心（插件系统核心）
│   ├── registration.py        # @register_module 装饰器 + agent_factory
│   ├── base_agent.py          # Agent 基类（LLM 客户端、对话记忆）
│   ├── orchestrator.py        # 主控 Agent（流水线协调、LLM 智能路由）
│   └── chat_router.py         # /api/chat（AI 对话 + Tool Use）
├── backend/                   # FastAPI 后端框架
│   ├── main.py                # 应用入口 + 路由注册
│   └── tools.py               # Registry → Anthropic tool_use 工具定义生成
├── prompts/                   # LLM 提示词模板
│   ├── loader.py              # {{variable}} 模板加载器
│   ├── system/                # 系统提示词
│   ├── ingestion/             # 摄入 Agent 提示词
│   ├── extractor/             # 提取 Agent 提示词
│   ├── analyzer/              # 分析 Agent 提示词
│   └── insight/               # 洞察 Agent 提示词
├── ui/                        # 前端界面
│   ├── shared/                # 共享层（API client、类型、命令定义）
│   ├── tui/                   # Ink.js 终端 TUI
│   └── web/                   # React + Vite + Tailwind Web UI
├── scripts/                   # 独立 CLI 脚本
│   ├── ideas_cli.py
│   ├── insights_cli.py
│   ├── questions_cli.py
│   └── structured_ideas_cli.py
└── data/                      # 运行时数据（gitignore）
    ├── papers/                # 论文文件 + 元数据
    ├── vector_db/             # ChromaDB 数据
    └── knowledge_graph.pkl    # 知识图谱持久化
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

```bash
cp config/config.example.yaml config/config.yaml
# 编辑 config.yaml，设置 API 密钥
```

默认 LLM 为 `claude-sonnet-4-5-20250929`，支持 Anthropic 和 OpenAI。

### 3. CLI 使用

```bash
python main.py --arxiv 2301.00001              # 添加 arXiv 论文（完整分析）
python main.py --arxiv 2301.00001 --quick       # 快速模式（仅摄入）
python main.py --local /path/to/paper.pdf       # 添加本地文件
python main.py --list                           # 列出论文
python main.py --stats                          # 系统统计
python main.py --search "transformer attention"  # 语义搜索
```

### 4. FastAPI 后端

```bash
python -m uvicorn backend.main:app --reload --port 8000
# API 文档: http://localhost:8000/docs
# 注册中心: http://localhost:8000/api/registry
```

### 5. 终端 TUI

```bash
cd ui && npm install
npm run tui
```

### 6. Web UI

```bash
cd ui/web && npm install
npm run dev    # http://localhost:5173
```

## 架构

### 多 Agent 流水线

```
Orchestrator Agent
  │
  ├─ Step 1: Ingestion Agent
  │    ArxivDownloader → TeX/PDF → TeXParser → 结构化论文数据
  │
  ├─ Step 2: Extractor Agent
  │    论文数据 → LLM → 贡献/方法/关键词/发现/局限
  │
  ├─ Step 3: Knowledge Base
  │    ChromaDB（向量索引）+ NetworkX（知识图谱）
  │
  └─ Step 4: Analyzer Agent
       引用分析 + 相似度计算 + 主题聚类 + 演进追踪
```

### 插件注册系统 (Registry)

所有模块通过类属性 `REGISTRATION = ModuleRegistration(...)` 声明元数据，Registry 自动发现并管理：

```python
class PaperIngestionAgent(BaseAgent):
    REGISTRATION = ModuleRegistration(
        name="paper_ingestion",
        module_type=ModuleType.AGENT,
        pipeline_stage="ingestion",
        pipeline_order=10,
        dependencies=[
            DependencySpec(name="arxiv_downloader"),
            DependencySpec(name="tex_parser"),
        ],
        constructor_params=[
            ConstructorParam(name="download_dir", from_config="storage.papers"),
        ],
        capabilities=[
            Capability(name="ingest_arxiv", description="从 arXiv 下载并解析论文"),
        ],
    )
```

- **自动发现**: `registry.auto_discover(['plugins', 'core'])` 扫描所有包
- **依赖注入**: `registry.get_instance(name, config)` 递归解析 `DependencySpec`，从 config 读取 `ConstructorParam`
- **工具生成**: `generate_tools_from_registry()` 自动将 Router Capability 转换为 Anthropic tool_use 格式
- **LLM 路由**: `describe_capabilities()` 生成能力描述文本，供 Orchestrator 智能路由未知命令

### REST API

| 端点 | 功能 |
|------|------|
| `POST /api/papers/download` | 下载 arXiv 论文 |
| `GET /api/papers` | 列出论文 |
| `GET /api/papers/{id}` | 论文详情 |
| `POST /api/insights` | 创建洞察 |
| `POST /api/questions` | 创建疑问 |
| `POST /api/ideas` | 创建想法 |
| `POST /api/chat` | AI 对话（Tool Use 流式返回） |
| `GET /api/stats` | 全局统计 |
| `GET /api/registry` | 注册中心信息 |

### 提示词模板

所有 LLM 提示词集中管理在 `prompts/` 目录，使用 `{{variable}}` 占位符：

```python
from prompts.loader import load as load_prompt
prompt = load_prompt("extractor/contributions", title="...", abstract="...")
```

## 工作流

1. **添加论文** — 输入 arXiv ID 或本地文件路径
2. **自动解析** — Ingestion Agent 下载 TeX 源文件并提取结构化内容
3. **知识提取** — Extractor Agent 通过 LLM 分析贡献、方法、关键词
4. **知识构建** — 添加到向量数据库和知识图谱
5. **关系分析** — Analyzer Agent 发现引用关系、相似论文、主题聚类
6. **交互探索** — 通过 CLI/API/TUI/Web 查询、搜索、对比论文

## 许可证

MIT License
