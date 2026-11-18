# 上游漂移信号（suspect_drift）

> 2026-11-18，v0.3.0。目的：把“接口变了”与“网络/限流/没查到”分开，让模型别再盲目重试。

## 分类

| 情况 | 异常 | 工具返回 |
|---|---|---|
| 网络错误、超时、429、500/502/503/504（重试后） | `UpstreamError` / `RateLimited` | `kind: unavailable / rate_limited`，**无** `suspect_drift` |
| 400/405/406/422（请求契约不再被接受） | `UpstreamDrift` | `suspect_drift: true` + `action: contact_admin` |
| 200 但不是 JSON（API 返回 HTML/空页） | `UpstreamDrift` | 同上 |
| 200 JSON 缺关键字段（`PropertyTable`/`results`/`data`/`value`…） | provider 里显式 `UpstreamDrift` | 同上 |
| 解析异常（XML ParseError、AttributeError/TypeError 逃出 adapter） | `UpstreamDrift` / guard 兜底 | 同上 |
| 404、找不到实体、空列表 | `NotFound` / 正常空结果 | **不是**漂移 |

`tool_error(..., suspect_drift=True)` 会加：
```json
{"error": "...", "source": "pubchem", "hint": "上游返回与适配器预期不一致…请告知用户联系管理员…", "suspect_drift": true, "action": "contact_admin"}
```

## 纪律

- 只有“同一请求重试也不会好、且不是用户输入错误”的失败才标漂移。
- 401/403 是 key 问题（`auth`），不是漂移；404 是标识符/资源不存在，不是漂移；429/5xx 是暂时性，不是漂移。
- 新增 provider 时，对每个 200 响应检查至少一个**结构性锚点**（顶层 key / 根标签），缺失就 `raise UpstreamDrift(...)`；解析代码里的 `KeyError/TypeError` 不要吞。
- `guarded_tool` 对逃出的 `Exception` 也标漂移：这通常意味着 payload 形状变了或 adapter 有 bug，管理员需要看。
- MCP `instructions` 已写明：看到 `suspect_drift` 不要重试，告诉用户联系管理员并说明是哪个 source。
