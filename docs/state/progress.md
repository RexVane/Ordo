# 进度

## 2026-10-09 09:12 +08:00 | claude-opus-5-5 | 远端锁定与仓库整理
- 远端锁定：
  - `origin` = `https://github.com/RexVane/Ordo.git`（自己的仓库，可推），无 `upstream`
  - 整理前基线：`main` 与 `origin/main` 同步于 `a8f8c6a`
- 现状快照：
  - 后端 Python（`app/`，入口 `main.py`，alembic 迁移），前端 Next.js（`web/`，pnpm），文档站 Docusaurus（`docs-site/`）
  - 基础设施走 docker compose；本机 Windows 需叠加 `docker/docker-compose.infra.override.yml`（postgres 映射到 15432），启动流程见本地 `AGENTS.md`（已被 gitignore，不上 GitHub）
  - `tests/`（405 个文件）、`scripts/`（168 个文件）都是平铺，远超 15 个上限；整体拆分需另行和用户确认，本次未动
- 改了什么（提交 `dbdebf1`）：
  - 根目录散装的 `DESIGN_MEMORY.md`、`DESIGN_PLAN.md` 用 `git mv` 迁到 `docs/design/design-memory.md`、`docs/design/ingestion-operation-redesign.md`，后者里对前者的路径引用同步改掉；仓库内无其他引用
  - `.gitignore` 里原来的 `Ordo/` 没有锚定，Windows 大小写不敏感，把 `deploy/helm/ordo/` 下 31 个已跟踪的 helm 文件也算成了被忽略（`git ls-files -ci` 可见），以后新加的 helm 文件会进不了 git；改为 `/Ordo/`
  - 只属于本机的东西不上 GitHub：`docker/*.override.yml`（Hyper-V 端口重映射）、`/docs/interview-prep/`（个人面试准备）、`.pnpm-store/`、`/backups/`；另补 `.commandcode/`、`.grok/`、`.opencode/`、`.zcode/` 等 AI 工具私有目录
  ```gitignore
  # .gitignore:112
  # Machine-local compose overrides (e.g. Windows Hyper-V port remaps)
  docker/*.override.yml
  # .gitignore:130
  /docs/interview-prep/
  /web/docs/
  # Anchored: unanchored `Ordo/` also matched deploy/helm/ordo/ on case-insensitive filesystems
  /Ordo/
  ```
  - 根目录 0 字节的 `nul`（Git Bash 里 `> nul` 误生成的 Windows 保留名文件）移入 `backups/nul`
- 影响文件：`.gitignore`, `docs/design/design-memory.md`, `docs/design/ingestion-operation-redesign.md`
- 下一步：
  - `.pnpm-store/` 在项目根（`web/node_modules` 装依赖时用的是它），pnpm 默认路径其实是 `D:\.pnpm-store`；要挪走需重装一次 `web/node_modules`，待用户决定
  - `tests/`、`scripts/` 按域拆子目录，待用户决定

## 2026-10-09 10:27 +08:00 | claude-haiku-5-5 | 清理未使用的代码、文档与资源
- 改了什么：
  - 前因：用户要求取出没用的东西，方便学习项目。先用只读的静态可达性脚本（放在系统临时目录，未进仓库）从生产入口出发：`main.py`、`alembic/`、`docker/`、`deploy/`、`.github/`、`config/`，以及运行时扫描的 `plugins/pipelines/`；再算测试、文档的引用。候选还要满足：路径、点分模块名、文件名在其他非候选文件里都没出现，才移动。
  - 140 个文件移入 `backups/`（保留原路径，未真删），提交 `22c24fa`：
    - app 73 个模块：`app/rag/chunking/integrated_pipeline/{chunkers,common,nlp,stubs}` 是转发到 `app/third_party/integrated_pipeline` 的旧路径壳，已无引用；另有 `rag/workflows`、`rag/kg/search`、`rag/evaluation` 的实验/遗留模块，`app/services` 4 个未接入服务，`app/deepdoc/vision` 的调试 CLI（`t_ocr.py` 等）
    - scripts 14 个一次性脚本，未被 Makefile、CI、文档、代码引用
    - web 33 个未引用的组件、hooks、lib 文件，以及 `web/workers/graph-parser.worker.ts`
    - docs/images 16 张按文件名全仓库搜不到的截图和图标；docs/migrations 2 个 alembic 之前的 SQL（`alembic/versions/0001_baseline_schema.py` 已覆盖）；ci 2 个无人使用的 fixture JSON
  - 保留，原因各不同：
    - `scripts/backfill_kg_event_vector_metadata.py`：`scripts/README.md` 有说明
    - `web/types/*.typecheck.ts`：`tsconfig` 的 `**/*.ts` 会整体编译
    - `web/scripts/*`：Makefile 在调用
    - `scripts/perf/`：`python -m` 入口
    - `app/rag/evaluation/datasets/` 的 JSON：`validator.py`、`schema.py` 是在用代码，数据路径可能被外部读取，只移走了两个无人用的加载器
    - `*.ps1`、`*.sh` 启动器和 demo：人工入口
    - `docs/examples/`：API 示例
    - `web/public/`：logo 按 provider id 动态拼文件名
- 验证：
  - 移动后复跑图谱分析：生产可达的 Python 文件数不变（1335）；断裂导入 0；前端无引用文件只剩上面的保留项
  - `import app.main` 成功（425 条路由）；`pnpm typecheck` 通过
  - `pnpm test`：421 通过，2 失败（`chunk-preview-dataset-scope.source.test.ts`、`retrieve-preview-panel.source.test.ts`）。两者与本次移动无关：它们读取的源文件没有动，断言期望 LF 换行，而工作区里这些文件是 CRLF（`.gitattributes` 要求 `*.ts`、`*.tsx` 为 `eol=lf`）
  - 未跑 pytest：`.venv` 里没有安装 pytest
- 影响文件：140 个移动文件（`git show --stat 22c24fa` 可看完整清单）；`docs/state/progress.md`
- 下一步：
  - 还原任一文件：从 `backups/<原路径>` 移回，或 `git show 22c24fa^:<路径>`
  - 待用户决定：CRLF 工作区是否统一（`git add --renormalize` 或重新检出，都会改动工作区文件，需先确认）；是否安装 dev 依赖后跑 pytest
  - 仍未处理：`.pnpm-store/` 位置、`tests/`（405 个）和剩余 `scripts/` 的平铺结构、`docs/` 下 129 个未被链接的文档
