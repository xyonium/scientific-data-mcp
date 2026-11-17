# 境外学术 API 的间歇性故障

> 迁移自 paper-search `flaky-foreign-academic-apis` / `ieee-api-flaky-hang`（2026-08），2026-11-17 在本项目实测复现。

现象：本机/容器访问境外学术 API 会间歇性出现 TLS 被对端提前断开（`SSL: UNEXPECTED_EOF_WHILE_READING`）或响应挂起至超时；突发并发、长查询时更明显。同一请求立即重试通常 1–2s 成功。单机 curl 正常不代表并发时正常。

2026-11-17 实测：
- ChEMBL `molecule.json?search_parameters__q=...` 单请求 20s 超时；同一时刻 `search.json?q=` 正常。慢/挂起是链路 + 端点双重问题。
- PMC ID converter（`www.ncbi.nlm.nih.gov`）20s 超时；换 `eutils.ncbi.nlm.nih.gov` 的 esearch 稳定。
- PubChem 首次请求 ~4s，之后正常；UniProt 2.3s；RCSB 1.2s；E-utilities 2.9s。

纪律：
- 所有外部调用必须带**有界重试 + 退避**（`PoliteClient` 已做：网络错误指数退避，429/503 尊重 `Retry-After`，最多 3 次）。
- 超时要有界，不要用无限等待；用户可见的失败是 `{"error": "unavailable: ..."}`，不是挂死。
- 区分"偶发 SSL EOF/超时"（重试可解）和"必现 4xx/404"（代码/端点 bug，重试无用）。
- 新增源时优先选同一 host 上更稳的端点（例：DOI→PubMed 用 esearch 而不是 idconv）。
