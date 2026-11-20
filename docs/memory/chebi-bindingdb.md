# ChEBI / BindingDB（v0.13.0）

> 2026-11-20。化学批次；两者都免 key。

## ChEBI

- 工具：`compound_lookup(source="chebi", query, limit=5)`；名称或 `CHEBI:15365`（也接受 `CHEBI_15365`）。
- 入口用 **EBI OLS4**（ChEBI 2.0 旧 REST 从本网络 301/404/超时）：
  - 搜索 `https://www.ebi.ac.uk/ols4/api/search?q=...&ontology=chebi&rows=...`
  - 精确 `https://www.ebi.ac.uk/ols4/api/ontologies/chebi/terms?iri=http://purl.obolibrary.org/obo/CHEBI_15365`
- 归一化：chebi_id（`obo_id`）、name（`label`）、description（列表首项）、synonyms、is_obsolete。
- 搜索 `docs` 缺 → drift；term 列表空 → NotFound。
- 0.5s host delay；免 key。

## BindingDB

- 工具：`bindingdb_ligands(uniprot, cutoff_nm=10000, limit=20)`。
- `https://bindingdb.org/rest/getLigandsByUniprot?uniprot={acc};{cutoff}&response=application/json`。
- 响应 key 拼写是 **`getLindsByUniprotResponse`**（少一个 a）；ligands 在 `bdb.affinities[]`，字段 `bdb.monomerid`/`bdb.smile`/`bdb.affinity_type`/`bdb.affinity`（值带前导空格）。
- 空 body → `count: 0`；缺响应 key → drift；`retry=False`，1s host delay，免 key，~1 req/s。
- `bdb.hit` 是总数；items 按 limit 截断。

## 验证

- 224 tests；live：ChEBI aspirin/ CHEBI:15365、BindingDB P35355 均 PASS。
