# UniChem / SABIO-RK（v0.20.0，免 key）

> 2026-11-22。UniChem 补化合物跨库 ID；SABIO-RK 补带实验条件的动力学。

## UniChem

- 工具：`unichem_map(inchikey, limit=20)`；标准 27 字符 InChIKey。
- `GET https://www.ebi.ac.uk/unichem/rest/verbose_inchikey/{inchikey}`；返回 list，每项含 source/name_long/src_id/src_compound_id[]/src_url。
- 只保留有 compound id 的源；按 limit 截断；1s host delay（与 www.ebi.ac.uk 共用）。
- 响应很大（aspirin 约 465KB），不要放大 limit；用于 ID 映射，不替代 PubChem/ChEBI 记录。

## SABIO-RK

- 工具：`sabio_kinetics(ec_number, page=1, limit=20)`。
- **新 export API**：`https://sabiork.h-its.org/export-api/sabio/kinlaw-entry/json?q=ecnumber:{ec}&page=&pageSize=`。
- 旧 `sabioRestWebServices` 路径 404；不要再使用。
- 响应 `{meta:{page,page_size,total_count,total_pages}, data:[...]}`。
- 归一化：sabio_id、organism、EC、enzyme/mutant、equation、kinetic law type/formula、parameters（name/value/end/unit/species/comment）、pH/温度/缓冲液、PubMed/title/year/journal。
- 1s host delay（官方 60 req/min）；免 key；空 data 正常，缺 meta/data → drift。
- 与 BRENDA 互补：SABIO 带实验条件，BRENDA 覆盖更全的动力学/突变/抑制剂。

## ClinGen

- 只找到基因搜索 `/api/genes/lookByName/{query}`（返回 hgnc/curated/has_validity 标志），未找到公开的基因-疾病 validity 条目 API；暂不接，避免抓 HTML。

## 验证

- 262 tests；live：UniChem aspirin InChIKey 3 源、SABIO EC 1.1.1.1 total 768 条 PASS。
