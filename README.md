# scientific-data-mcp

[![PyPI](https://img.shields.io/pypi/v/scientific-data-mcp.svg)](https://pypi.org/project/scientific-data-mcp/)

科研**实体数据** MCP —— 化合物 / 生物活性 / 蛋白序列与结构 / 文献元数据的**免费官方 API 直连**。一个 server，23 个基础工具（配 Materials Project key 时 24 个；BioGRID key 解锁互作 source，不增工具），零额度。同类输入输出的源合并为一个工具，用 `kind` / `by` 参数切换。

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

二十五个基础源完全免 key（PubChem / ChEMBL / UniProt / RCSB PDB / WHO / STRING / openFDA / ClinicalTrials.gov / AlphaFold DB / Open Targets / Reactome / NCBI Gene / ClinVar / InterPro / QuickGO / HPO / GEO / KEGG / DailyMed / GDC / cBioPortal / GTEx / Ensembl / ChEBI / BindingDB），PubMed / NCBI Gene / ClinVar / GEO 可选 `NCBI_API_KEY` 提速（3→10 req/s）；**Materials Project 和 BioGRID 需要免费 key**：MP 未配时 `material` 不注册；BioGRID 未配时 `protein_interactions(source="biogrid")` 返回明确错误，STRING 仍可用。openFDA 可选 key 只提额度。申请步骤见 [docs/CREDENTIALS.md](./docs/CREDENTIALS.md)。

| 工具 | 源 | 说明 |
|------|----|------|
| `chem_compound` | PubChem | 化合物记录：`identifier` + `id_type`（name/cid/smiles/inchikey）；可选 `properties` 指定 PubChem 属性集（省略为默认全集） |
| `chem_similar_compounds` | PubChem | 结构相似性（POST + ListKey 轮询），返回 CID 列表 |
| `chembl_data` | ChEMBL | `kind="search"`（query/resource）、`"activities"`（chembl_id 或 target_chembl_id）、`"mechanisms"`（chembl_id）；统一列表 envelope |
| `protein_record` | UniProt / RCSB / AlphaFold | `kind="uniprot"` 取条目（可选全序列）；`kind="pdb"` 取结构条目 + 实体摘要；`kind="alphafold"` 取预测模型 |
| `protein_search` | UniProt / RCSB | `kind="uniprot"` 用 UniProt 查询语法；`kind="pdb"` 全文检索；统一 `next_cursor` |
| `protein_map_ids` | UniProt | 官方 ID Mapping（submit → poll） |
| `pubmed_record` | PubMed | pmid / doi → 标题、作者、期刊、年卷期页、摘要、DOI、PMCID |
| `who_data` | WHO GHO | 按指标代码查国家/年份/性别的健康统计（如 `WHOSIS_000001`） |
| `material` | Materials Project（需免费 key） | `by="id"` 单条；`by="formula" / "chemsys" / "elements"` 检索；统一列表 envelope |
| `protein_interactions` | STRING / BioGRID | `source="string"`（免 key，含 combined/evidence scores）或 `"biogrid"`（需 key，含实验系统/PubMed）；`genes` 支持 `BRCA1|BRCA2` |
| `openfda` | openFDA | `endpoint="drug/label" / "drug/event" / "drug/enforcement"` + `query`（field:term）；无匹配是 `count: 0`；可选 key 提额度 |
| `clinical_trials` | ClinicalTrials.gov v2 | 自由文本检索 + `status` 过滤；返回 NCT id/标题/状态/分期/干预/入组/赞助方 + `next_cursor` |
| `opentargets` | Open Targets | `entity="target"` 查靶点→疾病关联；`entity="disease"` 查疾病→靶点关联；score 0-1 |
| `pathways` | Reactome | 按基因/通路名检索通路；默认人类，可传空字符串查所有物种 |
| `gene_record` | NCBI Gene / Ensembl | `kind="ncbi"`：符号或 Gene ID；`kind="ensembl"`：符号或 Ensembl ID + organism taxid；单记录 |
| `clinvar` | ClinVar | 按基因/变异/临床意义检索；返回 VCV、分类、review status、条件、基因、蛋白改变 |
| `protein_annotations` | InterPro / QuickGO | `source="interpro"` 取结构域/家族条目；`source="quickgo"` 取 GO 注释 |
| `phenotypes` | HPO | 按表型短语或 `HP:...` id 检索 Human Phenotype Ontology 术语 |
| `geo_datasets` | GEO (NCBI) | 按基因/疾病检索 GEO DataSets；返回 GSE、标题、摘要、物种、样本数、发布日期 |
| `dailymed` | DailyMed (NLM) | 药品名 → SPL setid、标题、发布日期、版本 |
| `compound_lookup` | ChEBI / KEGG | `source="chebi"`：名称或 `CHEBI:...`；`source="kegg"`：名称或 `C...`；统一列表 envelope；KEGG 学术免费/商用需许可 |
| `bindingdb_ligands` | BindingDB | UniProt 靶点 + nM cutoff → ligand SMILES / 亲和力；免 key，~1 req/s |
| `cancer_studies` | GDC / cBioPortal | `source="gdc"` 查 NCI GDC 项目；`source="cbioportal"` 查 cBioPortal 研究；统一列表 |
| `gene_expression` | GTEx | Ensembl gene id → 各组织 median 表达（TPM） |

所有工具只返回上游真实字段：缺字段就是上游没有，不推断、不补全。失败返回 `{"error": ..., "source": ...}`，不会让一次调用炸掉整轮对话。

如果错误里出现 `"suspect_drift": true` / `"action": "contact_admin"`，表示**上游返回结构与适配器不一致（接口可能漂移）**，不是限流或网络问题：不要用相同参数重试，请告知用户联系管理员更新对应 provider。`rate_limited` / `unavailable` / `auth` / `not_found` 不带这个标记。

## 安装

```bash
pip install scientific-data-mcp
# 或
uvx scientific-data-mcp
# 开发安装
uv venv --python 3.12 .venv
uv pip install -e '.[dev]' --python .venv/bin/python
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
  "MATERIALS_PROJECT_API_KEY": "免费申请；不配则不注册材料工具",
  "BIOGRID_ACCESS_KEY": "免费申请；不配则 protein_interactions 的 biogrid source 不可用",
  "OPENFDA_API_KEY": "可选；只提额度，不配也能用"
}
```

申请步骤、各源是否有 key、以及 M6 扩展源（NOAA / NASA）的入口见 **[docs/CREDENTIALS.md](./docs/CREDENTIALS.md)**。不配任何 key 时 26 个基础源全部可用（25 个免 key；PubMed / Gene / ClinVar / GEO 无 key 时慢一些），MP 工具隐藏、BioGRID source 不可用。

## Docker

```bash
docker build -t scientific-data-mcp:dev .
docker run --rm -p 8000:8000 scientific-data-mcp:dev --http --host 0.0.0.0
```

## PyPI 发布

包名 **`scientific-data-mcp`**，已发布到 [PyPI](https://pypi.org/project/scientific-data-mcp/)。首次发布通过 trusted publishing 完成；之后 push `v*` tag 自动发布。

一次性配置（推荐 trusted publishing，免 API token）：

1. 注册 PyPI 账号并开启 2FA。
2. 打开 https://pypi.org/manage/account/publishing/ ，添加 **pending publisher**：
   - PyPI project name: `scientific-data-mcp`
   - Owner: `xyonium`
   - Repository: `scientific-data-mcp`
   - Workflow name: `publish.yml`
   - Environment: `pypi`
3. 仓库 Settings → Secrets and variables → Actions → Variables 新建 `PYPI_PUBLISH=true`。
4. 之后 push `v*` tag（或手动运行 `publish` workflow）即构建 sdist/wheel 并上传。

工作流在 [.github/workflows/publish.yml](./.github/workflows/publish.yml)：tag 触发时只有在 `PYPI_PUBLISH=true` 才发布，避免未配置时 CI 变红。首次上传会自动创建 PyPI 项目并占用这个名字。

## 数据源清单追踪

[docs/research/kdense-databases.json](./docs/research/kdense-databases.json) 是 [K-Dense scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills) `database-lookup` 的数据库快照（当前 v1.8，80 库，2026-09-30 复核）。

```bash
python scripts/kdense_sources.py --check    # 与上游 diff
python scripts/kdense_sources.py --update   # 刷新快照
```

GitHub Action `kdense-sources` 每季度（1/4/7/10 月 1 日）自动扫描；上游新增或移除数据库时开 issue（已有 open issue 则追加评论）。

80 个库逐个的“已实现 / M6 / 归兄弟项目 / 不做”决定见 [docs/research/kdense-coverage.md](./docs/research/kdense-coverage.md)。

## 开发

```bash
pytest -q                 # hermetic（respx mock），0 egress
ruff check .
python scripts/live_smoke.py   # 真实打 25 个基础上游（Ensembl 不在 smoke；配 key 时 27 个），人工跑
```

- 设计与决策：[`docs/superpowers/specs/`](./docs/superpowers/specs/)
- 实施计划：[`docs/superpowers/plans/`](./docs/superpowers/plans/)
- 工作记忆：[`docs/memory/MEMORY.md`](./docs/memory/MEMORY.md)
- 立项证据：[`docs/research/kimi-sources/`](./docs/research/kimi-sources/)
- 维护指南：[`AGENTS.md`](./AGENTS.md)

## License

MIT
