# scientific-data-mcp

科研**实体数据** MCP —— 化合物 / 生物活性 / 蛋白序列与结构 / 文献元数据的**免费官方 API 直连**。一个 server，13 个基础工具（配 Materials Project key 时 15 个），零额度。

> 与 [paper-search](https://github.com/xyonium/paper-search)（文献检索 + RAG）、[finance-mcp](https://github.com/xyonium/finance-mcp)（金融/宏观）互补，不做重复。

## 定位

| 项目 | 管什么 | 不管 |
|------|--------|------|
| [finance-mcp](https://github.com/xyonium/finance-mcp) | 金融/宏观行情 | 科研 |
| [paper-search](https://github.com/xyonium/paper-search) | 学术**文献**检索 + RAG 入 OpenWebUI | 实体数据 |
| **scientific-data-mcp**（本项目） | 科研**实体数据**：化合物、活性、蛋白、结构、文献元数据 | 跨库文献检索、全文下载、RAG |

**边界一句话**：paper-search 管"找论文/读论文/入 RAG"，本项目管"查实体数据"。PubMed 只做 pmid/doi → 结构化记录，不做 `pubmed_search`。

## 为什么

kimi datasource 把一批本来就免 key 的官方科研 API（PubChem / ChEMBL / UniProt / PDB / PubMed）包装成收费额度源。finance-mcp 在 2026-09-13 的去重中把这批源摘除，每源都有 live 实测的免费端点证据（见 [`docs/research/kimi-sources/`](./docs/research/kimi-sources/)）。本项目是这批源的免费直连落点。

## 源与工具

五个基础源免 key（PubChem / ChEMBL / UniProt / RCSB PDB / WHO GHO）；PubMed 可选 `NCBI_API_KEY` 提速（3→10 req/s）；**Materials Project 需要免费 key**，未配置时其 2 个工具不会注册。申请步骤见 [docs/CREDENTIALS.md](./docs/CREDENTIALS.md)。

| 域 | 源 | 工具 |
|----|----|------|
| 化学 | **PubChem**（PUG-REST） | `chem_compound` — 化合物主记录（CID、分子式、分子量、IUPAC、SMILES、InChIKey、XLogP、TPSA、H 键、同义名） |
| 化学 | PubChem | `chem_compound_properties` — 指定属性集 |
| 化学 | PubChem | `chem_similar_compounds` — 结构相似性（POST + ListKey 轮询） |
| 化学 | **ChEMBL**（EBI REST） | `chembl_search` — molecule / target / assay 全文检索 |
| 化学 | ChEMBL | `chembl_bioactivity` — 按分子或靶点的活性测量（IC50/Ki/…、pChEMBL） |
| 化学 | ChEMBL | `chembl_mechanisms` — 作用机制（MoA） |
| 蛋白 | **UniProt**（rest.uniprot.org） | `protein_entry` — 归一化条目（功能、基因、物种、关键词、PDB 交叉引用、可选全序列） |
| 蛋白 | UniProt | `protein_search` — UniProtKB 检索，cursor 分页 |
| 蛋白 | UniProt | `protein_map_ids` — 官方 ID Mapping（submit → poll） |
| 结构 | **RCSB PDB**（Data + Search API） | `protein_structure` — 条目 + 聚合物实体摘要 |
| 结构 | RCSB PDB | `protein_structure_search` — 全文检索 PDB 条目 |
| 文献 | **PubMed**（E-utilities） | `pubmed_record` — pmid / doi → 标题、作者、期刊、年卷期页、摘要、DOI、PMCID |
| 材料 | **Materials Project**（需免费 key） | `material_get` — 单个材料摘要（带隙、energy above hull、密度、对称性、稳定性） |
| 材料 | Materials Project | `material_search` — 按 formula / chemsys / elements 检索 |
| 健康 | **WHO GHO**（OData） | `who_data` — 按指标代码查国家/年份/性别的健康统计（如 `WHOSIS_000001` 出生预期寿命） |

所有工具只返回上游真实字段：缺字段就是上游没有，不推断、不补全。失败返回 `{"error": ..., "source": ...}`，不会让一次调用炸掉整轮对话。

如果错误里出现 `"suspect_drift": true` / `"action": "contact_admin"`，表示**上游返回结构与适配器不一致（接口可能漂移）**，不是限流或网络问题：不要用相同参数重试，请告知用户联系管理员更新对应 provider。`rate_limited` / `unavailable` / `auth` / `not_found` 不带这个标记。

## 安装

```bash
uv venv --python 3.12 .venv
uv pip install -e . --python .venv/bin/python
# 或直接从仓库装（PyPI 尚未发布）
uvx --from git+https://github.com/xyonium/scientific-data-mcp scientific-data-mcp
```

## 运行

stdio（mcpo / 本地 MCP 客户端）：

```bash
scientific-data-mcp
```

Streamable HTTP：

```bash
scientific-data-mcp --http --host 0.0.0.0 --port 8000
```

mcpo 配置示例（`config.json`）：

```json
{
  "mcpServers": {
    "scientific-data": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/xyonium/scientific-data-mcp", "scientific-data-mcp"],
      "env": {}
    }
  }
}
```

### 可选 key（不是必需）

```json
"env": {
  "NCBI_API_KEY": "免费申请，PubMed 限速 3 → 10 req/s",
  "NCBI_EMAIL": "you@example.com",
  "MATERIALS_PROJECT_API_KEY": "免费申请；不配则不注册材料工具"
}
```

申请步骤、各源是否有 key、以及 M6 扩展源（openFDA / NOAA / BioGRID / NASA）的入口见 **[docs/CREDENTIALS.md](./docs/CREDENTIALS.md)**。不配任何 key 时五个免 key 源全部可用，只是 PubMed 慢一些、材料工具隐藏。

## Docker

```bash
docker build -t scientific-data-mcp:dev .
docker run --rm -p 8000:8000 scientific-data-mcp:dev --http --host 0.0.0.0
```

## 数据源清单追踪

[docs/research/kdense-databases.json](./docs/research/kdense-databases.json) 是 [K-Dense scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills) `database-lookup` 的数据库快照（当前 v1.8，80 库，2026-09-30 复核）。

```bash
python scripts/kdense_sources.py --check    # 与上游 diff
python scripts/kdense_sources.py --update   # 刷新快照
```

GitHub Action `kdense-sources` 每季度（1/4/7/10 月 1 日）自动扫描；上游新增或移除数据库时开 issue（已有 open issue 则追加评论）。

## 开发

```bash
pytest -q                 # hermetic（respx mock），0 egress
ruff check .
python scripts/live_smoke.py   # 真实打 5 个上游，人工跑
```

- 设计与决策：[`docs/superpowers/specs/`](./docs/superpowers/specs/)
- 实施计划：[`docs/superpowers/plans/`](./docs/superpowers/plans/)
- 工作记忆：[`docs/memory/MEMORY.md`](./docs/memory/MEMORY.md)
- 立项证据：[`docs/research/kimi-sources/`](./docs/research/kimi-sources/)
- 维护指南：[`AGENTS.md`](./AGENTS.md)

## License

MIT
