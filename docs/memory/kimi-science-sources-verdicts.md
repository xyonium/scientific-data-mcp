# kimi 五个科研源的裁决与端点

> 迁移自 finance-mcp `~/.claude/projects/-home-eli-finance-mcp/memory` + `docs/research/kimi-sources/*.verdict.md`（2026-09-13，R15–R17）。原文完整保留在 `docs/research/kimi-sources/`。

## 结论

kimi datasource 里与科研相关的源**恰好是这五个**：`pubchem`、`chembl`、`uniprot`、`pdb`、`pubmed`。五个全部被判"摘"——它们都是官方免 key API 的 1:1 薄包装，零数据增值：

| 源 | 官方上游 | kimi 包装的本质 |
|----|----------|----------------|
| pubchem | `pubchem.ncbi.nlm.nih.gov/rest/pug` | 4/4 API 直转；SMILES 走 POST form、相似性 ListKey 轮询是官方文档写法 |
| chembl | `www.ebi.ac.uk/chembl/api/data` | 4/4 API 直转，且官方覆盖面是 kimi 的严格超集 |
| uniprot | `rest.uniprot.org` | 4/4 API 直转；`next_cursor` 只是官方 Link header 的搬运 |
| pdb | `data.rcsb.org` + `search.rcsb.org` | 4/4 API 直转；kimi 的检索面反而更窄 |
| pubmed | `eutils.ncbi.nlm.nih.gov` | E-utilities esearch+efetch；paper-search 早已直连 |

kimi 侧**不需要改**（或至多小改）：它的源目录只是上游镜像，去掉这五个不损失能力；本仓库就是这些能力的免费落点。**不要**反向让本项目去调 kimi——那会把免费直连变成收费中转。

## 实测端点（2026-09-13，零鉴权头）

- PubChem：`GET /compound/name/aspirin/cids/JSON` → 200；`POST /compound/similarity/smiles/JSON` → 202 + `Waiting.ListKey`，再 `GET /compound/listkey/{key}/cids/JSON` → 200。
- ChEMBL：`GET /molecule/CHEMBL25.json` → 200；`GET /activity.json?molecule_chembl_id=CHEMBL941` → 200。
- UniProt：`GET /uniprotkb/P05067.json` → 200；`POST /idmapping/run` → `{"jobId":...}`，status → 303/200。
- RCSB：`GET /rest/v1/core/entry/4HHB` → 200；`POST search.rcsb.org/rcsbsearch/v2/query` → 200。
- PubMed：`esearch.fcgi?db=pubmed` → 200；`efetch.fcgi?db=pubmed&retmode=xml` → 200。

## 实施时修正的坑（2026-11-17）

1. **ChEMBL 检索端点**：verdict 里写的 `?search_parameters__q=` 实测会被忽略/极慢（20s 超时），**必须用官方的 `/<resource>/search.json?q=`**。用错参数会拿到未过滤的行。
2. **PubMed DOI 解析**：PMC ID converter（`www.ncbi.nlm.nih.gov/.../idconv`）在本网络 20s 超时；改用**同 host 的 E-utilities esearch** `term={doi}[doi]`，稳定且无额外依赖。
3. **PubMed ArticleIdList**：`PubmedArticle/PubmedData/ArticleIdList` 才是本文的 id；`.//ArticleIdList` 会匹配到参考文献里的 id（DOI/PMCID 会取错）。
4. **RCSB entity id 是 1-based 实体号**，不是 chain id；chain 在 `auth_asym_ids`。
5. **ChEMBL 的 MoA 挂在盐形式上**：`CHEMBL941`（imatinib 游离碱）机制为空是正常答案，`CHEMBL1642`（甲磺酸盐）才有。
