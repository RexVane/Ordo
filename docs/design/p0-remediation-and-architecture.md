# P0 加固与架构图（v1.0.2）

本文记录 v1.0.2 的三项 P0 修复，以及 Ordo 的核心架构图与关键时序图。图中虚线/注释表示默认关闭或可选分支。

## 1. 已落地的 P0 修复

### 1.1 向量后端 fail-fast

- `VECTOR_BACKEND` 只接受 `milvus`、`memory`、`faiss`、`chroma`。
- `qdrant` / `pgvector` 的占位实现不再注册到工厂；显式选择会在 `get_vector_store()` 阶段直接抛 `ValueError`。
- 未知 backend 不再回落到 `StubVectorStore`；`VECTOR_REGION_BACKENDS` 也会在运行时二次校验。
- `memory` 标记为 `ephemeral`，生产环境启动校验直接拒绝；readiness 的 `vector` 字段会返回 `persistence`。
- 旧的占位模块保留为兼容导入，但不再有工厂路径；如确认不再需要，可在下一次清理中移入 `backups/`。

### 1.2 发布基线

- 以 `v1.0.1` 标注既有基线，本次改动版本为 `1.0.2`。
- `app/__init__.py`、`web/package.json`、Helm `appVersion`、README badge、最新发布说明由 `scripts/release/check_versions.py` 统一校验。
- `make check-versions`、`make release-check`、`make release-tag VERSION=x.y.z` 已加入 Makefile。
- `.github/workflows/release.yml` 在 `v*` tag 上复核版本、构建并推送 API/Web 镜像、创建 GitHub Release。

### 1.3 PDF 解析去 PyMuPDF

- 默认 `basic` PDF 解析器改用 `pdfplumber`（文本、坐标、嵌入图片、页面渲染），质量评分改用 `pypdf` 读取旋转与注释。
- `PyMuPDF` 从 `requirements.txt` 移除，放入可选的 `requirements-agpl.txt`；默认镜像不包含 AGPL 运行时。
- 仍使用 PyMuPDF 的可选能力（OCR 校验、图像预处理、水印、VLM 校正、DeepSeek OCR、ETL4LLM、Docling 回退）改为惰性加载；未安装时抛出带许可证说明的 `RuntimeError`。
- 新增测试：`test_pdf_parser_parity.py`、`test_no_agpl_default_imports.py`、`test_vector_backend_contracts.py`、`test_version_consistency.py`。

## 2. 容器与依赖关系

```mermaid
flowchart LR
  B["Browser / Next.js 16"] -->|"REST + SSE /api/v1/*"| A["FastAPI ordo-api :8000"]
  A -->|"SQLAlchemy"| PG[("PostgreSQL 15")]
  A -->|"向量 upsert / search"| MV[("Milvus 2.6")]
  A -->|"队列 / 锁 / 缓存"| RD[("Redis 7")]
  A -->|"对象存储"| MI[("MinIO / local uploads")]
  A -->|"LLM + embedding"| LLM["OpenAI-compatible / local models"]
  W["arq ordo-worker"] --> PG
  W --> MV
  W --> RD
  W --> MI
  W --> P["Parser subprocess"]
  P --> PS["Optional parser services<br/>Docling / MinerU / Marker / PaddleVL / ..."]
  A --> P
  OBS["Prometheus / OTEL / Sentry"] -.-> A
  OBS -.-> W
```

要点：

- API 与 Worker 共用镜像；Worker 承担持久化入库，API 在队列关闭时退化为后台线程/内联处理。
- BM25 默认是进程内索引；多副本部署需要每副本预热，或切换到共享 PostgreSQL 词法召回。
- LLM/Embedding 是外部服务；默认栈不包含本地大模型。

## 3. 文档入库时序

```mermaid
sequenceDiagram
  autonumber
  participant U as 用户
  participant W as Web
  participant A as API
  participant R as Redis
  participant DB as PostgreSQL
  participant S as MinIO/upload
  participant K as Worker
  participant P as Parser 子进程
  participant X as 可选解析服务
  participant C as Chunker
  participant I as Indexer
  participant M as Milvus
  participant B as BM25/PG

  U->>W: 上传文件
  W->>A: POST /api/v1/documents
  A->>A: 认证 + 租户 + 扩展名/大小 + 去重
  A->>S: 保存原文件
  A->>DB: 插入 Document(status=processing)
  alt TASK_QUEUE_ENABLED=true
    A->>R: enqueue doc:{tenant}:{doc}:{pipeline_hash}
    R->>K: 投递任务
  else 队列关闭
    A->>K: BackgroundTasks / 线程内联
  end
  K->>R: SET NX EX 获取入库锁 + 心跳
  K->>DB: 读取 pipeline 配置
  K->>P: parse(file, backend=auto)
  P->>X: 远程解析（可选）
  P-->>K: documents + backend
  K->>C: Normalize（常开）→ Governance（可选）→ 切块
  C-->>K: chunks
  K->>I: 统一索引
  I->>M: 向量 upsert
  I->>B: PG chunks + BM25
  I->>DB: status=completed, pipeline_hash
  W->>A: 轮询 /documents/{id}/status
  A-->>W: 进度/完成/失败
```

要点：

- 解析在独立子进程里做，避免 OCR/解析阻塞 API 事件循环；失败落 `IngestDeadLetter`，可 replay。
- 索引是“三写”：Milvus、PG chunks、BM25；任何一路失败都会影响检索通道，需要看 `DocumentIndexChannel` 状态。

## 4. 问答/检索时序

```mermaid
sequenceDiagram
  autonumber
  participant U as 用户
  participant W as Web
  participant A as API
  participant AU as Auth/Tenant
  participant CA as Chat cache
  participant E as RAGEngine
  participant R as HybridRetriever
  participant V as Milvus
  participant BM as BM25/Lexical
  participant F as Fusion/Rerank
  participant L as LLM
  participant DB as PostgreSQL

  U->>W: 提问
  W->>A: POST /api/v1/chat/stream (SSE)
  A->>AU: JWT + 租户 + 成员校验 + 配额/限流
  AU-->>A: scope
  A->>CA: 查回答缓存（默认开）
  alt 缓存命中
    CA-->>A: 缓存答案 + citations
    A-->>W: SSE token/done
  else 缓存未命中
    A->>E: stream_chat(question, scope, rag_config)
    E->>E: Query Rewrite / Multi-Query / HyDE / 分解（默认关）
    E->>R: 按 query variant 检索
    R->>V: 向量检索（dataset shard）
    R->>BM: BM25 / lexical
    V-->>F: 通道结果
    BM-->>F: 通道结果
    F->>F: budgeted RRF + 可选 rerank
    F-->>E: 融合上下文
    E->>E: 上下文预算 + citations
    E->>L: 流式生成
    L-->>E: token
    E->>E: 证据 span / claim 校验 / 拒答（默认关）
    E-->>A: status/citations/token/done
    A-->>W: SSE 事件
    A->>DB: 保存 messages + citations + metrics
  end
```

要点：

- 默认路径是 Milvus + BM25/lexical + budgeted RRF，不重排、不强制 span、不拒答。
- 回答缓存默认开，且要求空历史才命中；多轮对话不会误用单轮缓存。
- 检索 admission timeout 默认 15s，超时返回 503，而不是静默空结果。

## 5. 证据/引用校验流

```mermaid
flowchart TD
  H["混合检索命中"] --> C["build_citations_from_docs"]
  C --> S{"RAG_EVIDENCE_REQUIRE_SPANS_ENABLED"}
  S -- "true" --> V["严格 span 过滤 / citation 修复"]
  S -- "false（默认）" --> K["claim verifier：token overlap / heuristic"]
  V --> K
  K --> Q{"claims supported?"}
  Q -- "yes" --> ANS["带引用的回答"]
  Q -- "no" --> AB{"RAG_ABSTAIN_ENABLED"}
  AB -- "true" --> REF["拒答 / 证据不足"]
  AB -- "false（默认）" --> COR["corrective second pass / repair"]
  COR --> K
```

合规场景应显式打开 `RAG_EVIDENCE_REQUIRE_SPANS_ENABLED` 与 `RAG_ABSTAIN_ENABLED`。

## 6. 核心数据模型（简化）

```mermaid
erDiagram
  TENANT ||--o{ TENANT_MEMBER : has
  USER ||--o{ TENANT_MEMBER : joins
  TENANT ||--o{ DATASET : owns
  DATASET ||--o{ DOCUMENT : contains
  DOCUMENT ||--o{ DOCUMENT_CHUNK : splits
  DOCUMENT ||--o{ DOCUMENT_PERMISSION : acl
  TENANT ||--o{ CONVERSATION : owns
  CONVERSATION ||--o{ MESSAGE : contains
  MESSAGE ||--o{ MESSAGE_FEEDBACK : receives
  DATASET ||--o{ RAGAS_REGRESSION_CASE : evaluates
  DOCUMENT ||--o{ EVIDENCE_ITEM : supports
  TENANT ||--o{ AUDIT_LOG : records
  CONNECTOR_CONFIG ||--o{ CONNECTOR_RUN : runs
  CONNECTOR_RUN ||--o{ DOCUMENT : ingests
```

## 7. 验证命令

```bash
python scripts/release/check_versions.py
pytest -q tests/test_pdf_parser_parity.py tests/test_no_agpl_default_imports.py
pytest -q tests/test_vector_backend_contracts.py tests/test_version_consistency.py
ruff check app/parsing/parsers/pdf_parser.py app/storage/vector/factory.py
```

完整解析回归建议使用：

```bash
python -m app.rag.evaluation.parse_bench run \
  --input-dir tests/fixtures/parsing_golden \
  --manifest tests/fixtures/parsing_golden/manifest.json \
  --parsers basic --max-files 8 \
  --out artifacts/parser_benchmark.plumber.json \
  --baseline ci/parser_benchmark_baseline.v1.json \
  --strict-profile ci/parser_strict_profile.v1.json --strict
```
