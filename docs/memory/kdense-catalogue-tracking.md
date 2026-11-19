# K-Dense 数据源清单追踪

> 2026-11-18。

## 事实

- 上游：`K-Dense-AI/scientific-agent-skills` 的 `skills/database-lookup/SKILL.md`。2026-09-13 立项时抓的是 v1.6（80 库，9 组）；2026-11-18 复核为 **v1.8 / last-reviewed 2026-09-30**，仍是 **80 库、同样 9 组**（天文 5 / 地球 4 / 化学 9 / 材料 2 / 生物 34 / 疾病临床 12 / 专利监管 2 / 经济金融 9 / 社科 3）。
- 所以数据库清单本身稳定；变的是 skill 版本与文档细节。仓库整体从 165 skills 涨到 177 skills，但那是非数据库技能，不在本项目范围。
- 我们只把 `database-lookup` 的库清单当**源池**，没有依赖它的 177 个 skill；经济/金融 9 个归 finance-mcp，专利 2 个归 paper-search，社科 3 个观察。

## 机制

- 快照：`docs/research/kdense-databases.json`（name / reference / category / coverage + 版本）。
- 脚本：`scripts/kdense_sources.py --check`（diff，集合变化 exit 1） / `--update`（刷新快照）。
- Action：`.github/workflows/kdense-sources.yml`，每季度 1/4/7/10 月 1 日 03:00 UTC + 手动；有新增/移除就开 issue（已有 open issue 则评论），并上传 diff artifact。
- 处理新增源的顺序：判定域（本项目 / paper-search / finance-mcp）→ 判断免 key / 免费注册 key / 付费 → 只把值得接的写进 `docs/计划.md` 的 M6 池 → `--update` 刷新快照。

## 边界

清单是"可以考虑的源"，不是"已接的源"。当前已接 21 个 K-Dense 源（含 PubMed 共 22 个工具源），逐源状态以 `docs/research/kdense-coverage.md` 为准；本项目基础 20 工具，Materials Project key 加 1。

## 2026-11-18 兄弟项目归属审计

- finance-mcp（HEAD `36d4230`）：14 个经济/监管/社科源里，真正值得补的只有 **SEC EDGAR**；World Bank 任意指标透传、Treasury Fiscal Data 是低成本增量；BEA/BLS 由 FRED 派生覆盖，Eurostat/WHO/Census/Data Commons 暂缓。
- paper-search：USPTO 官方直连完全未覆盖，但 ODP 需 ID.me 实名 + 个人 key、仅美国、无全文/语义检索；PatentsView 搜索暂停。结论 **暂不新增**，patsnap 继续用；触发条件是 patsnap 失效或需要美国审查文书。
- 交接：`docs/handoff/2026-11-18-kdense-finance-gaps.md`（dockerno1 副本在 `~/finance-mcp/docs/handoff-2026-11-18-kdense-gaps.md`）。
