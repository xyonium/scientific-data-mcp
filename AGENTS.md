# scientific-data-mcp — 维护指南

科研**实体数据** MCP：化合物（PubChem）、生物活性（ChEMBL）、蛋白序列/功能（UniProt）、实验结构（RCSB PDB）、文献元数据（PubMed E-utilities），以及材料/互作数据（Materials Project、BioGRID，需免费 key）、互作/药品/临床/通路/疾病关联/基因/变异/注释/表型/数据集/化合物（STRING、openFDA、ClinicalTrials.gov、AlphaFold DB、Open Targets、Reactome、NCBI Gene、ClinVar、InterPro、QuickGO、HPO、GEO、KEGG、DailyMed，基础免 key）。一个 FastMCP server：20 个基础工具（配 MP key 时 21 个）；BioGRID key 解锁 `protein_interactions` 的 biogrid source，不增工具。同类输入输出的源合并为一个工具（`kind`/`by` 参数切换）。

本项目由 **DSH 维护**（2026-11-17 从 Claude Code 项目迁移）。`AGENTS.md` 是唯一常驻指令；`docs/memory/` 是本项目的工作记忆，动手前先读 `docs/memory/MEMORY.md`。

## 定位与边界

| 项目 | 管什么 | 不管 |
|------|--------|------|
| **scientific-data-mcp**（本仓库） | 科研实体数据：化合物 / 活性 / 蛋白 / 结构 / 文献元数据 | 跨库文献检索、全文下载、RAG 入库 |
| `paper-search` | 找论文 / 读论文 / 入 OpenWebUI Knowledge | 实体数据 |
| `finance-mcp` | 金融 / 宏观行情 | 科研 |

PubMed 只做**实体级记录查询**（pmid/doi → 一条结构化记录），不做 `pubmed_search` —— 文献搜索归 paper-search。

## 命令

```bash
uv venv --python 3.12 .venv
uv pip install -e '.[dev]' --python .venv/bin/python

pytest -q                 # hermetic，0 egress
ruff check .
python scripts/live_smoke.py   # 真实打 20 个基础上游（配 key 时 22 个），人工跑，不进 CI

.venv/bin/scientific-data-mcp                 # stdio（mcpo 用这个）
.venv/bin/scientific-data-mcp --http --port 8000
docker build -t scientific-data-mcp:dev .
```

本机 uv 的默认缓存目录可能被沙箱挡住；必要时 `export UV_CACHE_DIR=$PWD/.uv-cache UV_PYTHON_INSTALL_DIR=$PWD/.uv-python`。

## 架构纪律

- `providers/<source>.py`：URL 构造、分页、字段归一化。`tools/<domain>.py`：LLM-facing schema、参数校验、错误包装。
- 所有 HTTP 走 `http.PoliteClient`：per-host 限速（见 `config.HOST_DELAYS`）、429/503 与瞬时 5xx（500/502/504）重试、401/403→`AuthError`、404→`NotFound`。**创建服务端任务的 POST（PubChem 相似性、UniProt idmapping run）不自动重试**，只重试其后的轮询 GET。
- 工具用 `guarded_tool(...)` 注册：最外层兜底任何 `Exception`，保证 never-raise；`CancelledError` 不捕。
- **工具永不抛异常**：任何失败返回 `{"error": "...", "source": "..."}`；空结果是正常答案（`count: 0`），不是错误。
- **漂移信号**：非连接/限流类失败（400/405/406/422、非 JSON 200、缺关键字段、解析异常）抛 `UpstreamDrift`，工具返回 `suspect_drift: true` + `action: contact_admin` + 提示联系管理员；限流/网络/5xx 不带该标记。
- **反幻觉**：只返回上游真实字段；缺失字段省略，不推断、不补全；docstring 写明"不补全"。返回体不带时间戳（测试可复现）。
- 返回值 `source_url` 指向官方记录页，便于人工复核。
- 分页：列表返回 `next_cursor`/`next_offset`/`next_start`，最后一页为 `null`。
- 新增源时同步：provider、tool、`runtime.build_service`、`tools/__init__.register_all`、`tests/test_server.py` 的基础 20 工具断言（+ 有 key 时的工具面）、README 工具表、`docs/memory/`。
- **key-gated 源只在 key 存在时注册 provider**（Materials Project 先例）：MP 没有 key 时 `material` 不注册；BioGRID 没有 key 时 provider 缺席，但共享的 `protein_interactions` 仍注册（STRING 可用），`source="biogrid"` 返回明确错误。
- 数据源池追踪：`docs/research/kdense-databases.json` + `scripts/kdense_sources.py`；季度 Action 有变化会开 issue，评估后 `--update` 刷新快照。逐源决定见 `docs/research/kdense-coverage.md`（80 行：已实现 / M6 / 兄弟项目 / 不做）。

## 发布纪律

- 版本只来自 git tag（hatch-vcs，`pyproject.toml` 里 `dynamic = ["version"]`）。**永不手写 version**。
- `v*` tag 推上去即发布对应版本；改版本 = 打新 tag，不改文件。
- 细节见 `docs/memory/publishing-hatch-vcs.md`。

## 记忆

`docs/memory/MEMORY.md` 是索引。改动某一域前先读对应笔记：

- 改 PubChem / ChEMBL / UniProt / PDB / PubMed → `kimi-science-sources-verdicts.md`
- 改 HTTP / 重试 / 超时 → `flaky-upstream-apis.md`
- 改 key / 环境变量 / 限速 / 申请步骤 → `secrets-and-quotas.md` + `docs/CREDENTIALS.md`
- 改 Materials Project / key-gated 源 → `materials-project-key-gate.md`
- 改 WHO GHO → `who-gho.md`
- 改错误分类 / 漂移信号 → `upstream-drift-signal.md`
- 改 K-Dense 快照 / 季度扫描 → `kdense-catalogue-tracking.md`
- 改工具面 / 合并规则 → `tool-surface-v0.4.md`
- 改 PyPI 发布 / 包名 → `publishing-hatch-vcs.md` + README「PyPI 发布」
- 改 docstring / 工具描述 → `tool-description-discipline.md`
- 改边界（PubMed 搜索、全文、RAG） → `boundary-with-siblings.md`
- 改 BioGRID / STRING / openFDA / ClinicalTrials → `string-openfda-clinicaltrials.md`
- 改 AlphaFold / Open Targets / Reactome → `biology-sources.md`
- 改 NCBI Gene / ClinVar / InterPro / QuickGO → `genomics-annotations.md`
- 改 HPO / GEO → `hpo-geo.md`
- 改 KEGG / DailyMed → `kegg-dailymed.md`
- 改发布 / 版本 → `publishing-hatch-vcs.md`
- 迁移背景 / DSH 形态 → `dsh-migration.md`

## Agent 工具纪律

- 仓库根有 `.codegraph/` 时，先用 MCP `codegraph_explore`（或 shell `codegraph query "<符号>"`）再 grep/read。注意 codegraph 0.9.9 没有 `explore` 子命令。
- 取网页/搜索走 firecrawl（`firecrawl_scrape` / `firecrawl_search`），不用原生 WebFetch。
