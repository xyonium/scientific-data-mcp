# 发布管路：hatch-vcs

> 迁移自 finance-mcp `publish-pipeline-hatch-vcs`（2026-09-12/14）。

- `pyproject.toml` 用 `dynamic = ["version"]` + `[tool.hatch.version] source = "vcs"`：**版本完全由 git tag 推导**。
- 发布 = 打 `v*` tag 并 push。**不要手改 pyproject 里的版本号**。
- 事故（2026-09-11）：硬编码 `version = "0.1.2"` 后打 `v0.1.3` tag，wheel metadata 仍是 0.1.2 → PyPI 视为重复**静默丢弃**，workflow 却 success，版本卡了一天没人发现。
- 若走容器/`uvx` 从 PyPI 拉包：发布后几分钟内某些 pip 缓存层看不到新版本，需 `--index-url https://pypi.org/simple --no-cache-dir` 强刷。
- Docker 构建没有 `.git`，hatch-vcs 会回退到 `fallback_version`（pyproject 里已设 `0.0.0`），镜像内版本号不代表发布版本——需要真实版本时在构建参数里注入 `SETUPTOOLS_SCM_PRETEND_VERSION`。

本项目当前发布形态：public GitHub repo + tag，暂不发布 PyPI（名字 `scientific-data-mcp` 已验证可用）。
