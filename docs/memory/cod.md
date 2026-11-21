# COD（v0.17.0）

> 2026-11-21。Crystallography Open Database；实验晶体结构，补 MP 的 DFT 数据。

## 工具

- `cod_crystals(cod_id, formula, elements, text, limit=10)`；四个过滤条件必须**恰好一个**。
- 查询 `GET {base}/result?{filter}&format=json`；返回 list；归一化 cod_id/formula/chemname/mineral/title/authors/journal/year/doi/space_group/space_group_number/method/cell。
- `elements` 逗号/空格；`formula` 自动在数字+元素之间补空格（`Fe2O3` → `Fe2 O3`）。

## 主机与 fallback

- 主机顺序：`www.crystallography.net/cod` → `cod.psdi.ac.uk` → `qiserver.ugr.es/cod`。
- 主站间歇性 TCP/TLS 超时（2026-11-21 实测：先 80/443 超时，后 200 2.56s）；不能永久拉黑。
- 每次调用最多试 **2 个 host**，每个 host **1 次请求**，`retry=False`：
  - 主站 timeout 4s；镜像 8s；
  - 主站失败冷却 10min；镜像失败 10min；429/403 冷却 60min；
  - 成功 host 缓存 10min，主站恢复后自动回主站；
  - 失败不重试、不换 UA/IP。
- 返回 `source_url` 实际 host + `via_mirror`；镜像数据可能滞后。
- COD 数据 public domain / CC0；限速 1 req/s。

## 验证

- 242 tests；主站 live 200；单测覆盖 timeout→UK、403→UK、全失败 unavailable。
