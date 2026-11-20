# 境外学术 API 的间歇性故障

> 迁移自 paper-search `flaky-foreign-academic-apis` / `ieee-api-flaky-hang`（2026-08），2026-11-17 在本项目实测复现。

现象：本机/容器访问境外学术 API 会间歇性出现 TLS 被对端提前断开（`SSL: UNEXPECTED_EOF_WHILE_READING`）或响应挂起至超时；突发并发、长查询时更明显。同一请求立即重试通常 1–2s 成功。单机 curl 正常不代表并发时正常。

2026-11-17 实测：
- ChEMBL `molecule.json?search_parameters__q=...` 单请求 20s 超时；同一时刻 `search.json?q=` 正常。慢/挂起是链路 + 端点双重问题。
- PMC ID converter（`www.ncbi.nlm.nih.gov`）20s 超时；换 `eutils.ncbi.nlm.nih.gov` 的 esearch 稳定。
- PubChem 首次请求 ~4s，之后正常；UniProt 2.3s；RCSB 1.2s；E-utilities 2.9s。

纪律：
- 所有外部调用必须带**有界重试 + 退避 + 总预算**（`PoliteClient`：网络错误指数退避，429/503 尊重 `Retry-After`，最多 4 次；`retry_budget=45s`，超出预算立即返回，避免一次工具调用挂 2 分钟）。
- 超时要有界，不要用无限等待；用户可见的失败是 `{"error": "unavailable: ..."}`，不是挂死。
- 区分"偶发 SSL EOF/超时"（重试可解）和"必现 4xx/404"（代码/端点 bug，重试无用）。
- 新增源时优先选同一 host 上更稳的端点（例：DOI→PubMed 用 esearch 而不是 idconv）。

## 全球出口 / 代理

- 目前**没有任何源是因为 IP 被限制而排除的**：USPTO 是 ID.me 实名（身份，不是 IP），Eurostat/Census/DataCommons 是解析成本/优先级，WHO 目录端点是 CDN 504，ChEMBL 的 500 在外部 IP（Jina/Firecrawl）同样复现，属上游故障。
- 若要把不稳定 host 走全球出口：`httpx` 默认 `trust_env=True`，给 MCP 进程/容器设 `HTTPS_PROXY` / `ALL_PROXY` 即可全局生效；**按域名分流**需要本地转发代理（Envoy/Privoxy 等）按 host 规则转发，应用层未实现 per-host 代理。
- 值得单独路由观察的 host：`www.ebi.ac.uk`（ChEMBL 慢/500）、`ghoapi.azureedge.net`（WHO 502/504）、`rest.uniprot.org`（偶发 network error）、`eutils.ncbi.nlm.nih.gov`、`api.materialsproject.org`。注意：全局故障换出口无效。


## Ensembl REST（2026-11-19）

- 正确 base 是 `https://rest.ensembl.org`；`/lookup/symbol/homo_sapiens/TP53?content-type=application/json` 和 `/info/ping` 均可用（正常时）。
- 当次故障表现：DNS 解析到 AWS ALB（3.8.72.101 / 13.43.212.132），TCP 443 可连，但 TLS ClientHello 后 20–60s 无响应；`www.ensembl.org` 正常（193.62.193.83）。
- 独立验证：Firecrawl/Jina 抓取失败，allorigins/codetabs 返回 **522**，说明是 REST 后端/边缘不可达，不是我们 URL 拼错。
- 处理：不接入未验证的 provider；等 REST 恢复，或让 `rest.ensembl.org` 走可用出口后再实现。


## 上游探测纪律（2026-11-20 起）

- 不做短时突发探测；同一 host 连续请求间隔 ≥1s，边界/变体测试合并成少量请求。
- 403/429 **不重试**、不换 UA/路径/IP；记录一次并停止，冷却 ≥24h。
- 不通过轮换节点绕过封锁；不把不稳定源放进 CI/smoke。
- Ensembl 已按此规则暂停，见 `ensembl-rest-access.md`。
