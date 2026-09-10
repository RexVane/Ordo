<div align="center">

<img src="./web/public/brand/ordo-mark.png" alt="Ordo Logo" width="120"/>

# Ordo

**Local-First, Enterprise-Grade RAG Knowledge Base for macOS, Windows & Linux**

<sub>Files stay faithful and inspectable — deeply parseable, accurately searchable, reliably askable, sentence-by-sentence citable.</sub>

<p>
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey.svg" alt="Platform: macOS | Windows | Linux"/>
  <a href="./docs/releases/v1.0.1.md"><img src="https://img.shields.io/badge/release-v1.0.1-2563EB.svg" alt="Release v1.0.1"/></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT"/></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+"/></a>
</p>

<sub><a href="./README.md">简体中文</a> · <a href="./README_EN.md">English</a></sub>

</div>

---

## 📖 Overview

**Ordo** is a local-first, high-precision enterprise RAG (Retrieval-Augmented Generation) knowledge base system for macOS, Windows, and Linux.

Naive chunking plus vector-only matching loses critical context and produces unverifiable hallucinations. Ordo is built on **"files stay faithful, pipelines stay controllable, evidence stays citable"**:

- **Local-first & data sovereignty**: run on a single machine or via Docker; files, embeddings, and indices stay in your own environment;
- **Controllable pipeline**: every stage — multimodal parsing, data governance, smart chunking, hybrid indexing — supports visual inspection and swappable strategies;
- **Grounded answers**: dense vectors plus BM25 hybrid retrieval with strict sentence-level citations and source highlighting, so every answer is verifiable.

---

## ✨ Key Features

- 📄 **Deep multimodal parsing**: built-in DeepDoc engine, extensible with Docling, MinerU, Marker and more; faithfully restores complex PDFs, tables, scans, and formulas.
- 🧹 **Data governance workbench**: document preview, quality inspection, rule-based cleaning, and human annotation out of the box.
- 🧩 **Smart chunking**: semantic, parent-child, and recursive strategies with real-time chunk preview.
- 🔍 **Hybrid retrieval & reranking**: Milvus / FAISS / Chroma vector search combined with BM25 full-text search, RRF fusion, and Cross-Encoder rerankers.
- 📌 **Evidence citations**: answers link to source chunks with in-document highlighting; visible evidence constraints, citation validation, and abstention on insufficient evidence reduce hallucination and keep the process auditable.
- 🕸️ **Knowledge graph & GraphRAG**: automatic entity/relation extraction with 2D/3D exploration and graph-enhanced retrieval.
- 🔌 **Dify & API integration**: native Dify External Knowledge API and HTTP workflow nodes, plus full OpenAPI / RESTful endpoints.

---

## 🏗️ Architecture

```
Next.js frontend ──REST/SSE──▶ FastAPI backend ──▶ parsing / governance / chunking / hybrid retrieval / RAG
                                        │
            ┌───────────────────────────┼───────────────────────────┐
            ▼                           ▼                           ▼
      PostgreSQL                  Milvus / FAISS                BM25 index
   (documents/chats)            (vector search)              (keyword search)
```

| Layer | Stack |
|-------|-------|
| Frontend | Next.js + TypeScript + Tailwind CSS |
| Backend | FastAPI + Python 3.11 |
| AI orchestration | LangChain / LangGraph (OpenAI-compatible APIs) |
| Vector store | Milvus / FAISS / Chroma (switchable) |
| Relational DB | PostgreSQL |
| Task queue | Arq + Redis |
| Object storage | MinIO (S3-compatible) |

See [docs/architecture.md](./docs/architecture.md) and [docs/backend_structure.md](./docs/backend_structure.md) for details.

---

## 🚀 Quick Start

### 1. Clone & initialize

```bash
git clone https://github.com/RexVane/Ordo.git
cd Ordo
make init
```

Edit the generated `.env` and at minimum set `LLM_API_KEY` (defaults to a SiliconFlow OpenAI-compatible endpoint; embeddings reuse the same key unless overridden).

### 2. Run services

**Option 1: Docker one-click launch (recommended)**

```bash
make up-web
```

Then open in your browser:

- Web console: [http://localhost:3000](http://localhost:3000)
- API docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Initial admin: set `INITIAL_ADMIN_EMAIL` / `INITIAL_ADMIN_USERNAME` / `INITIAL_ADMIN_PASSWORD` (or `INITIAL_ADMIN_PASSWORD_FILE`) in `.env` before first startup; weak passwords are rejected — use a strong password in production and rotate it after first login.

**Option 2: local source development**

```bash
# Install dependencies and start Docker infrastructure (PostgreSQL, Redis, Milvus, MinIO, …)
make setup-host

# Start backend and frontend in separate terminals
make backend
make web
# Optional dedicated background worker
make worker
```

See [docs/quickstart.md](./docs/quickstart.md) and [docs/user_guide.md](./docs/user_guide.md) for more.

---

## ⚙️ Common Commands

```bash
make doctor       # environment sanity checks
make verify       # lint + typecheck + API contract checks
make test         # backend tests
make test-web     # frontend tests
make api-ping     # backend reachability check
make config-check # validate .env against the template
```

`.env.example` is the complete, commented configuration template; `config/profiles/` additionally ships minimal / local / production / airgapped presets.

---

## 📁 Project Structure

```
Ordo/
├── app/          # FastAPI backend (APIs / parsing / governance / retrieval / RAG / storage / tasks)
├── web/          # Next.js frontend
├── docker/       # Docker Compose stacks and images
├── docs/         # Project docs (quickstart, architecture, deployment, evaluation)
├── docs-site/    # Docusaurus handbook
├── scripts/      # Ops and check scripts
├── tests/        # Backend tests
├── config/       # Config manifests and env profiles
└── Makefile      # Command entry point
```

---

## 📄 License

- Original contributions in this repository are licensed under the [MIT License](./LICENSE).
- Derived third-party upstream components (MimirQ, RAGFlow/DeepDoc, etc.) remain under the Apache License 2.0 — see [NOTICE](./NOTICE) and [LICENSE-APACHE-2.0](./LICENSE-APACHE-2.0).
- Dependencies follow their own licenses (see `requirements.txt` / `web/package.json`); note PyMuPDF is dual-licensed AGPL-3.0 / commercial — see section 5 of [NOTICE](./NOTICE).
