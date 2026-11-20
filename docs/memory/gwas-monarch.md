# GWAS Catalog / Monarch（v0.15.0）

> 2026-11-20。临床关联补全；两者都免 key。

## GWAS Catalog

- 工具：`gwas_associations(query, by="auto", limit=10, page=0)`。
- **旧 REST `/rest/api/` 已 410 下线**；用 v2：`https://www.ebi.ac.uk/gwas/rest/api/v2/associations`。
- v2 支持的过滤参数：`rs_id`、`efo_trait`、`efo_id`、`mapped_gene`；`diseaseTrait`/`reported_trait` 被忽略。
- auto：`rs\d+` → rs_id（大小写归一）；`MONDO/EFO/HP/ORPHA/DOID` id → efo_id（前缀大写、冒号转下划线）；其他 → efo_trait（必须是 EFO 精确 label）。基因符号请显式传 `by="mapped_gene"`。
- 响应：`_embedded.associations[]` + `page.totalElements`；归一化 association_id/p_value/reported_trait/efo_traits/mapped_genes/risk_frequency/beta/snp_effect_allele/pubmed_id/first_author/accession_id。
- 分页 0-based `page` + `size`；返回 `next_page`（最后一页 null）。缺 `_embedded`/`page`/非数字 total → drift。

## Monarch

- 工具：`monarch_associations(entity, category="gene_disease", limit=10, offset=0)`。
- `https://api.monarchinitiative.org/v3/api/association?entity=...&category=...&limit=&offset=`。
- 类别映射：gene_disease → `biolink:CausalGeneToDiseaseAssociation`；gene_phenotype → `biolink:GeneToPhenotypicFeatureAssociation`；disease_phenotype → `biolink:DiseaseToPhenotypicFeatureAssociation`；all → 不传。
- 注意 Monarch **没有** `biolink:GeneToDiseaseAssociation`（422）；基因-疾病用 Causal。
- 归一化 subject/object id+label+category、predicate、category、publications、primary_knowledge_source。
- 0 items 是正常空结果；缺 `items`/非数字 total → drift。

## 验证

- 231 tests；live：GWAS rs7412（1185 条）、Monarch FBN1（18 条）均 PASS。
