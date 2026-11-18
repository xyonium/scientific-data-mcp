# 项目记忆索引

> 从 Claude Code 的 per-project memory 迁移而来（2026-11-17）。DSH 不会自动加载 memory 目录，所以这里的笔记由 `AGENTS.md` 显式指引；改对应域之前先读。

- [kimi 五个科研源的裁决与端点](kimi-science-sources-verdicts.md) — pubchem/chembl/uniprot/pdb/pubmed 全是官方免 key 1:1 镜像；kimi 侧无需改动
- [发布管路 hatch-vcs](publishing-hatch-vcs.md) — 版本只来自 tag；硬编码 version + 打 tag = PyPI 静默丢包
- [密钥、环境与限速](secrets-and-quotas.md) — 本服务零必需 key；NCBI_API_KEY 可选；不读 .env
- [境外学术 API 的间歇性故障](flaky-upstream-apis.md) — SSL EOF / 挂起 / ChEMBL 9s，重试即恢复；必须带退避
- [工具描述纪律](tool-description-discipline.md) — 给人看的源列表不可删；反幻觉 docstring 是硬要求
- [与兄弟项目的边界](boundary-with-siblings.md) — paper-search 管文献检索/RAG，本项目管实体数据
- [从 Claude Code 迁到 DSH](dsh-migration.md) — 迁移做了什么、为什么、以后别再引入 .claude 依赖
- [Materials Project 的 key-gated 形态](materials-project-key-gate.md) — 无 key 不注册工具；MP 是 80 库里唯一需 key 的当前源
- [K-Dense 数据源清单追踪](kdense-catalogue-tracking.md) — v1.8 仍 80 库；季度 Action + 快照 diff
- [2026-11-18 K-Dense 归属审计](kdense-catalogue-tracking.md) — finance 只补 SEC EDGAR；paper 的 USPTO 暂不加
