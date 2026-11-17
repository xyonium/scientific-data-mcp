# scientific-data-mcp — 维护指南

免费、免 key 的科研**实体数据** MCP：化合物（PubChem）、生物活性（ChEMBL）、蛋白序列/功能（UniProt）、实验结构（RCSB PDB）、文献元数据（PubMed E-utilities）。一个 FastMCP server，12 个工具，零额度、可自托管。

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
python scripts/live_smoke.py   # 真实打 5 个上游，人工跑，不进 CI

.venv/bin/scientific-data-mcp                 # stdio（mcpo 用这个）
.venv/bin/scientific-data-mcp --http --port 8000
docker build -t scientific-data-mcp:dev .
```

本机 uv 的默认缓存目录可能被沙箱挡住；必要时 `export UV_CACHE_DIR=$PWD/.uv-cache UV_PYTHON_INSTALL_DIR=$PWD/.uv-python`。

## 架构纪律

- `providers/<source>.py`：URL 构造、分页、字段归一化。`tools/<domain>.py`：LLM-facing schema、参数校验、错误包装。
- 所有 HTTP 走 `http.PoliteClient`：per-host 限速（见 `config.HOST_DELAYS`）、429/503 与瞬时 5xx（500/502/504）重试、401/403→`AuthError`、404→`NotFound`。
- **工具永不抛异常**：任何失败返回 `{"error": "...", "source": "..."}`；空结果是正常答案（`count: 0`），不是错误。
- **反幻觉**：只返回上游真实字段；缺失字段省略，不推断、不补全；docstring 写明"不补全"。返回体不带时间戳（测试可复现）。
- 返回值 `source_url` 指向官方记录页，便于人工复核。
- 分页：列表返回 `next_cursor`/`next_offset`/`next_start`，最后一页为 `null`。
- 新增源时同步：provider、tool、`runtime.build_service`、`tools/__init__.register_all`、`tests/test_server.py` 的 12 工具断言、README 工具表、`docs/memory/`。

## 发布纪律

- 版本只来自 git tag（hatch-vcs，`pyproject.toml` 里 `dynamic = ["version"]`）。**永不手写 version**。
- `v*` tag 推上去即 v0.1.0；改版本 = 打新 tag，不改文件。
- 细节见 `docs/memory/publishing-hatch-vcs.md`。

## 记忆

`docs/memory/MEMORY.md` 是索引。改动某一域前先读对应笔记：

- 改 PubChem / ChEMBL / UniProt / PDB / PubMed → `kimi-science-sources-verdicts.md`
- 改 HTTP / 重试 / 超时 → `flaky-upstream-apis.md`
- 改 key / 环境变量 / 限速 → `secrets-and-quotas.md`
- 改 docstring / 工具描述 → `tool-description-discipline.md`
- 改边界（PubMed 搜索、全文、RAG） → `boundary-with-siblings.md`
- 改发布 / 版本 → `publishing-hatch-vcs.md`
- 迁移背景 / DSH 形态 → `dsh-migration.md`

## Agent 工具纪律

- 仓库根有 `.codegraph/` 时，先用 MCP `codegraph_explore`（或 shell `codegraph query "<符号>"`）再 grep/read。注意 codegraph 0.9.9 没有 `explore` 子命令。
- 取网页/搜索走 firecrawl（`firecrawl_scrape` / `firecrawl_search`），不用原生 WebFetch。
