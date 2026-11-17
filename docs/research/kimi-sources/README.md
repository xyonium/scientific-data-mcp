# 立项证据：kimi 科研源的免费直连裁决

本目录是 finance-mcp 2026-09-13 去重工作的原文（R15–R17），每个文件对 kimi datasource 的一个源做裁决，并给出 live 实测的官方免费端点。

这些文件是 scientific-data-mcp 的立项依据：五个科研源全部是官方免 key API 的 1:1 薄包装，从 kimi 摘除后由本项目直连。

| 文件 | 源 | 裁决 |
|------|----|------|
| `pubchem.verdict.md` | PubChem PUG-REST | 摘 — 4/4 API 1:1，免 key |
| `chembl.verdict.md` | ChEMBL EBI REST | 摘 — 4/4 API 1:1，且官方是严格超集 |
| `uniprot.verdict.md` | UniProt REST | 摘 — 4/4 API 1:1，含 ID Mapping |
| `pdb.verdict.md` | RCSB PDB Data/Search | 摘 — 4/4 API 1:1，kimi 检索面更窄 |
| `pubmed.verdict.md` | NCBI E-utilities | 摘 — 官方本体 + paper-search 已覆盖 |

实施时发现的两处端点修正记在 [`../../memory/kimi-science-sources-verdicts.md`](../../memory/kimi-science-sources-verdicts.md)：ChEMBL 检索要用 `/<resource>/search.json?q=`；PubMed DOI 解析走 E-utilities esearch。

> 这些是历史证据，不随本项目代码演进；引用时以官方 API 文档为准。
