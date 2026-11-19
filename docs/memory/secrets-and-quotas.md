# 密钥、环境与限速

> 迁移自 finance-mcp `finance-mcp-env-and-quotas`，按本项目的"全免 key"形态改写。

- 本服务**零必需 key**。可选：`NCBI_API_KEY` + `NCBI_EMAIL`（PubMed / Gene / ClinVar 提速）、`MATERIALS_PROJECT_API_KEY`（材料工具）、`BIOGRID_ACCESS_KEY`（互作 source）、`OPENFDA_API_KEY`（可选，只提额度）。MP 未配不注册 `material`；BioGRID 未配时 `protein_interactions` 仍注册但 biogrid source 报错；openFDA 始终可用。NCBI 部分：免费申请，把 E-utilities 从 3 req/s 提到 10 req/s；不配静默降速，不报错。申请步骤与 M6 扩展源入口见 `docs/CREDENTIALS.md`。
- 应用**不加载 `.env`**（无 dotenv 依赖）。本地测试要先用 `set -a; . .env; set +a`；Docker/mcpo 由部署层注入 env。
- key 只按需探测（`os.environ.get`），不读整个 `.env`，不把 key 写进日志/返回体；错误信息只带 host（`errors.scrub` 兜底）。
- E-utilities 只支持把 `api_key` 放 query 参数，所以 `build_service()` 把 httpx 的 INFO 请求日志压到 WARNING，防止完整 URL（含 key）落日志。
- 限速表在 `config.HOST_DELAYS`：
  - PubChem ≤5 req/s → 0.2s
  - ChEMBL "moderate" → 0.5s（实测单请求可达 9s，见 flaky-upstream-apis）
  - UniProt / RCSB data → 0.2s；RCSB search → 0.5s
  - NCBI E-utilities → 0.34s（无 key 3/s 的倒数）；有 key 时 0.1s（10/s）
  - Materials Project → 1.0s（MP 会对侵略性流量限速/封 IP）
  - BioGRID → 1.0s（未公布限额，保守）
  - STRING → 0.5s
  - openFDA → 0.5s（无 key 1,000/day）
  - ClinicalTrials.gov → 0.5s
- 自动化测试一律 mock，禁止真实调用；`scripts/live_smoke.py` 每次会话最多 1–2 轮。
