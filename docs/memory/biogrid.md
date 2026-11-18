# BioGRID 接入

> 2026-11-19，v0.5.0。第二个 key-gated 源（第一个是 Materials Project）。

- 免费 access key（32 位）在 https://webservice.thebiogrid.org/ 注册后生成；环境变量 `BIOGRID_ACCESS_KEY`，以 query 参数 `accesskey` 传递。
- 工具：`biogrid_interactions(genes, organism=9606, limit=100, offset=0)`；`genes` 用 `|` 分隔（`BRCA1|BRCA2`），`organism` 是 NCBI taxId（9606 human / 10090 mouse / 559292 yeast）。
- 响应是 **dict**（key = interaction id），不是 list；空结果是 `{}`，不是错误。字段：`OFFICIAL_SYMBOL_A/B`、`ENTREZ_GENE_A/B`、`ORGANISM_A/B`、`EXPERIMENTAL_SYSTEM`、`EXPERIMENTAL_SYSTEM_TYPE`、`PUBMED_ID`、`THROUGHPUT`、`SCORE`。
- 没有文档化的 total count；`next_offset` 只在**满页**时给出，语义是“可能还有”，不是精确总数。
- 无效 key 返回 **401 JSON** → `auth`（不是漂移）；非 JSON/非 dict 200 → `UpstreamDrift`。
- 限速未公布，本项目固定 1 req/s。
- 边界：只做 curated 互作查询；不做 bulk download、不做网络图可视化；与 STRING（M6）是互补关系。
