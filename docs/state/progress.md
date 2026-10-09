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
