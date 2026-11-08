# Releases / 发布索引

This folder contains the curated public release notes for Ordo.
Git tags remain the authoritative history; this folder is the human-readable layer for GitHub Releases, README links, and external announcements.

## Latest release / 当前最新版本

| Version | Status | Focus |
| --- | --- | --- |
| [v1.0.2](./v1.0.2.md) | Latest stable | Vector backend fail-fast, Apache-only default PDF parser, consistent release versions |
| [v1.0.1](./v1.0.1.md) | Previous stable | Safe first-run bootstrap, isolated Docker cleanup, complete operation guide, current UI screenshots |
| [v1.0.0](./v1.0.0.md) | Previous stable | Docker + host quick start, Dify integration, real-model 800-question validation, strict provenance gates |

## Previous milestone / 里程碑

| Version | Focus |
| --- | --- |
| v0.8.0 | Universal knowledge hardening, concurrent upload safety, ACL isolation, local reranker retention |

## Tag and publish / 打标签与发布

The git tag is the source of truth. Before tagging, run:

```bash
make check-versions
make release-check
git tag -a v1.0.2 -m "Ordo v1.0.2"
git push origin v1.0.2
```

Pushing a `v*` tag triggers `.github/workflows/release.yml`, which re-checks the
version, builds the API/Web images, pushes them to GHCR, and creates the GitHub
Release from `docs/releases/v<version>.md`.

发布前先跑 `make check-versions` 和 `make release-check`；推送 `v*` tag 后由
`.github/workflows/release.yml` 复核版本、构建镜像、推送 GHCR 并从对应发布说明
创建 GitHub Release。

## Writing rules / 写作规则

- Keep the title short and versioned.
- Put facts in tables before prose.
- Link benchmark and gate artifacts instead of repeating long history.
- Keep Chinese and English in the same page when the release is public-facing.
- Use the same structure across versions so tag pages stay visually consistent.
