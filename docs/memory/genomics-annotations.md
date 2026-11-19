# NCBI Gene / ClinVar / InterPro / QuickGO（v0.8.0）

> 2026-11-19。NCBI Gene/ClinVar 走 E-utilities，可选 NCBI key 提速；InterPro/QuickGO 免 key。

## 工具

| 工具 | source | 说明 |
|---|---|---|
| `gene_record(identifier, organism=9606)` | `ncbi_gene` | 基因符号或数字 Gene ID → 一条记录 |
| `clinvar(query, limit=10)` | `clinvar` | ClinVar 检索 → 列表（分类、review status、条件、基因） |
| `protein_annotations(identifier, source="interpro"\|"quickgo", limit=20)` | `interpro` / `quickgo` | 同一 UniProt accession 的两种注释 |

## NCBI Gene

- `esearch.fcgi?db=gene&term={symbol}[gene] AND {taxid}[taxid]` → `esummary.fcgi?db=gene`。
- 数字 identifier 直接跳过 esearch 走 esummary。
- ESummary 字段：`name`/`description`/`chromosome`/`maplocation`/`otheraliases`/`summary`/`organism`；`geneticsource` 作为 `gene_type`。
- 无命中 → `NotFound`；缺 `esearchresult`/`result` → drift。
- NCBI key/email 复用 `Settings.ncbi_api_key` / `ncbi_email`。

## ClinVar

- `esearch.fcgi?db=clinvar` → `esummary.fcgi?db=clinvar`。
- **分类不在顶层 `clinical_significance`**：在 `germline_classification.description` / `review_status` / `last_evaluated`；条件在 `germline_classification.trait_set[].trait_name`。
- 变异信息在 `variation_set[0]`（`variation_name`、`variant_type`、`canonical_spdi`）；基因在 `genes[].symbol`。
- 空 idlist → `count: 0`，不是错误。

## InterPro

- `https://www.ebi.ac.uk/interpro/api/entry/all/protein/uniprot/{acc}/?page_size={limit}`。
- 返回 `{count, results[].metadata}`；`metadata.name` 可能为 null（成员库条目），省略；`go_terms` 保留 id/name。
- 用 `entry/all`（含 Pfam/CDD/CATH 等成员库），不是只 `entry/interpro`。

## QuickGO

- `https://www.ebi.ac.uk/QuickGO/services/annotation/search?geneProductId=UniProtKB:{acc}&limit={limit}`。
- 返回 `{numberOfHits, results[]}`；字段 `goId`、`goName`（常为 null）、`qualifier`、`goEvidence`、`goAspect`、`reference`、`assignedBy`、`taxonId`。
- 工具接受并剥离 `UniProtKB:` 前缀。

## 验证

- 161 tests；keyed live 26/26（首轮 25/26 为瞬时网络失败，复跑全过）。
