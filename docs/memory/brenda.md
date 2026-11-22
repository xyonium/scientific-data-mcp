# BRENDA（v0.18.0，key-gated）

> 2026-11-22。酶动力学/底物/抑制剂/工程突变；免费注册，但只有 SOAP。

## 配置

- `BRENDA_EMAIL` + `BRENDA_PASSWORD`（本机 `.env`，不提交）。
- 程序本地做 `sha256(password).hexdigest()`，SOAP 参数是 email + hash；不保存明文。
- 没有这两个变量时 `brenda` provider/tool 不注册。
- WSDL：`https://www.brenda-enzymes.org/soap/brenda_zeep.wsdl`；endpoint：`https://www.brenda-enzymes.org/soap/brenda_server.php`。
- 用 `zeep`（同步）在 `asyncio.to_thread` 里跑；WSDL 只取一次；1 req/s；**不自动重试**。

## 工具

`brenda(enzyme, kind="km", organism="", limit=20)`，`enzyme` 必须是完整 EC（`1.1.1.1`）。

| kind | SOAP method |
|---|---|
| km | getKmValue |
| kcat | getTurnoverNumber |
| ki | getKiValue |
| kcat_km | getKcatKmValue |
| substrates | getSubstratesProducts |
| names | getEnzymeNames |
| engineering | getEngineering |

- 参数：`ecNumber*...`、`organism*...`（空则 `organism*`）+ 各方法字段；返回值递归转 plain dict。
- 空列表是正常 `count: 0`；认证失败 `AuthError`；其他 SOAP 错误 `UpstreamError`。
- CC BY 4.0；不要批量抓取/再分发。

## 验证

- 单测用 fake service 验证参数/哈希/method/错误映射；2026-11-22 用真实凭证 live 验证：EC 1.1.1.1 + Homo sapiens 返回 181 条 Km；工具层不限物种返回 1067 条；字段 commentary/ecNumber/kmValue/kmValueMaximum/ligandStructureId/literature/organism/substrate。
- 配好后跑 `docs/CREDENTIALS.md` 第 5 节的 Python 片段或 `live_smoke.py`（只在 env 有 BRENDA 时追加用例）。
