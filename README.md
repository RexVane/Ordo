<div align="center">

<img src="./web/public/brand/ordo-mark.png" alt="Ordo Logo" width="120"/>

# Ordo

**面向 macOS、Windows 与 Linux 的本地优先企业级 RAG 知识库系统**

<sub>原文件可控、证据留存——可深度解析、可精准检索、可严格问答、可逐句回溯</sub>

<p>
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey.svg" alt="Platform: macOS | Windows | Linux"/>
  <a href="./docs/releases/v1.0.1.md"><img src="https://img.shields.io/badge/release-v1.0.1-2563EB.svg" alt="Release v1.0.1"/></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT"/></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+"/></a>
</p>

<sub><a href="./README.md">简体中文</a> · <a href="./README_EN.md">English</a></sub>

</div>

---

## 📖 项目简介

**Ordo** 是面向 macOS、Windows 与 Linux 的本地优先、高精度企业级 RAG（检索增强生成）知识库系统。

在实际知识管理与问答场景中，单纯的文档切片和向量匹配容易丢失关键上下文，并带来难以检验的模型幻觉。Ordo 秉承 **“原文件不动、过程可控制、证据全回溯”** 的理念：

- **数据与原文件自主可控**：支持跨平台本地单机或 Docker 容器化部署，数据与索引完全保留在本地环境；
- **全链路精细可控**：从多模态文档解析、数据清洗、智能切块到混合索引，每一步均支持可视化检查与灵活替换；
- **真实证据可问答、可回溯**：结合密集向量与 BM25 混合检索，提供严格的逐句证据引用与原文定位高亮，让每一次回答都真实可信、有据可查。

---

## ✨ 核心特性

- 📄 **深度多模态解析**：内置 DeepDoc 引擎，支持按需扩展 Docling、MinerU、Marker 等，精准还原复杂 PDF、表格、扫描件与公式。
- 🧹 **数据治理工作台**：开箱即用的文档预览、质量质检、规则清洗与人工标注，从源头确保知识质量。
- 🧩 **业务智能切块**：支持语义切块、父子切块（Parent-Child）、递归切块等多种策略，配备切片实时可视化预览。
- 🔍 **混合检索与精细重排**：结合 Milvus / FAISS / Chroma 向量检索与 BM25 全文检索，内置多路召回融合（RRF）与 Cross-Encoder Reranker。
- 📌 **证据引用溯源**：生成的回答关联原始切片，支持在原文中高亮定位，通过可见证据约束、引用验证和证据不足拒答降低幻觉风险，提供可审计的检索与生成过程。
- 🕸️ **知识图谱增强**：自动抽取知识实体与关系拓扑，支持 2D/3D 图谱交互与图检索增强（GraphRAG）。
- 🔌 **无缝对接 Dify 与 API**：原生支持 Dify 外部知识库 API 与 HTTP 工作流节点，提供完整的 OpenAPI / RESTful 接口。

---

## 🏗️ 系统架构

```
Next.js 前端 ──REST/SSE──▶ FastAPI 后端 ──▶ 解析 / 治理 / 切块 / 混合检索 / RAG 生成
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
        PostgreSQL            Milvus / FAISS          BM25 索引
        (文档/对话)            (向量检索)              (关键词检索)
```

| 层级 | 技术选型 |
|------|---------|
| 前端 | Next.js + TypeScript + Tailwind CSS |
| 后端 | FastAPI + Python 3.11 |
| AI 编排 | LangChain / LangGraph（OpenAI 兼容接口） |
| 向量库 | Milvus / FAISS / Chroma（可切换） |
| 关系库 | PostgreSQL |
| 任务队列 | Arq + Redis |
| 对象存储 | MinIO（S3 兼容） |

详细说明见 [docs/architecture.md](./docs/architecture.md) 与 [docs/backend_structure.md](./docs/backend_structure.md)。

---

## 🚀 快速开始

### 1. 克隆与初始化

```bash
git clone https://github.com/RexVane/Ordo.git
cd Ordo
make init
```

编辑生成的 `.env` 文件，至少填写 `LLM_API_KEY`（默认硅基流动 OpenAI 兼容接口，Embedding 默认复用该 Key）。

### 2. 启动服务

**方式一：Docker 一键启动（推荐）**

```bash
make up-web
```

启动完成后在浏览器访问：

- 前端控制台：[http://localhost:3000](http://localhost:3000)
- API 接口文档：[http://localhost:8000/docs](http://localhost:8000/docs)
- 初始管理员：首次启动前在 `.env` 中设置 `INITIAL_ADMIN_EMAIL` / `INITIAL_ADMIN_USERNAME` / `INITIAL_ADMIN_PASSWORD`（或 `INITIAL_ADMIN_PASSWORD_FILE`），启动时自动创建；弱密码会被拒绝启动，生产环境请使用强密码并在首次登录后轮换。

**方式二：本地源码开发模式**

```bash
# 安装依赖并启动 Docker 基础设施（PostgreSQL, Redis, Milvus, MinIO 等）
make setup-host

# 分别在终端启动后端与前端
make backend
make web
# 如需独立后台任务队列，再开一个终端
make worker
```

更多说明见 [docs/quickstart.md](./docs/quickstart.md) 与 [docs/user_guide.md](./docs/user_guide.md)。

---

## ⚙️ 常用命令

```bash
make doctor      # 环境自检
make verify      # lint + 类型检查 + API 契约检查
make test        # 后端测试
make test-web    # 前端测试
make api-ping    # 后端连通性检查
make config-check # 检查 .env 与模板的一致性
```

`.env.example` 是完整配置模板（含每项中文说明），`config/profiles/` 下另有 minimal / local / production / airgapped 精简模板。

---

## 📁 项目结构

```
Ordo/
├── app/          # FastAPI 后端（API / 解析 / 治理 / 检索 / RAG / 存储 / 任务）
├── web/          # Next.js 前端
├── docker/       # Docker Compose 编排与镜像
├── docs/         # 项目文档（含快速入门、架构、部署、评测）
├── docs-site/    # Docusaurus 全栈手册
├── scripts/      # 运维与检查脚本
├── tests/        # 后端测试
├── config/       # 配置清单与环境模板
└── Makefile      # 常用命令入口
```

---

## 📄 开源协议

- 本仓库原创部分采用 [MIT License](./LICENSE) 开源。
- 衍生的第三方上游组件（MimirQ、RAGFlow/DeepDoc 等）遵循 Apache License 2.0，归属与许可文本见 [NOTICE](./NOTICE) 与 [LICENSE-APACHE-2.0](./LICENSE-APACHE-2.0)。
- 依赖包各自遵循其自身许可（见 `requirements.txt` / `web/package.json`）；注意 PyMuPDF 为 AGPL-3.0 / 商业双许可，详见 [NOTICE](./NOTICE) 第 5 节。
