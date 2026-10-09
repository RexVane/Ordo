# Ordo Backend 目录结构

> 2026-10-09 按当前仓库校正：移除了已不存在的目录（`app/governance/`、`app/evaluation/`、`app/storage/search/`、`app/parsing/chunking/`、`tests/parsing/` 等），修正了迁移对照表中的新路径，并把示例代码对齐到实际函数签名。

## 概览

```
app/
├── main.py           # FastAPI 应用入口（根目录 main.py 是本地启动包装，调用 uvicorn）
├── api/              # HTTP 层
│   ├── v1/           # 路由（约 100 个文件），入口 get_router()
│   ├── schemas/      # 请求/响应 Schema（pydantic）
│   ├── dependencies/ # 依赖注入：鉴权、租户、日志上下文
│   ├── middleware/   # 请求级中间件：request id、限流、耗时、响应头清理
│   └── utils/
├── core/             # 核心配置与基础设施：config.py、database.py、migrations.py
├── models/           # SQLAlchemy ORM 模型
├── services/         # 业务服务（平铺，约 178 个文件）
├── parsing/          # 文档解析：parsers/、processors/、quality/、preprocess/、enrich/、models/、output/、utils/
├── rag/              # RAG 核心：engine.py、agent.py、graph.py、tools.py、retriever.py，及子包
│                     #   chunking/、retrieval/、reranker/、evaluation/、kg/、llm/、embedding/、workflows/、policy/ 等
├── storage/          # 存储：vector/（BaseVectorStore 与 Milvus 等）、object/（MinIO）
├── deepdoc/          # DeepDoc 版面解析引擎
├── connectors/       # 外部数据源连接器
├── tasks/            # 后台任务：queue、worker、jobs、locks
├── query/            # 查询扩展与归一化
├── config/           # 配置子模块（如 rerank_profile.py）
├── types/            # 共享类型（pipeline、indexing、document_analytics）
└── third_party/      # 第三方集成代码（integrated_pipeline 为规范实现）
```

## 模块说明

### 1. api/ — API 路由层

- 入口是 `app/api/v1/__init__.py` 的 `get_router()`，它按前缀挂载各路由；`app/main.py` 再以 `/api/v1` 前缀挂载整个 v1 路由。
- 主要路由文件：`chat.py`、`documents.py`、`datasets.py`、`pipeline.py`、`evaluations.py`、`network_analysis.py`。清洗预览、摄取预览在 `pipeline_support/` 下。
- 知识图谱路由 `app/rag/kg/api/routes.py` 挂在 `/kg` 下。

```python
from app.api.v1 import get_router
```

### 2. core/ — 核心配置

- `config.py`：`Settings` 类与全局单例 `settings`
- `database.py`：数据库连接与会话（`get_db` 定义在 `database_singleton.py`，这里转出）
- `migrations.py`：运行时迁移

```python
from app.core.config import settings
from app.core.database import get_db
```

### 3. models/ — 数据库模型

SQLAlchemy ORM 模型：`document.py`（`Document`、`DocumentChunk`）、`chat.py`、`dataset.py`、`evaluation.py`。

```python
from app.models.document import Document, DocumentChunk
```

### 4. api/schemas/ — API Schema

请求/响应的数据验证模型，例如 `document.py` 中的 `DocumentPipelineOptions`。

```python
from app.api.schemas.document import DocumentPipelineOptions
```

### 5. api/dependencies/ — 依赖注入

- `auth.py`：`get_current_account_id`（鉴权）
- `tenant.py`：`get_tenant_id`（租户）
- `logging.py`：`bind_route_context`（只写日志上下文，不做鉴权）

```python
from app.api.dependencies.auth import get_current_account_id
from app.api.dependencies.tenant import get_tenant_id
```

### 6. parsing/ — 文档解析 📦

负责解析、质量评估、预处理，产出 Markdown。**切块不在这里**，切块位于 `app/rag/chunking/`。

子模块：`parsers/`（各解析器）、`processors/`（处理流程编排）、`quality/`（PDF 质量评估、OCR 验证）、`preprocess/`、`enrich/`、`models/`、`output/`、`utils/`（ZIP 等）。

```python
# 质量评估
from app.parsing.quality.scorer import score_pdf_quality
quality = score_pdf_quality(pdf_path, sample_pages=3, use_ocr_validation=True)

# 解析文档，返回 (documents, backend)
from app.parsing.factory import parser_factory
documents, backend = parser_factory.parse(file_path, parser_backend="auto")

# 文本切块（切块工厂位于 rag/chunking）
from app.rag.chunking.factory import chunker_factory
chunker = chunker_factory.get_chunker("langchain_recursive", chunk_size=1000, chunk_overlap=200)
chunks = chunker.split_documents(documents)

# 分层切块
from app.rag.chunking.utils.hierarchical import hierarchical_chunk_markdown
result = hierarchical_chunk_markdown(markdown_text)

# 完整流程（异步）
from app.parsing.processors.processor import document_processor
await document_processor.process_document(file_path, doc_id, tenant_id)
```

**每文档可覆盖的 pipeline 参数**（定义在 `app/api/schemas/document.py` 的 `DocumentPipelineOptions`）：
- `governance_enabled`、`chunk_size`、`chunk_overlap`
- `chunk_vector_enabled`、`bm25_index_enabled`
- `kg_enabled`、`event_vector_enabled`、`entity_vector_enabled`

### 6.5 数据治理（清洗预览）

- 开关：`GOVERNANCE_ENABLED`（`app/core/config.py`，默认关闭）
- 接口（前缀 `/api/v1/pipeline`，定义在 `app/api/v1/pipeline.py`）：
  - `POST /clean-preview`：清洗预览
  - `GET /clean-rules`：清洗规则列表
  - `POST /llm-clean-preview`：大模型清洗预览
  - `POST /extract-keywords`：关键词提取；`provider=hanlp` 需要环境变量 `HANLP_TOKENIZER_MODEL`
- 实现：清洗预览在 `app/api/v1/pipeline_support/clean_preview.py`；规则、诊断、关键词在 `app/rag/preprocessing/`（停用词见 `stopwords.py`，关键词见 `keyword.py`）。

### 7. storage/ — 存储 📦

- `vector/`：`factory.py` 定义抽象基类 `BaseVectorStore` 和 `get_vector_store()`；`milvus.py` 等是具体实现。
- `object/`：`minio.py`，提供 `minio_service` 单例。
- 混合检索（BM25 + 向量 + 融合）不在 storage：`app/rag/retriever.py` 提供 `hybrid_retriever`，通道与索引细节在 `app/rag/retrieval/hybrid/`。

```python
from app.storage.vector.factory import get_vector_store
vector_store = get_vector_store()
vector_store.add_documents(docs, doc_id, tenant_id)

from app.storage.object.minio import minio_service
img_id = minio_service.upload_image(image_data, tenant_id, dataset_id, document_id, chunk_key)
url = minio_service.get_image_url(img_id)

from app.rag.retriever import hybrid_retriever
```

### 8. rag/ — RAG 引擎 📦

- `engine.py`：`get_rag_engine()` 返回 `RAGEngine`，核心方法 `stream_chat(question, *, context=None, rag_config=None, response_options=None)`，以流式事件输出。
- `graph.py`：导出 `build_rag_graph`、`run_rag_graph`，实现位于 `app/rag/pipelines/langgraph.py`。
- `agent.py`：`RAGAgent`，同样提供 `stream_chat`。
- `tools.py`：RAG 工具函数；`retriever.py`：`HybridRetriever` 与 `hybrid_retriever`。
- 主要子包：`chunking/`（切块）、`retrieval/`（检索与融合）、`reranker/`（重排序，含 `llm_based.py`、`hybrid.py`）、`evaluation/`（评估）、`kg/`（知识图谱）、`embedding/`、`llm/`、`workflows/`、`policy/`、`preprocessing/`、`safety/`、`industry_rules/` 等。

```python
from app.rag.engine import get_rag_engine
rag_engine = get_rag_engine()
# async for event in rag_engine.stream_chat(question, context=..., rag_config=...): ...

from app.rag.graph import run_rag_graph
from app.rag.agent import RAGAgent
```

### 9. rag/evaluation/ — 评估

RAG 评估（Ragas 等）位于 `app/rag/evaluation/`。`ragas.py` 中的回归评估入口是 `run_regression_ragas_evaluation`，参数较多，以源码为准。

```python
from app.rag.evaluation.ragas import run_regression_ragas_evaluation
```

### 10. services/ — 业务服务

高层业务逻辑，约 178 个文件，平铺在 `app/services/` 下。

```python
from app.services.dataset_service import DatasetService
from app.services.document_access import filter_allowed_document_ids
from app.services.prompt_resolver import resolve_prompt_template
```

**常用服务：**
- `dataset_service.py`：数据集管理
- `document_access.py`：文档权限
- `prompt_resolver.py`：提示词解析与选择
- `metrics_logger.py`：指标日志
- `mineru_service.py`：MinerU API 客户端
- `indexer.py`：统一索引器（chunk/event 入库、重建、删除）
- `pipeline_config.py`：文档级 pipeline 配置解析与合并

### 11. rag/kg/ — 知识图谱

从文档 chunks 抽取事件/实体，并提供图谱检索。路由在 `app/rag/kg/api/routes.py`，抽取在 `extraction/`，搜索在 `search/`。

## 依赖关系（设计上的分层）

```
┌─────────────────────────────────────────────┐
│           api/ (FastAPI 路由)               │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│        services/ (业务服务层)               │
└─────────────────┬───────────────────────────┘
                  │
        ┌─────────┼──────────────┐
        │         │              │
┌───────▼───┐ ┌───▼─────┐ ┌──────▼──────┐
│ parsing/  │ │ storage │ │   rag/      │
│   解析    │ │   存储  │ │ 检索/生成/评估 │
└───────┬───┘ └───┬─────┘ └──────┬──────┘
        │         │              │
        └─────────┴──────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│   models/ + api/schemas/ (数据层)           │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│           core/ (核心配置)                  │
└─────────────────────────────────────────────┘
```

## 导入路径对照表

| 旧路径 | 新路径 |
|--------|--------|
| `app.services.pdf_quality` | `app.parsing.quality.scorer` |
| `app.services.rapid_ocr_service` | `app.parsing.quality.ocr_validator` |
| `app.services.parsers` | `app.parsing.factory` |
| `app.services.chunkers` | `app.rag.chunking.factory` |
| `app.services.hierarchical_chunking` | `app.rag.chunking.utils.hierarchical` |
| `app.services.document_processor` | `app.parsing.processors.processor` |
| `app.services.document_parser_service` | `app.parsing.processors.parser_service` |
| `app.services.zip_image_processor` | `app.parsing.utils.zip_processor` |
| `app.services.vector_router` | `app.storage.vector.factory` |
| `app.services.milvus_store` | `app.storage.vector.milvus` |
| `app.services.minio_service` | `app.storage.object.minio` |
| `app.services.hybrid_retriever` | `app.rag.retriever` |
| `app.services.rag_engine` | `app.rag.engine` |
| `app.services.rag_graph` | `app.rag.graph` |
| `app.services.rag_agent` | `app.rag.agent` |
| `app.services.rag_tools` | `app.rag.tools` |
| `app.services.llm_reranker` | `app.rag.reranker.llm_based` |
| `app.services.ragas_evaluator` | `app.rag.evaluation.ragas` |

## 设计原则

### 1. 单一职责

每个模块只负责一类功能：
- `parsing/` 只管解析
- `storage/` 只管存储
- `rag/` 只管检索生成和评估

### 2. 低耦合

模块间通过清晰的接口交互，避免循环依赖。

### 3. 高内聚

相关功能集中在同一模块内，便于维护。

### 4. 易扩展

新功能有明确的归属位置。

## 开发指南

### 添加新解析器

在 `app/parsing/parsers/` 下实现，并在 `app/parsing/factory.py` 的后端注册表中接入。

### 添加新切块策略

在 `app/rag/chunking/` 下实现，并在 `app/rag/chunking/capabilities.py` 的能力表（`ChunkerCapability`）中登记。

### 添加新向量数据库

在 `app/storage/vector/` 下实现 `BaseVectorStore`（定义在 `factory.py`），并在 `get_vector_store()` 中接入。

### 添加新 RAG 策略

扩展 `app/rag/engine.py`，或在 `app/rag/pipelines/` 下新增编排文件。

### 添加新 API 路由

在 `app/api/v1/` 下创建路由文件，然后在 `app/api/v1/__init__.py` 的 `_build_router()` 中 `include_router(...)` 注册。

**认证约定（务必遵守）**：后端没有全局强制认证中间件——认证由**每个路由显式声明依赖**实现。新增任何路由都必须带认证依赖：

- 函数级：访问租户数据时同时声明 `tenant_id: Annotated[UUID, Depends(get_tenant_id)]` 和 `account_id: Annotated[str, Depends(get_current_account_id)]`；只需确认身份、不涉及租户数据时声明 `Depends(get_current_account_id)`；
- 路由级：`APIRouter(dependencies=[Depends(get_current_account_id)])`（整组路由统一鉴权，适合一组无租户数据但仍需认证的端点）。

即使是**纯计算、不访问数据库**的端点（如图算法工具）也必须认证，否则会成为未认证的计算/DoS 面；同时对客户端提供的列表/数组输入用 `Field(..., max_length=...)` 设上限，避免无界输入导致 CPU/内存耗尽。参考 `api/v1/network_analysis.py`（用路由级 `Depends(get_current_account_id)` + `edges` 上限）。

## 测试

- `tests/` 为平铺结构，约 405 个测试文件；子目录只有 `fixtures/`（136 个测试数据）、`helpers/`、`rag/`。
- 常用命令：

```bash
pytest tests/test_xxx.py   # 单个文件
pytest                     # 全量（pytest.ini 中 testpaths = tests）
```

- 按功能域拆分测试子目录的方案尚未执行，需先与维护者确认。

## 历史说明

2026 年的目录迁移已完成，导入路径映射见上表。本文件已于 2026-10-09 按当前仓库校正。
