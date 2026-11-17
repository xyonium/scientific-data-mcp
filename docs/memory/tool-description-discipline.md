# 工具描述纪律

> 迁移自 paper-search `tool-description-source-list-permanent`（2026-08-06）。

1. **给人看的源列表永远不要删。** 工具/模块描述里的完整源清单（如 "PubChem / ChEMBL / UniProt / RCSB PDB / PubMed"）是给人在 OpenWebUI hover 时快速了解覆盖面的，受众是人不是 LLM。只能更正、改名、补充，不能以"冗余/重复"为由精简。
2. **反幻觉 docstring 是硬要求。** 查询类工具写清楚：只返回上游真实字段、缺失即省略、不推断/不补全；空结果是正常答案；失败返回 error dict 而不是异常。先例：finance-mcp `2d4892f`，本仓库每个 tool docstring 都遵守。
3. **别在描述里承诺没有的能力。** 例如本项目不做 `pubmed_search`，描述里就不能暗示"可以搜文献"；边界见 `boundary-with-siblings.md`。
