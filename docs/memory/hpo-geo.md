# HPO / GEO（v0.9.0）

> 2026-11-19。两个免 key 源；GEO 复用 NCBI key 提速。

## HPO（Human Phenotype Ontology）

- 工具：`phenotypes(query, limit=10)`；查询是表型短语（"seizure"）或精确 `HP:0001250`。
- API：`https://ontology.jax.org/api/hp/search?q=...&limit=...` 和 `/terms/{HP:id}`；无 key。
- 精确 HP id 直接取单条；文本查询取 `terms` 列表。未知 id 返回 404 → `NotFound`。
- 归一化：id/name/definition/synonyms/descendant_count；`synonyms` 空时省略。
- 表型搜索不是基因→表型注释；后者需要 HPO 的 gene-phenotype 数据（未接）。

## GEO (NCBI)

- 工具：`geo_datasets(query, limit=10)`；`db=gds` 的 esearch + esummary。
- 字段：`accession`（GSE...）、`title`、`summary`、`gdstype`、`taxon`（不是 `organism`）、`n_samples`、`pdat`、`pubmedids`。
- 空 idlist → `count: 0`；缺 `esearchresult`/`result` → drift。
- NCBI key/email 复用 `Settings.ncbi_api_key` / `ncbi_email`。

## 未接

- **Ensembl REST**：`https://rest.ensembl.org` 仍不稳定；ping 偶尔 200，lookup 常 403/504；换出口后仍复现。
- **GTEx**：`gtexportal.org` 从当前网络 SSL EOF（`unexpected eof while reading`），暂缓。

## 验证

- 174 tests；keyed live 27/28（唯一失败为 ChEMBL 500 上游故障；HPO/GEO 均 PASS）。
