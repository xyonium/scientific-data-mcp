# Materials Project：key-gated 接入形态

> 2026-11-18，v0.2.0。K-Dense `database-lookup` 的 80 库里，唯一需要注册 key 的当前源。

- 上游：`https://api.materialsproject.org`，鉴权头 `X-API-KEY`，key 在 materialsproject.org 免费账号的 Dashboard → API 生成。
- 环境变量：`MATERIALS_PROJECT_API_KEY`。**没有 key 时 provider 和 2 个工具都不注册**（服务保持 12 工具），不是"注册但永远报错"。先例价值：以后接 BioGRID/openFDA 等 key-gated 源沿用同一形态。
- 工具：`material_get(material_id)`、`material_search(formula|chemsys|elements, limit)`；search 三个选择器必须恰好一个。
- 字段只取 summary 端点：`material_id/formula_pretty/chemsys/elements/band_gap/energy_above_hull/density/is_stable/nsites/theoretical/symmetry`；缺字段省略。
- 限速：`api.materialsproject.org` 固定 1 req/s（MP 明确会对侵略性流量限速/封 IP）。
- 实测约束：MP 的 401/403 会翻成 `auth`，提示检查 key；无 key 时不要试图"静默降级成免费源"——MP 没有匿名面。
