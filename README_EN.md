<div align="center">

<img src="./web/public/brand/ordo-mark.png" alt="Ordo Logo" width="120"/>

# Ordo

**Local-First, Enterprise-Grade RAG Knowledge Base System for macOS, Windows & Linux**

<sub>Files stay faithful, pipelines stay controllable, evidence stays citable — deep parsing, accurate retrieval, grounded answers, sentence-level citations.</sub>

<p>
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey.svg" alt="Platform: macOS | Windows | Linux"/>
  <a href="./docs/releases/v1.0.1.md"><img src="https://img.shields.io/badge/release-v1.0.1-2563EB.svg" alt="Release v1.0.1"/></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="License: Apache 2.0"/></a>
  <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+"/>
</p>

<sub><a href="./README.md">简体中文</a> · <a href="./README_EN.md">English</a></sub>

</div>

---

## 📖 Overview

**Ordo** is a local-first, high-precision enterprise RAG (Retrieval-Augmented Generation) knowledge base system for macOS, Windows, and Linux.

Naive text chunking plus vector-only matching loses critical context and produces hard-to-verify hallucinations. Ordo is built on **"files stay faithful, pipelines stay controllable, evidence stays citable"**:

- **Data sovereignty**: run on a single local machine or via Docker; documents, vectors, and indices stay in your own environment by default;
- **Controllable pipeline**: every step — from multimodal parsing and data cleaning to smart chunking and hybrid indexing — offers visual inspection and swappable strategies;
- **Verifiable answers**: dense vector search combined with BM25 full-text search grounds every answer in source chunks, with in-source highlight positioning, citation validation, and abstention on insufficient evidence.

---

## ✨ Key Features

- 📄 **Deep multimodal parsing**: built-in DeepDoc engine with optional Docling, MinerU, Marker backends for complex layouts, tables, scans, and formulas.
- 🧹 **Data governance workbench**: document preview, quality inspection, rule-based cleaning, and human annotation.
- 🧩 **Smart chunking**: semantic, parent-child, and recursive strategies with real-time visual chunk preview.
- 🔍 **Hybrid retrieval & reranking**: Milvus / FAISS / Chroma vector search plus BM25, with multi-recall fusion (RRF) and Cross-Encoder rerankers.
- 📌 **Grounded citations**: answers link to source chunks with in-text highlights; visible evidence constraints, citation checks, and abstention reduce hallucination risk with a fully auditable trail.
- 🕸️ **Knowledge graph**: automatic entity/relation extraction with 2D/3D exploration and graph-augmented retrieval (GraphRAG).
- 🔌 **Open integration**: full OpenAPI / RESTful endpoints, natively compatible with Dify External Knowledge APIs and HTTP workflow nodes.

---

## 🏗️ Architecture

```
Web UI (Next.js) ──REST / SSE──▶ FastAPI backend ──▶ RAG orchestration
                                                   ├─ Parsing / governance / chunking
                                                   ├─ Hybrid retrieval (vector + BM25) + rerank
                                                   └─ LLM generation + citations + faithfulness checks
                                                             │
                           ┌──────────────┬──────────────────┼───────────────┐
                           ▼              ▼                  ▼               ▼
                      PostgreSQL      Milvus /           BM25 index       MinIO / S3
                   (docs/chats)    FAISS / Chroma                      (object store)
```

See [`docs/architecture.md`](./docs/architecture.md) and [`docs/backend_structure.md`](./docs/backend_structure.md) for details.

---

## 🚀 Quick Start

### Prerequisites

- Git, Docker Engine (or Docker Desktop), Docker Compose v2; GNU Make recommended;
- Python 3.11+ and pnpm for source-mode development;
- An OpenAI-compatible LLM API key (embeddings reuse the same key by default).

### 1. Clone & initialize

```bash
git clone <your-repo-url>
cd <repo>
make init
```

Edit the generated `.env` and at minimum set `LLM_API_KEY` (required for real Q&A and embeddings).

### 2. Run services

**Option 1: Docker one-click launch (recommended)**

```bash
make up-web
```

Open in your browser:

- Web console: <http://localhost:3000>
- API docs: <http://localhost:8000/docs>

Before first startup you may set `INITIAL_ADMIN_EMAIL` / `INITIAL_ADMIN_USERNAME` / `INITIAL_ADMIN_PASSWORD` (or `INITIAL_ADMIN_PASSWORD_FILE`) in `.env` to auto-create the initial administrator; weak passwords are rejected at startup — use a strong one in production and rotate it after first login.

**Option 2: Local source development**

```bash
# Install dependencies and start Docker infrastructure (PostgreSQL, Redis, Milvus, MinIO, ...)
make setup-host

# Start backend and frontend in separate terminals
make backend
make web
```

See [`docs/quickstart.md`](./docs/quickstart.md) and [`docs/user_guide.md`](./docs/user_guide.md) for more paths.

---

## ⚙️ Common Commands

| Command | Description |
|---|---|
| `make init` | Generate local `.env` / `web/.env.local` (missing files only, with random secrets) |
| `make up-web` | Start the full Docker stack (Web + API + Worker + infra) |
| `make backend` / `make web` | Run backend / frontend in source mode |
| `make worker` | Run the background task worker in source mode |
| `make test` / `make test-web` | Backend / frontend tests |
| `make verify` | Lint + typecheck + API contract + compile checks |
| `make doctor` | Environment sanity checks |
| `make clean` | Remove local build caches and compiled artifacts |
| `make config-check` | Validate `.env` against `.env.example` |

Full list: `make help`.

---

## 📁 Layout

```
├── app/            # FastAPI backend (APIs / parsing / governance / retrieval / RAG / storage / tasks)
├── web/            # Next.js frontend (routes / components / API clients / state)
├── docker/         # Compose stacks and image builds
├── config/         # Parser model manifests and env profiles
├── docs/           # User guides, architecture, and ops docs
├── docs-site/      # Searchable handbook (Docusaurus sources)
├── scripts/        # Ops and quality-gate scripts
├── tests/          # Backend tests
├── alembic/        # Database migrations
└── Makefile        # Command entry point
```

---

## 📚 Docs

- Quick start: [`docs/quickstart.md`](./docs/quickstart.md)
- Full operation guide: [`docs/user_guide.md`](./docs/user_guide.md)
- Architecture: [`docs/architecture.md`](./docs/architecture.md)
- Deployment: [`docs/deployment/`](./docs/deployment/)
- Integration: [`docs/integration/`](./docs/integration/)
- Releases: [`docs/releases/`](./docs/releases/)

---

## 📄 License

Licensed under the [Apache License 2.0](./LICENSE).
