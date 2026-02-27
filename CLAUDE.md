# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Deep Research Agent (OpenResearch) — a multi-agent paper management and analysis system. It ingests academic papers (arXiv or local PDF/TeX), extracts knowledge via LLM agents, builds a vector store + knowledge graph, and exposes results through CLI, REST API, TUI, and Web UI.

Primary language is Chinese for UI text and comments; code identifiers and docs use English.

## Commands

### Python backend
```bash
pip install -r requirements.txt

# CLI usage
python main.py                                  # Interactive chat (LLM orchestrates tasks)
python main.py "your task description"          # Single task execution
python main.py --server                         # Start FastAPI server (port 8000)

# FastAPI server
python -m uvicorn backend.main:app --reload --port 8000
```

### Terminal UI (Ink.js)
```bash
cd ui && npm install
npm run tui          # Run TUI
npm run tui:dev      # Watch mode
```

### Web UI (React + Vite)
```bash
cd ui/web && npm install
npm run dev          # Dev server (port 5173)
npm run build        # Production build (runs tsc first)
```

## Architecture

### Plugin-Based Domain Architecture
Code is organized by domain in `plugins/`, with each domain containing its services, agents, and API routers:

```
plugins/
├── papers/          # Paper ingestion domain
│   ├── downloader.py, tex_parser.py   (services)
│   ├── agent.py                       (PaperIngestionAgent)
│   └── router.py                      (/api/papers)
├── knowledge/       # Knowledge base domain
│   ├── vector_store.py, knowledge_graph.py  (services)
│   ├── extractor_agent.py, analyzer_agent.py (agents)
│   ├── schemas.py                     (JSON Schemas for structured LLM output)
│   ├── teams.py                       (Team definitions: knowledge_review)
├── insights/        # Insight domain
│   ├── manager.py   └── router.py
├── questions/       # Question domain
│   ├── manager.py   └── router.py
├── ideas/           # Ideas domain
│   ├── manager.py, structured.py, agent.py, router.py
core/  (shared infrastructure)
├── registry.py        # Module registry (plugin system core, ModuleType: TOOL/SUBAGENT/ROUTER)
├── registration.py    # @register_module decorator + agent_factory
├── base_agent.py      # BaseAgent ABC (LLM client, memory, call_llm(), call_llm_structured())
├── tool_use_runner.py # ToolUseRunner (generic Anthropic tool-use loop executor)
├── chat_router.py     # AI chat + Tool Use API (/api/chat) + built-in subagent tools (Team)
├── team.py            # Agent Team engine (TeamContext, TeamCoordinator, Team, factories)
├── team_schemas.py    # COORDINATOR_DECISION_SCHEMA
└── recursive_chat.py  # Recursive chat engine (Team agent research tool)
```

### LLM-Orchestrated Multi-Agent System
All task orchestration is done by the LLM via tool-use — no fixed pipeline. The LLM autonomously decides which agents to invoke and in what order:

```
TaskSystem (main.py) / ChatRouter (core/chat_router.py)
  └── ToolUseRunner (core/tool_use_runner.py)
        ├── ingest_paper    → PaperIngestionAgent
        ├── extract_knowledge → KnowledgeExtractorAgent
        ├── add_to_knowledge_base → VectorStore + KnowledgeGraph
        ├── analyze_relations → RelationAnalyzerAgent
        └── search_papers   → VectorStore
```

All agents extend `BaseAgent` (`core/base_agent.py`) which handles LLM client initialization (Anthropic or OpenAI), conversation memory, and provides:
- `call_llm(prompt, system_prompt, max_retries)` — text response with exponential backoff retry
- `call_llm_structured(prompt, schema, tool_name)` — forced structured JSON output via tool_use/function_calling
- `_parse_json_response(response)` — bracket-depth JSON extraction from text (unified, replaces per-agent copies)

Each agent implements `async process(input_data) -> dict`.

The `TaskSystem` class in `main.py` is the CLI entry point — a zero-domain-knowledge task runner that delegates to LLM + tool-use via `ToolUseRunner`.

### ToolUseRunner
`core/tool_use_runner.py` is a generic, callback-driven Anthropic tool-use loop executor extracted from `chat_router.py` and `main.py`. It provides:
- `max_iterations=15` safety limit
- Callback hooks: `on_text`, `on_tool_call`, `on_tool_result` for UI adaptation
- Used by both CLI (`main.py`) and API (`chat_router.py`)

### Agent Team System
`core/team.py` provides multi-agent collaboration within a single task. Two forms:

- **Form 1 (same-plugin)**: Same agent class, different system prompts for different roles. Uses `TeamAgentWrapper` to override `_get_system_prompt()` without modifying the original agent. Example: `knowledge_review` team (extractor + critic, both backed by `knowledge_extractor`).
- **Form 2 (cross-plugin)**: Different plugin agents cooperate. Agents declare `team_export=TeamExport(default_role=..., description=...)` in their `REGISTRATION` to opt in.

Key components:
- **TeamContext** (shared blackboard): `write(key, value, writer)` / `read(key)` / `get_summary()` (token-efficient, only key+writer+summary)
- **TeamCoordinator**: LLM-driven decision loop using `call_llm_structured()` + `COORDINATOR_DECISION_SCHEMA`. Decides `delegate(member_role, input_keys, instruction, output_key)` or `terminate`.
- **Team**: Execution engine — loops coordinator decisions, delegates to members, passes data via blackboard. Safety limit via `max_turns`.
- **TeamDefinition / TeamMemberSpec**: Declarative team definitions exported as `TEAM_DEFINITIONS` module-level constant (auto-discovered by registry).

Team tools are built into `core/chat_router.py` (not a separate plugin):
- `run_team(team_name, task, initial_data?)` — run a predefined team
- `run_ad_hoc_team(agent_names[], task, initial_data?)` — dynamically assemble and run
- `list_teams()` — list available teams and team-ready agents

Prompts: `prompts/system/team_coordinator.txt` (system), `prompts/team/coordinator.txt` (per-turn decision template with `{{task_description}}`, `{{members_description}}`, `{{blackboard_summary}}`, `{{history_summary}}`, `{{current_turn}}`, `{{max_turns}}`).

### Recursive Chat (Team Agent Research)
`core/recursive_chat.py` enables Team agents to autonomously research external information via a `research` tool. When a Team agent needs to look up papers, extract knowledge, etc., it calls `research(query)` which spawns a recursive ToolUseRunner chat with full tool permissions.

Key design:
- **Recursion depth**: `max_recursion_depth` (default 2) configured at Team level. `depth < max`: agent has `research` tool; `depth >= max`: falls back to plain `call_llm`.
- **Full permissions**: Recursive chat has access to all TOOL + subagent tools (including `run_team`, which creates sub-teams whose agents also get `research` at depth+1).
- **Memory isolation**: Recursive chat produces two outputs: (1) `full_result` returned to the agent for reasoning, (2) `meta_summary` (tool call log, no LLM needed) recorded for system awareness. The recursive chat's conversation history is discarded after return (natural GC).
- **`RESEARCH_TOOL_DEF`**: Anthropic tool_use definition for the `research` tool (internal to Team agents, not exposed to top-level chat).
- **`TeamAgentWrapper`**: Always wraps Team member agents. When `depth < max_depth`, `process()` uses ToolUseRunner + `[RESEARCH_TOOL_DEF]`; otherwise falls back to `call_llm`.

Prompt: Reuses `chat_assistant.txt` (via `_get_system_prompt()`) with a recursive mode header prepended.

### Structured LLM Output
`BaseAgent.call_llm_structured()` forces structured JSON output via:
- **Anthropic**: `tool_choice={"type": "tool", "name": ...}` with a virtual tool definition containing the JSON Schema
- **OpenAI**: `tool_choice={"type": "function", ...}` with function calling

JSON Schemas for all extraction/analysis tasks are centralized in `plugins/knowledge/schemas.py`.

Optional `jsonschema` validation is performed if the package is installed.

### Knowledge Extraction Pipeline
`KnowledgeExtractorAgent` runs extraction in phased parallel groups:
- **Phase A** (parallel): contributions, research_questions, keywords
- **Phase B** (depends on A, parallel): methodology, concepts
- **Phase C** (depends on A+B, parallel): findings, limitations, future_work
- **Phase D** (depends on all): summary

Each phase injects prior results as `{{prior_context}}` into subsequent prompts. High-impact extractions (contributions, methodology, findings) undergo reflection verification.

### Dual Storage
- **Vector Store** (`plugins/knowledge/vector_store.py`): ChromaDB wrapper for semantic search over paper chunks
- **Knowledge Graph** (`plugins/knowledge/knowledge_graph.py`): NetworkX graph for citation relationships, similarity edges, and topic clustering

### TeX-First Strategy
`plugins/papers/downloader.py` downloads TeX source when available (covers ~70% of arXiv papers), falling back to PDF. `plugins/papers/tex_parser.py` extracts structured content (sections, equations, citations, comments). PDF parsing is the fallback path.

### Prompt Template System
All LLM prompts live in `prompts/` as `.txt` files organized by agent (e.g., `prompts/extractor/contributions.txt`). Load with `prompts.loader.load("extractor/contributions", title=..., abstract=...)` — uses `{{variable}}` substitution.

Each extractor prompt includes:
- Extraction guidance (what to look for, how to distinguish)
- Missing-info handling instructions
- `{{prior_context}}` variable for cross-task context sharing

### Plugin Classification: TOOL vs SUBAGENT
Modules that expose LLM-callable tools are classified into two types:
- **TOOL** (`ModuleType.TOOL`): Simple function calls — CRUD, search, extraction. All domain plugins use this type.
- **SUBAGENT** (`ModuleType.SUBAGENT`): Complex multi-agent collaboration (Team). Currently no plugins use this type; Team tools are built into `chat_router.py`.
- **ROUTER** (`ModuleType.ROUTER`): Reserved for `chat_router` itself (the chat API).

`TOOL_PROVIDING_TYPES = {ROUTER, TOOL, SUBAGENT}` — the set of module types that can provide tools and routers.

### Plugin Auto-Loading
All plugins are auto-discovered via `Registry.auto_discover(['core', 'plugins'])`. No hardcoded registration required — adding a new plugin to `plugins/` with `ROUTER_REGISTRATION` and/or class-level `REGISTRATION` is sufficient. The registry collects:
- **Router objects** (`get_router_objects()`): auto-mounted in `backend/main.py` — scans all `TOOL_PROVIDING_TYPES`
- **Tool handlers** (`get_all_tool_handlers()`): each module exports a `TOOL_HANDLERS` dict, auto-collected by `core/chat_router.py`
- **Stats handlers** (`get_stats_handlers()`): each module's `get_stats()` function, auto-aggregated for `/api/stats`
- **Team definitions** (`get_all_team_definitions()`): modules exporting `TEAM_DEFINITIONS` list, auto-collected by registry
- **Team-ready agents** (`get_team_ready_agents()`): agents with `team_export` in their REGISTRATION

Tool generation: `generate_tools_from_registry()` in `backend/tools.py` generates Anthropic tool definitions from `TOOL_PROVIDING_TYPES` modules. `generate_subagent_tools()` in `chat_router.py` generates the built-in Team tool definitions. `get_all_tools()` combines both.

### REST API (FastAPI)
`backend/main.py` auto-mounts all routers discovered by the registry from `plugins/*/router.py` and `core/chat_router.py` — all under `/api/`. Auto-generated docs at `/docs`. Both TUI and Web UI consume this API via a shared TypeScript client at `ui/shared/api/client.ts`.

### Frontend Architecture
- **Shared layer** (`ui/shared/`): API client, types, and command definitions shared between TUI and Web
- **TUI** (`ui/tui/`): Ink.js (React for terminal), entry at `ui/tui/index.tsx`
- **Web** (`ui/web/`): React 18 + Vite + Tailwind CSS, entry at `ui/web/src/main.tsx`

### Additional Systems
- **Insights** (`plugins/insights/manager.py`): Cross-paper insight generation
- **Questions** (`plugins/questions/manager.py`): Research problem tracking
- **Ideas** (`plugins/ideas/manager.py`, `plugins/ideas/structured.py`): Idea management and structured extraction

## Configuration

Copy `config/config.example.yaml` to `config/config.yaml` and set API keys. Default LLM is `claude-sonnet-4-5-20250929`. Config controls LLM provider, TeX/PDF parser options, vector DB settings, and storage paths.

### Unified LLM Configuration

All LLM settings are in the `llm:` section of `config/config.yaml` and can be overridden by environment variables:

| Config key | Env var | Default | Description |
|---|---|---|---|
| `provider` | `LLM_PROVIDER` | `"anthropic"` | `"anthropic"` or `"openai"` (covers DeepSeek, Ollama, etc.) |
| `model` | `LLM_MODEL` | `"claude-sonnet-4-5-20250929"` | Model name |
| `api_key` | `LLM_API_KEY` | `""` | API key (fallback: `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`) |
| `base_url` | `LLM_BASE_URL` | `""` | Custom endpoint (empty = SDK default) |

Priority: environment variable > config.yaml > built-in default. If `provider` is empty, it is auto-detected from the model name (`claude` → anthropic, otherwise → openai).

Configuration is loaded by `core/config.py` (`load_app_config()` / `get_app_config()`), shared by CLI (`main.py`), FastAPI (`backend/main.py`), and chat router (`core/chat_router.py`).

Data is stored under `data/` (papers, metadata, vector_db, reports, knowledge_graph.pkl).
