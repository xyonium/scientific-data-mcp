# Rhea / M-CSA（v0.19.0，免 key）

> 2026-11-22。酶反应 + 催化机制；补 BRENDA 的动力学和 KEGG/Reactome 的通路层。

## Rhea

- 工具：`rhea_reactions(query, limit=10)`。
- `GET https://www.rhea-db.org/rhea?query={query}&format=json`；query 可为 EC、ChEBI id、化合物名、Rhea id。
- 响应 `{count, results:[{id,equation,status,comment,balanced,transport}]}`；`count` 是总数，items 按 limit 截断。
- 0 条是正常空结果；缺 results/count → drift。
- 0.5s host delay；免 key。

## M-CSA

- 工具：`mcsa_sites(enzyme="", uniprot="", mcsa_id="", limit=5)`；三个过滤条件必须恰好一个。
- `GET https://www.ebi.ac.uk/thornton-srv/m-csa/api/entries/?format=json`：
  - EC：`entries.reactions.ecs.codes=1.1.1.1`
  - UniProt：`entries.proteins.sequences.uniprot_ids=P00334`
  - M-CSA id：`entries.mcsa_ids=255`
- 响应 `{count, results:[...]}`；归一化 mcsa_id/enzyme_name/ec_numbers/uniprot_id/description/reaction/催化 residues（residue/roles/pdb/chain）。
- 0 条正常；缺 results/count → drift。
- 1s host delay（与 www.ebi.ac.uk 共用）；免 key。

## SABIO-RK

新 export API 已确认并接入：`/export-api/sabio/kinlaw-entry/json`；见 `unichem-sabio.md`。旧 `sabioRestWebServices` 已废弃。

## 验证

- 256 tests；live EC 1.1.1.1：Rhea 3 条、M-CSA 5 条 PASS。
