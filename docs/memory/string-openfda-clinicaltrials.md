# STRING / openFDA / ClinicalTrials.gov（v0.6.0）

> 2026-11-19。三个基础免 key 源；BioGRID 与 STRING 合并为一个工具，不再新增工具数。

## 工具面

| 工具 | source/endpoint | 说明 |
|---|---|---|
| `protein_interactions` | `source="string"`（默认）/ `"biogrid"` | 同一列表 envelope；STRING 免 key，BioGRID 需 `BIOGRID_ACCESS_KEY` |
| `openfda` | `endpoint="drug/label" / "drug/event" / "drug/enforcement"` | 原始 upstream records，默认 3 条（label 单条可达 ~10 KB） |
| `clinical_trials` | ClinicalTrials.gov v2 | 归一化为 NCT/标题/状态/分期/干预/入组/赞助方，带 `next_cursor` |

BioGRID key 不再改变工具数量：provider 缺席时 `protein_interactions` 仍注册（STRING 可用），`source="biogrid"` 返回明确错误。

## STRING

- Endpoint：`https://string-db.org/api/json/interaction_partners`；参数 `identifiers`（多基因用 `\r` 连接）、`species`（taxId）、`limit`、`required_score`（0-1000）、`caller_identity`。
- 返回 **list**；score 是 0-1 的 combined score，evidence channels 为 n/f/p/a/e/d/t score。空 list 正常。
- 无分页参数；用 `limit` 控制。非 list 200 → drift。

## openFDA

- Base `https://api.fda.gov`；可选 key `OPENFDA_API_KEY` 以 query 参数 `api_key` 传递。
- **无匹配是 HTTP 404 + `error.code="NOT_FOUND"`**，必须当 `count: 0`，不能当 `not_found` 错误；用 `PoliteClient.get_response(..., allow_status=(404,))` 特判。
- 有 key 240/min + 120,000/day；无 key 240/min + 1,000/day（per IP）。
- 记录是原始 JSON，label 很大；工具 `limit` 上限 10、默认 3。
- 200 无 `results` → drift；其他 404 → `NotFound`。

## ClinicalTrials.gov v2

- Endpoint：`https://clinicaltrials.gov/api/v2/studies`；参数 `query.term`、`pageSize`、`countTotal=true`、`filter.overallStatus`、`pageToken`。
- 返回 `studies` / `totalCount` / `nextPageToken`；缺 `studies` → drift；空 list 正常。
- 归一化只取 protocolSection 的常用字段；不补全缺失字段。

## 验证

- 127 tests（含 404 NOT_FOUND、非 list drift、分页 cursor）。
- Keyed live smoke 19/19（base 16 + BioGRID 1 + MP 2）。
