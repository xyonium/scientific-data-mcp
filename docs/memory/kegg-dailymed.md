# KEGG / DailyMed（v0.10.0）

> 2026-11-19。化学批次：KEGG 化合物 + DailyMed 药品标签。

## KEGG

- 工具：`compound_lookup(source="kegg", query, limit)`；名称或 `C\d{5}`。
- API：`https://rest.kegg.jp/find/compound/{name}` → `C01405\tAspirin; ...`；`/get/cpd:{id}` 返回 flat text。
- 解析：`ENTRY`/`NAME`（`;` 分隔）/`FORMULA`/`EXACT_MASS`/`MOL_WEIGHT`/`PATHWAY`（`map04976  Bile secretion`）。
- 名称查询最多取 `limit` 个 ID，再逐个 `get`；限速 0.5s。
- **许可**：KEGG REST 学术免费；商用需要 KEGG 许可（docstring 已写明）。
- 空 find → `count: 0`；缺 `ENTRY` → drift。

## DailyMed

- 工具：`dailymed(query, limit=5)`；`https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json?drug_name=...&pagesize=...`。
- 返回 `{data, metadata.total_elements}`；归一化 setid/title/published_date/spl_version。
- 只做标签元数据搜索，不抓全文；空 `data` → `count: 0`。
- 免 key；0.5s。

## 未接

- **ChEBI**：backend API 从当前网络 301/404/超时，未找到稳定 JSON 入口；暂缓。
- **ZINC**：`zinc15.docking.org/substances.json` 返回 captcha 302，暂缓。
- **Ensembl**：换节点后仍 403/504；**GTEx** 换节点后已 200，留到表达/临床批次。
