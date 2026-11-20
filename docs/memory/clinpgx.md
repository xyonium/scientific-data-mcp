# ClinPGx（v0.16.0）

> 2026-11-20。PharmGKB 后继；免 key，公开只读。

## 工具

- `clinpgx(gene, drug="", limit=10)`；gene 必填（`CYP2C19`），drug 可选（`clopidogrel`）。
- `GET https://api.clinpgx.org/v1/data/summaryAnnotation`：
  - `location.genes.symbol={gene}`
  - 有 drug 时加 `relatedChemicals.name={drug}`
- 响应 `{data:[...], status:"success"}`；`data` 列表按 limit 截断。
- 归一化：annotation_id、accession_id、name、gene/gene_id、drug/drug_id、level_of_evidence（`levelOfEvidence.term`）、allele_phenotypes（allele/phenotype/limited_evidence）、related_guidelines/diseases/labels、score。
- 0 条是正常空结果；缺 `data` 或 status 非 success → drift。
- 1s host delay（官方 ≤2 req/s）；免 key。

## 不做/暂缓

- **COD**：`www.crystallography.net` 从本网络三个变体都 45s 超时，暂缓。
- **ZINC**：仍返回 captcha/跳转，不绕过，暂缓。
- ClinPGx 只做 summaryAnnotation；guidelineAnnotation/label 需要 PA accession，后续按需。

## 验证

- 237 tests；live CYP2C19+clopidogrel：PA166134797 / 1A PASS。
