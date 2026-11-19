# GDC / cBioPortal / GTEx（v0.11.0）

> 2026-11-20。临床/表达批次；三者都免 key。

## cancer_studies

- `cancer_studies(query, source="gdc"|"cbioportal", limit=10)`。
- **GDC**：`https://api.gdc.cancer.gov/projects?size=500&format=json`；GDC 的 `filters`/`q` 对项目名过滤不可靠，直接取全量（93 个项目）本地按 project_id/name/primary_site/disease_type 过滤。
- **cBioPortal**：`https://www.cbioportal.org/api/studies?keyword=...&pageSize=...&pageNumber=0`；有 `keyword`，返回 list。
- GDC 有过滤后 `total`；cBioPortal 不返回总数，省略 `total`。
- 空结果 `count: 0`；非 list/缺 hits → drift。

## gene_expression

- `gene_expression(gene_id, dataset="gtex_v8", limit=20)`；`gene_id` 是 Ensembl ID（可带版本）。
- 两步：`/reference/gene?geneId=...` 拿 `gencodeId`（带版本），再 `/expression/medianGeneExpression?gencodeId=...&datasetId=gtex_v8`。
- 返回 tissueSiteDetailId/ontologyId/median/unit(TPM)/datasetId；`total` 来自 paging_info.totalNumberOfItems。
- 未知 gene → `NotFound`；缺 data → drift。
- GTEx 换节点后可达；Ensembl REST 仍 403/504。

## 验证

- 202 tests；keyed live 29/32（ChEMBL 网络故障 + MP 瞬时 403；GDC/cBioPortal/GTEx 均 PASS）。
- MP 403 复测：带 key 直接 curl 200，属瞬时/限流，不是 key 失效。
