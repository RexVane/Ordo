<div align="center">

<img src="./web/public/brand/ordo-mark.png" alt="Ordo Logo" width="120"/>

# Ordo

**面向 macOS、Windows 与 Linux 的本地优先企业级 RAG 知识库系统**

<sub>原文件不动、过程可控、证据可回溯——深度解析、精准检索、严格问答、逐句引用</sub>

<p>
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey.svg" alt="Platform: macOS | Windows | Linux"/>
  <a href="./docs/releases/v1.0.1.md"><img src="https://img.shields.io/badge/release-v1.0.1-2563EB.svg" alt="Release v1.0.1"/></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="License: Apache 2.0"/></a>
  <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+"/>
</p>

<sub><a href="./README.md">简体中文</a> · <a href="./README_EN.md">English</a></sub>

</div>

---

## 📖 项目简介

**Ordo** 是一套本地优先、高精度的企业级 RAG（检索增强生成）知识库系统，支持 macOS、Windows 与 Linux。

单纯的文档切片加向量匹配容易丢失关键上下文，并产生难以检验的模型幻觉。Ordo 围绕 **“原文件不动、过程可控制、证据全回溯”** 设计：

- **数据自主可控**：支持跨平台本地单机或 Docker 容器化部署，文档、向量与索引默认全部保留在本地环境；
- **全链路精细可控**：从多模态文档解析、数据清洗、智能切块到混合索引，每一步都支持可视化检查与策略替换；
- **回答有据可查**：密集向量检索结合 BM25 全文检索，回答严格关联原始切片，支持原文定位高亮、引用验证与证据不足拒答。

---

## ✨ 核心特性

- 📄 **深度多模态解析**：内置 DeepDoc 引擎，可按需扩展 Docling、MinerU、Marker 等，还原复杂版式、表格、扫描件与公式。
- 🧹 **数据治理工作台**：文档预览、质量质检、规则清洗与人工标注，从源头保障知识质量。
- 🧩 **业务智能切块**：语义切块、父子切块（Parent-Child）、递归切块等多种策略，配切片实时可视化预览。
- 🔍 **混合检索与精细重排**：Milvus / FAISS / Chroma 向量检索结合 BM25 全文检索，内置多路召回融合（RRF）与 Cross-Encoder Reranker。
- 📌 **证据引用溯源**：回答关联原始切片并可在原文中高亮定位，以可见证据约束、引用验证和拒答机制降低幻觉风险，全程可审计。
- 🕸️ **知识图谱增强**：自动抽取实体与关系拓扑，支持 2D/3D 图谱交互与图检索增强（GraphRAG）。
- 🔌 **开放集成**：完整 OpenAPI / RESTful 接口，原生兼容 Dify 外部知识库 API 与 HTTP 工作流节点。

---

## 🏗️ 系统架构

```
用户界面 (Next.js) ──REST / SSE──▶ FastAPI 后端 ──▶ RAG 编排引擎
                                                ├─ 文档解析 / 治理 / 切块
                                                ├─ 混合检索 (向量 + BM25) + 重排
                                                └─ LLM 生成 + 引用 + 忠实度校验
                                                          │
                        ┌───────────────┬─────────────────┼───────────────┐
                        ▼               ▼                 ▼               ▼
                   PostgreSQL      Milvus /          BM25 索引        MinIO / S3
                  (文档/对话)    FAISS / Chroma                      (对象存储)
```

详细说明见 [`docs/architecture.md`](./docs/architecture.md) 与 [`docs/backend_structure.md`](./docs/backend_structure.md)。

---

## 🚀 快速开始

### 前置条件

- Git、Docker Engine（或 Docker Desktop）与 Docker Compose v2，推荐安装 GNU Make；
- 源码开发另需 Python 3.11+ 与 pnpm；
- 一个 OpenAI 兼容接口的 LLM API Key（向量模型默认复用同一 Key）。

### 1. 克隆与初始化

```bash
git clone <your-repo-url>
cd <repo>
make init
```

编辑生成的 `.env`，至少填写 `LLM_API_KEY`（真实问答与向量化的最低要求）。

### 2. 启动服务

**方式一：Docker 一键启动（推荐）**

```bash
make up-web
```

浏览器访问：

- 前端控制台：<http://localhost:3000>
- API 接口文档：<http://localhost:8000/docs>

首次启动前可在 `.env` 中设置 `INITIAL_ADMIN_EMAIL` / `INITIAL_ADMIN_USERNAME` / `INITIAL_ADMIN_PASSWORD`（或 `INITIAL_ADMIN_PASSWORD_FILE`）自动创建初始管理员；弱密码会被拒绝启动，生产环境请使用强密码并在首次登录后轮换。

**方式二：本地源码开发模式**

```bash
# 安装依赖并启动 Docker 基础设施（PostgreSQL、Redis、Milvus、MinIO 等）
make setup-host

# 分别在终端启动后端与前端
make backend
make web
```

更多路径见 [`docs/quickstart.md`](./docs/quickstart.md) 与 [`docs/user_guide.md`](./docs/user_guide.md)。

---

## ⚙️ 常用命令

| 命令 | 说明 |
|---|---|
| `make init` | 生成本地 `.env` / `web/.env.local`（仅创建缺失项并填充随机密钥） |
| `make up-web` | Docker 启动完整栈（Web + API + Worker + 基础设施） |
| `make backend` / `make web` | 主机源码模式分别启动后端 / 前端 |
| `make worker` | 主机源码模式启动后台任务 Worker |
| `make test` / `make test-web` | 后端 / 前端测试 |
| `make verify` | Lint + 类型检查 + API 契约 + 编译检查 |
| `make doctor` | 环境自检 |
| `make clean` | 清理本地构建缓存与编译产物 |
| `make config-check` | 校验 `.env` 与 `.env.example` 是否一致 |

完整目标列表：`make help`。

---

## 📁 目录结构

```
├── app/            # FastAPI 后端（API / 解析 / 治理 / 检索 / RAG / 存储 / 任务）
├── web/            # Next.js 前端（页面路由 / 组件 / API 客户端 / 状态管理）
├── docker/         # Compose 编排与镜像构建
├── config/         # 解析模型清单与环境模板
├── docs/           # 用户指南、架构与运维文档
├── docs-site/      # 可搜索全栈手册（Docusaurus 源码）
├── scripts/        # 运维与质检脚本
├── tests/          # 后端测试
├── alembic/        # 数据库迁移
└── Makefile        # 常用命令入口
```

---

## 📚 文档导航

- 入门：[`docs/quickstart.md`](./docs/quickstart.md)
- 全流程操作：[`docs/user_guide.md`](./docs/user_guide.md)
- 架构：[`docs/architecture.md`](./docs/architecture.md)
- 部署：[`docs/deployment/`](./docs/deployment/)
- 集成：[`docs/integration/`](./docs/integration/)
- 发版记录：[`docs/releases/`](./docs/releases/)

---

## 📄 开源协议

本项目基于 [Apache License 2.0](./LICENSE) 开源。
