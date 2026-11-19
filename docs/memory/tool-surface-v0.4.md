# 工具面收敛（v0.4.0）

> 2026-11-18。从 15 个工具收到 8 基础 + 1 MP。原则：**同样输入/输出结构的合并，用 `kind`/`by` 切换**；不同结构（record vs list vs mapping）不硬塞进一个 schema。

## 合并映射

| 旧 | 新 |
|---|---|
| `chem_compound` + `chem_compound_properties` | `chem_compound(identifier, id_type, properties?)` |
| `chembl_search` + `chembl_bioactivity` + `chembl_mechanisms` | `chembl_data(kind="search"|"activities"|"mechanisms", ...)` |
| `protein_entry` + `protein_structure` | `protein_record(kind="uniprot"|"pdb", identifier, include_sequence?)` |
| `protein_search` + `protein_structure_search` | `protein_search(kind="uniprot"|"pdb", query, size, cursor?)` |
| `material_get` + `material_search` | `material(by="id"|"formula"|"chemsys"|"elements", query, limit?)` |

保留独立：`chem_similar_compounds`（SMILES→CID 列表）、`protein_map_ids`（mapping envelope）、`pubmed_record`（单记录）、`who_data`（观测列表）、`material`（v0.4.0 合并后单工具）。v0.6.0 把 BioGRID 与 STRING 合并为 `protein_interactions(source=...)`，并新增 `openfda`、`clinical_trials`；v0.7.0 再加 AlphaFold（并入 protein_record）、opentargets、pathways；v0.8.0 再加 gene_record/clinvar/protein_annotations；v0.9.0 再加 phenotypes/geo_datasets；基础工具 18 个（MP key 时 19 个）。

## 设计约束

- 合并工具跨 source 时，工具内部 catch `ProviderError` 并按实际 source 返回（`provider_error_payload`）；外层 `guarded_tool` 只兜底意外异常。
- `protein_search(kind="pdb")` 的 cursor 是数字 offset 的字符串；`kind="uniprot"` 是官方 opaque cursor。描述里写清楚，别让模型混用。
- 不为了少而少：5 个 domain 容器（chemistry/protein/...）会把 10+ 个可选参数塞进一个 schema，模型更容易传错；finance 的 Futu 容器是给同构 action 用的，不是把所有任务揉一起。
