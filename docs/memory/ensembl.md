# Ensembl 接入（v0.12.0）

> 2026-11-20。用户配置了 `rest.ensembl.org` 到 3 个可用节点的自动路由后恢复；严格低频。

## 工具

- 并入 `gene_record(kind="ensembl", identifier, organism=9606)`，不新增工具。
- `identifier`：基因符号（`TP53`）或 Ensembl gene id（`ENSG00000141510`）。
- taxid 映射：9606 human / 10090 mouse / 10116 rat / 559292 yeast / 7227 fly / 6239 worm / 7955 zebrafish / 3702 Arabidopsis / 9031 chicken / 9615 dog / 9823 pig / 9913 cow / 9544 macaque；其他报 `unsupported organism`。
- 符号：`GET /lookup/symbol/{species}/{symbol}?content-type=application/json`；ID：`GET /lookup/id/{id}?species={species}&content-type=application/json` + `Accept: application/json`。
- 归一化：gene_id/symbol/description/biotype/species/chromosome/start/end/strand/assembly/canonical_transcript/version。

## 访问纪律（重要）

- **1 请求/次调用**，host delay **5s**，`retry=False`。
- 403/429 立即 `UpstreamError`，**不重试、不换路径/UA/IP**。
- 不跑 ping/健康检查；不加入 `live_smoke.py`/CI/定时任务；只在实际工具调用时请求。
- 手动 live 验证只发一次请求，成功即停；失败冷却 ≥24h。
- 背景：此前短时突发+403 重试疑似触发 WAF，多个节点被封；详见 `ensembl-rest-access.md`。

## 验证

- 210 tests（全部 mock，0 egress）。
- 单次 live 请求成功：`TP53 -> ENSG00000141510, chr17`。
