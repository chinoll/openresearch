# OpenResearch - 多 Agent 论文研究平台

基于 LLM 驱动的多 Agent 论文管理与深度研究系统。支持 arXiv 论文自动下载（TeX 源文件优先）、知识提取与关系分析、向量数据库 + 知识图谱双存储，通过 CLI、REST API、终端 TUI 和 Web UI 四种方式交互。

所有任务编排由 LLM 通过 tool-use 自主完成——无固定流水线，无硬编码步骤。

## 核心特性

- **LLM 自主编排** — 零领域知识的 TaskSystem，由 LLM 决定调用哪些工具、什么顺序
- **Agent Team 协作** — 多 Agent 组队协同（LLM 协调 + 共享黑板），支持预定义 Team 和动态组队
- **递归 Chat** — Team 内 agent 拥有完整 tool-use chat 能力，自主调工具、启子 Team、嵌套研究
- **TeX-First 解析** — 优先下载 arXiv TeX 源文件（约 70%），提取结构化内容，PDF 作为降级方案
- **插件自动发现** — 所有 Agent、工具、路由通过 `REGISTRATION` 声明，Registry 自动注册、暴露为 API
- **双存储引擎** — ChromaDB 向量数据库（语义搜索）+ NetworkX 知识图谱（引用、相似度、主题聚类）
- **多端界面** — CLI、FastAPI REST API（`/docs`）、Ink.js 终端 TUI、React + Vite Web UI

## 项目结构

```
deepresearch/
├── main.py                    # CLI 入口（TaskSystem: LLM + ToolUseRunner）
├── config/
│   └── config.example.yaml    # 配置模板
├── core/                      # 共享基础设施
│   ├── registry.py            # 模块注册中心（自动发现、ModuleType: TOOL/SUBAGENT/ROUTER）
│   ├── registration.py        # @register_module 装饰器 + agent_factory
│   ├── base_agent.py          # Agent 基类（LLM 客户端、call_llm、call_llm_structured）
│   ├── tool_use_runner.py     # 通用 Anthropic tool-use 循环执行器
│   ├── chat_router.py         # /api/chat（AI 对话 + Tool Use）+ 内置 Team 工具
│   ├── team.py                # Agent Team 引擎（黑板、协调者、执行引擎、工厂）
│   ├── team_schemas.py        # Coordinator 决策 JSON Schema
│   ├── recursive_chat.py      # 递归 Chat 引擎（Team agent 的通用执行环境）
│   └── config.py              # 统一 LLM 配置加载
├── plugins/                   # 按领域组织的插件
│   ├── papers/                # 论文领域
│   │   ├── downloader.py      # arXiv 下载器（TeX 优先）
│   │   ├── tex_parser.py      # TeX 解析器
│   │   ├── agent.py           # PaperIngestionAgent
│   │   └── router.py          # /api/papers
│   ├── knowledge/             # 知识库领域
│   │   ├── vector_store.py    # ChromaDB 向量存储
│   │   ├── knowledge_graph.py # NetworkX 知识图谱
│   │   ├── extractor_agent.py # KnowledgeExtractorAgent
│   │   ├── analyzer_agent.py  # RelationAnalyzerAgent
│   │   ├── schemas.py         # 提取任务 JSON Schema
│   │   └── teams.py           # Team 定义（knowledge_review）
│   ├── insights/              # 洞察领域
│   ├── questions/             # 疑问领域
│   └── ideas/                 # 想法领域
├── backend/                   # FastAPI 后端
│   ├── main.py                # 应用入口 + 路由自动挂载
│   └── tools.py               # Registry → Anthropic tool_use 定义生成
├── prompts/                   # LLM 提示词模板（{{variable}} 替换）
│   ├── system/                # 系统提示词
│   ├── team/                  # Team 协调者提示词
│   ├── extractor/             # 知识提取提示词
│   ├── analyzer/              # 关系分析提示词
│   └── ...
├── ui/
│   ├── shared/                # 共享层（API client、类型定义）
│   ├── tui/                   # Ink.js 终端 TUI
│   └── web/                   # React + Vite + Tailwind Web UI
└── data/                      # 运行时数据（gitignore）
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

支持通过环境变量覆盖：`LLM_PROVIDER`、`LLM_MODEL`、`LLM_API_KEY`、`LLM_BASE_URL`。

### 3. CLI 使用

```bash
python main.py                        # 交互式 chat（LLM 自主编排）
python main.py "你的任务描述"           # 单次任务执行
python main.py --server               # 启动 FastAPI 服务（端口 8000）
```

### 4. FastAPI 后端

```bash
python -m uvicorn backend.main:app --reload --port 8000
# API 文档: http://localhost:8000/docs
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

### LLM 自主编排

无固定流水线——LLM 通过 tool-use 自主决定调用哪些工具、什么顺序：

```
用户输入
  └─ TaskSystem / ChatRouter
       └─ ToolUseRunner（tool-use 循环）
            ├─ ingest_paper      → PaperIngestionAgent
            ├─ extract_knowledge → KnowledgeExtractorAgent
            ├─ search_papers     → VectorStore
            ├─ analyze_relations → RelationAnalyzerAgent
            ├─ run_team          → Agent Team 协作
            └─ ...（所有插件工具自动注册）
```

### Agent Team 协作

多 Agent 组队协同完成复杂任务，由 LLM Coordinator 协调：

```
run_team(team_name, task)
  └─ Team.run()
       ├─ Coordinator（LLM 决策）→ delegate / terminate
       ├─ 共享黑板（TeamContext）— 成员间数据传递
       └─ 成员执行
            └─ TeamAgentWrapper.process()
                 ├─ depth < max → 递归 Chat（完整工具权限）
                 └─ depth ≥ max → call_llm（纯推理）
```

- **Form 1**（同插件）：同一 agent 类，不同 system prompt 扮演不同角色
- **Form 2**（跨插件）：不同插件的 agent 协作，通过 `team_export` 声明

### 递归 Chat

Team 内的 agent 不是简单调一次 LLM——而是启动一轮完整的 tool-use chat，LLM 自主决定：

```
TeamAgentWrapper.process(instruction)
  └─ run_recursive_chat(query, context=父Team任务, depth)
       └─ ToolUseRunner（所有工具 + research）
            ├─ 调工具（search_papers, extract...）
            ├─ 启子 Team（run_team，自行决定是否传父任务）
            ├─ 嵌套 research（depth+1，更深层递归）
            └─ 或直接推理回答
```

- **递归深度**：`max_recursion_depth`（默认 2），depth ≥ max 退化为纯推理
- **记忆隔离**：递归 chat 对话历史在返回后丢弃，只保留结果 + 元摘要
- **父任务感知**：父 Team 的 task_description 作为上下文传入，由编排 LLM 决定是否传给子调用

### 插件系统

所有模块通过 `REGISTRATION` 声明，Registry 自动发现：

```python
class KnowledgeExtractorAgent(BaseAgent):
    REGISTRATION = ModuleRegistration(
        name="knowledge_extractor",
        module_type=ModuleType.TOOL,
        capabilities=[
            Capability(name="extract_knowledge", description="从论文提取知识"),
        ],
    )
```

- **自动发现**：`registry.auto_discover(['plugins', 'core'])`
- **工具生成**：Capability → Anthropic tool_use 定义
- **路由挂载**：`ROUTER_REGISTRATION` → FastAPI router 自动注册
- **Team 发现**：`TEAM_DEFINITIONS` + `team_export` → 自动收集可组队信息

### REST API

| 端点 | 功能 |
|------|------|
| `POST /api/chat` | AI 对话（Tool Use 流式返回） |
| `POST /api/papers/download` | 下载 arXiv 论文 |
| `GET /api/papers` | 列出论文 |
| `GET /api/papers/{id}` | 论文详情 |
| `POST /api/insights` | 创建洞察 |
| `POST /api/questions` | 创建疑问 |
| `POST /api/ideas` | 创建想法 |
| `GET /api/stats` | 全局统计 |

### 配置

| Config key | 环境变量 | 默认值 | 说明 |
|---|---|---|---|
| `llm.provider` | `LLM_PROVIDER` | `"anthropic"` | `"anthropic"` 或 `"openai"` |
| `llm.model` | `LLM_MODEL` | `"claude-sonnet-4-5-20250929"` | 模型名称 |
| `llm.api_key` | `LLM_API_KEY` | `""` | API 密钥 |
| `llm.base_url` | `LLM_BASE_URL` | `""` | 自定义 endpoint |

优先级：环境变量 > config.yaml > 内置默认值。

## 许可证

MIT License
