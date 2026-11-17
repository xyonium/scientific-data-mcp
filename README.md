# scientific-data-mcp

科研**实体数据** MCP —— 化合物 / 生物活性 / 蛋白序列与结构 / 文献元数据的**免费官方 API 直连**。一个 server，12 个工具，零 key、零额度。

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

全部免 key。唯一可选配置是 `NCBI_API_KEY`（免费申请，把 E-utilities 从 3 req/s 提到 10 req/s；不配也能用）和联系邮箱 `NCBI_EMAIL`。申请步骤与扩展源的 key 入口见 [docs/CREDENTIALS.md](./docs/CREDENTIALS.md)。

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

所有工具只返回上游真实字段：缺字段就是上游没有，不推断、不补全。失败返回 `{"error": ..., "source": ...}`，不会让一次调用炸掉整轮对话。

## 安装

```bash
uv venv --python 3.12 .venv
uv pip install -e . --python .venv/bin/python
# 或
pip install scientific-data-mcp
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
  "NCBI_EMAIL": "you@example.com"
}
```

申请步骤、各源是否有 key、以及 M6 扩展源（Materials Project / openFDA / NOAA / BioGRID / NASA）的入口见 **[docs/CREDENTIALS.md](./docs/CREDENTIALS.md)**。不配 key 时五个源全部可用，只是 PubMed 慢一些。

## Docker

```bash
docker build -t scientific-data-mcp:dev .
docker run --rm -p 8000:8000 scientific-data-mcp:dev --http --host 0.0.0.0
```

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
