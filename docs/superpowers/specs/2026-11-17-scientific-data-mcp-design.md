# scientific-data-mcp 设计

> 日期：2026-11-17 ｜ 状态：已批准 ｜ 前身：`eli@dockerno1:~/scientific-data-mcp`（仅 README + 计划，无代码）

## 意图

kimi datasource 把一批**本来就免 key 的官方科研 API**（PubChem / ChEMBL / UniProt / PDB / PubMed）包装成收费额度源。finance-mcp 在 2026-09-13 的 R15–R17 去重中把这批源摘除，每源都有 live 实测的免费端点证据（`docs/research/kimi-sources/*.verdict.md`）。**本项目是这批源的免费直连落点**：一个 MCP server，让 agent 查科研实体数据（化合物、生物活性、蛋白序列、结构、文献元数据），零 key、零额度、可自托管。

边界：`paper-search` 管"找论文/读论文/入 RAG"，本项目管"查实体数据"；本项目只做**实体级** PubMed 记录查询（pmid/doi → 结构化记录），不做跨库文献搜索。金融/宏观归 finance-mcp，专利归 paper-search。

## 目标

- M1 骨架：可安装、可测试、可容器化、CI 绿。
- M2 化学：PubChem（化合物/性质/同义名/相似性）+ ChEMBL（活性/机制/检索）。
- M3 蛋白：UniProt（条目/检索/ID 映射）+ RCSB PDB（条目/结构搜索）。
- M4 文献元数据：PubMed E-utilities（pmid/doi → 结构化记录）。
- 发布 v0.1.0：GitHub public + PyPI 名字保留 + docker 镜像可构建。

**非目标**：K-Dense 80 库清单里的 M6 扩展源、材料/天文/地球域、Open Targets/gnomAD 等 POST-only 源、任何需要注册 key 的源、文献全文下载、RAG 入库、kimi/cliproxy 转发链路。

## 约束（来自前身与兄弟项目）

- Python ≥3.10，`mcp[cli]>=1.27,<2`（FastMCP 1.x API；2.x 移除了 `mcp.server.fastmcp`）。
- **全部源免 key**；唯一可选 key 是 `NCBI_API_KEY`（免费申请，3 req/s → 10 req/s），无 key 静默降速，不报错。
- 反幻觉纪律：工具 docstring 与返回体只陈述上游真实字段；缺失字段省略，不推断、不补全；错误返回 `{"error": ..., "source": ...}`，**工具永不抛异常**。
- 限速与重试（上游实测/文档；瞬时 5xx 也重试）：PubChem ≤5 req/s；ChEMBL "moderate"（≥0.5s 间隔）；UniProt 合理；RCSB 合理；NCBI 3/s（无 key）/10/s（有 key）。
- 境外学术 API 在同网络下会间歇 SSL EOF/挂起（paper-search 记忆）：所有请求必须带退避重试；记录到 `docs/memory/`。
- 发布：hatch-vcs，version 只来自 git tag；不再手写 `version = "..."`（finance-mcp 2026-09-11 duplicate 事故）。

## 方案

**选定：单 FastMCP server + per-source provider + per-domain tool 路由**（finance-mcp 模式）。

每源一个 `providers/<source>.py`，封装 URL 构造、分页、字段归一化；每域一个 `tools/<domain>.py`，负责工具 schema、跨源编排、错误包装。HTTP 统一走 `http.PoliteClient`（per-host 限速、429/503 Retry-After、指数退避），错误走 `errors.py` 分类。

备选（已否）：
- 每源一个 MCP server：OpenWebUI 出现 5 组 namespace，tooltip/部署碎片化，跨源编排（化合物→ChEMBL cross-ref）要多跳。
- 单工具 `query(source, resource, params)` 泛代理：无字段 schema，模型最易幻觉参数；归一化责任推给调用方。

## 架构

```
src/scientific_data_mcp/
  __main__.py        # CLI: stdio 默认 / --http
  server.py          # FastMCP 实例、service 组装、tool 注册
  config.py          # Settings（env 覆盖 base_url、NCBI key、超时、UA）
  http.py            # PoliteClient：per-host 限速 + 重试 + 错误翻译
  errors.py          # ProviderError 分类 + tool_error()
  providers/
    base.py          # Provider 协议（name/base_url/available）
    pubchem.py       # PUG-REST（含 similarity POST + ListKey 轮询）
    chembl.py        # EBI REST（molecule/target/assay/activity/mechanism）
    uniprot.py       # UniProtKB + search(Link cursor) + idmapping
    rcsb.py          # data.rcsb.org + search.rcsb.org
    pubmed.py        # E-utilities efetch + PMC ID converter
  tools/
    chemistry.py     # 6 个 chem_* 工具
    protein.py       # 5 个 protein_* 工具
    literature.py    # 1 个 pubmed_record 工具
tests/               # respx hermetic；tests/live 标记 live 不进 CI
scripts/live_smoke.py
```

**返回契约**

单条记录：
```json
{"source": "pubchem", "source_url": "https://…", "record": {…}}
```
列表：
```json
{"source": "chembl", "count": 20, "items": [...], "next_offset": 20}
```
错误：`{"error": "not_found: CID 999999999", "source": "pubchem", "hint": "..."}`。

`source_url` 是官方记录页/检索页（便于人工点击复核）；不返回本地时间戳（测试可复现）。

**工具面（v0.1.0，12 个）**

化学：
1. `chem_compound(identifier, id_type="name"|"cid"|"smiles"|"inchikey")` — PubChem 化合物主记录（CID、分子式、分子量、IUPAC、SMILES、InChIKey、XLogP、TPSA、前 20 个同义名）。
2. `chem_compound_properties(cid, properties=None)` — 指定属性集（默认白名单）。
3. `chem_similar_compounds(smiles, threshold=90, max_records=20)` — 相似性（POST → ListKey 轮询）。
4. `chembl_search(resource="molecule"|"target"|"assay", query, limit=10, offset=0)`。
5. `chembl_bioactivity(chembl_id=None, target_chembl_id=None, limit=20, offset=0)` — 二选一。
6. `chembl_mechanisms(chembl_id)` — 药物作用机制（返回 target + action）。

蛋白：
7. `protein_entry(accession, include_sequence=False)` — UniProt 归一化条目（名、基因、物种、功能、关键词、序列长度/质量、PDB 交叉引用）。
8. `protein_search(query, size=10, cursor=None)` — UniProtKB 检索，返回 `next_cursor`。
9. `protein_map_ids(from_db, to_db, ids)` — UniProt ID mapping（submit → poll，上限 30s）。
10. `protein_structure(pdb_id)` — RCSB 条目 + 聚合物实体摘要。
11. `protein_structure_search(query, rows=10, start=0)` — RCSB 全文检索。

文献：
12. `pubmed_record(pmid=None, doi=None)` — 结构化记录（标题、作者、期刊、年、卷期页、摘要、DOI/PMCID）。

## DSH 维护形态

- **`AGENTS.md` 是唯一常驻指令**（DSH 自动加载 `AGENTS.md`/`CLAUDE.md`；本项目只保留 `AGENTS.md`）。内容：定位与边界、目录结构、命令、代码纪律（反幻觉、永不抛异常、限速）、发布纪律、记忆索引指针。
- **记忆在 `docs/memory/`**：`MEMORY.md` 索引 + 每主题一笔记（Claude Code 的 memory 目录无法被 DSH 自动加载，故显式落库并在 AGENTS.md 里要求"动某域前先读对应笔记"）。
- 不再有 `.claude/`；不依赖任何 Claude Code 专有机制。git hooks/CI 全部平台无关。
- `docs/research/kimi-sources/*.verdict.md` 是立项证据链，原样保留；`docs/计划.md` 转入历史，里程碑状态以本 spec 与 README 为准。

## 迁移记忆清单

| 来源 | 笔记 | 去处 |
|---|---|---|
| finance-mcp `MEMORY.md` | kimi 5 源裁决 + 端点 | `docs/memory/kimi-science-sources-verdicts.md`（+ verdict 原文） |
| finance-mcp | hatch-vcs 发布/duplicate 事故 | `docs/memory/publishing-hatch-vcs.md` |
| finance-mcp | .env 与配额纪律（无 dotenv、key 只按需探测） | `docs/memory/secrets-and-quotas.md` |
| paper-search | 境外学术 API SSL EOF / 退避重试 | `docs/memory/flaky-upstream-apis.md` |
| paper-search | tool description 源列表给人看、不可删 | `docs/memory/tool-description-discipline.md` |
| paper-search | 与 paper-search 的边界 | `docs/memory/boundary-with-siblings.md` |
| 全局 CLAUDE.md | codegraph 优先、firecrawl 取网页 | 写进 `AGENTS.md` 的 Agent 工具纪律 |

## 验收

- `pytest` 全绿（hermetic，0 egress）；`ruff check` 干净。
- `scripts/live_smoke.py` 对 5 源各 1 次真实调用成功（人工跑，不进 CI）。
- `scientific-data-mcp` stdio 能起、`--http` 能起、`docker build` 成功。
- GitHub `xyonium/scientific-data-mcp` public，v0.1.0 tag；codegraph 索引可用（`codegraph explore` 能答工具位置）。
