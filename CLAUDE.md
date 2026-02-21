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
python main.py --arxiv 2301.00001              # Add arXiv paper (full analysis)
python main.py --arxiv 2301.00001 --quick       # Quick mode (ingestion only)
python main.py --local /path/to/paper.pdf       # Add local file
python main.py --list                           # List papers
python main.py --stats                          # Show statistics
python main.py --search "query"                 # Semantic search

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
├── insights/        # Insight domain
│   ├── manager.py   └── router.py
├── questions/       # Question domain
│   ├── manager.py   └── router.py
├── ideas/           # Ideas domain
│   ├── manager.py, structured.py, agent.py, router.py
core/  (shared infrastructure + orchestration)
├── registry.py        # Module registry (plugin system core)
├── registration.py    # @register_module decorator + agent_factory
├── base_agent.py      # BaseAgent ABC (LLM client, memory, call_llm())
├── orchestrator.py    # OrchestratorAgent (pipeline coordination, LLM routing)
└── chat_router.py     # AI chat + Tool Use API (/api/chat)
```

### Multi-Agent Pipeline
```
Orchestrator (core/orchestrator.py)
├── Ingestion Agent (plugins/papers/agent.py) → ArxivDownloader + TexParser
├── Extractor Agent (plugins/knowledge/extractor_agent.py) → contributions, methodology, keywords
└── Analyzer Agent (plugins/knowledge/analyzer_agent.py)   → citations, similarity, clustering
```

All agents extend `BaseAgent` (`core/base_agent.py`) which handles LLM client initialization (Anthropic or OpenAI), conversation memory, and provides `call_llm()`. Each agent implements `async process(input_data) -> dict`.

The `DeepResearchSystem` class in `main.py` is the CLI entry point — it creates the orchestrator which in turn initializes all sub-agents, the vector store, and the knowledge graph.

### Dual Storage
- **Vector Store** (`plugins/knowledge/vector_store.py`): ChromaDB wrapper for semantic search over paper chunks
- **Knowledge Graph** (`plugins/knowledge/knowledge_graph.py`): NetworkX graph for citation relationships, similarity edges, and topic clustering

### TeX-First Strategy
`plugins/papers/downloader.py` downloads TeX source when available (covers ~70% of arXiv papers), falling back to PDF. `plugins/papers/tex_parser.py` extracts structured content (sections, equations, citations, comments). PDF parsing is the fallback path.

### Prompt Template System
All LLM prompts live in `prompts/` as `.txt` files organized by agent (e.g., `prompts/extractor/contributions.txt`). Load with `prompts.loader.load("extractor/contributions", title=..., abstract=...)` — uses `{{variable}}` substitution.

### REST API (FastAPI)
`backend/main.py` mounts routers from `plugins/*/router.py` and `core/chat_router.py`: papers, insights, questions, ideas, chat — all under `/api/`. Auto-generated docs at `/docs`. Both TUI and Web UI consume this API via a shared TypeScript client at `ui/shared/api/client.ts`.

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

Data is stored under `data/` (papers, metadata, vector_db, reports, knowledge_graph.pkl).
