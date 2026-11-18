# 与兄弟项目的边界

> 迁移自 paper-search `MEMORY.md` / pubmed verdict 的边界段。

一句话：**paper-search 管"找论文/读论文/入 RAG"，本项目管"查实体数据"。**

| 用户意图 | 去哪里 |
|----------|--------|
| 这个化合物的性质/靶点 | 本项目 `chem_compound` / `chembl_*` |
| 这个蛋白的序列/结构 | 本项目 `protein_record`（kind=uniprot/pdb） |
| 给了 PMID/DOI 要结构化记录 | 本项目 `pubmed_record`（不下载全文） |
| 关于 X 的论文 | paper-search |
| 要全文 / 入 Knowledge RAG | paper-search |
| 金融行情/宏观 | finance-mcp |

实现层约束：
- 本项目**不提供** `pubmed_search`、全文下载、RAG 入库。
- 不实现 K-Dense 清单里的经济/金融组（归 finance-mcp）和专利监管组（归 paper-search）。
- 参考源池：`K-Dense-AI/scientific-agent-skills` 的 80 库清单（见 `docs/计划.md`），M6 再评估扩展。
