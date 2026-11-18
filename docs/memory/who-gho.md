# WHO GHO 接入

> 2026-11-18，v0.3.0。唯一新增的“健康统计”源，免 key。

- Base：`https://ghoapi.azureedge.net/api`，OData v4；观测端点 `/{IndicatorCode}`，返回 `{"value": [...]}`。
- 工具 `who_data(indicator, country?, year?, sex?, limit?)`：**必须给指标代码**（如 `WHOSIS_000001` 出生预期寿命）；不做指标目录搜索，因为 `/Indicator` 目录端点在本网络持续 504（大响应 + Azure CDN），实现成“搜索”只会给用户一个常坏的工具。
- 过滤语法（实测）：`$filter=SpatialDim eq 'CHN' and TimeDim eq 2022`，`$top=N`。字段：`SpatialDim`（ISO3/地区/GLOBAL）、`TimeDim`（年）、`Dim1`（性别，`SEX_FMLE`/`SEX_MLE`/`SEX_BTSX`）、`NumericValue`、`Value`（带 CI 的文本）、`Low`/`High`。
- 限速：0.5s；官方建议 1–2 req/s。
- 漂移锚点：200 响应必须有 `value` 列表；缺失 → `UpstreamDrift`。
- 边界：只做观测查询，不做指标目录、不做图表、不做国家元数据；健康统计归本项目（不塞给 finance-mcp）。
