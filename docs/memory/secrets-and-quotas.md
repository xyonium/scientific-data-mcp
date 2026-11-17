# 密钥、环境与限速

> 迁移自 finance-mcp `finance-mcp-env-and-quotas`，按本项目的"全免 key"形态改写。

- 本服务**零必需 key**。`NCBI_API_KEY` 是唯一可选变量：免费申请，把 E-utilities 从 3 req/s 提到 10 req/s；不配静默降速，不报错。
- 应用**不加载 `.env`**（无 dotenv 依赖）。本地测试要先用 `set -a; . .env; set +a`；Docker/mcpo 由部署层注入 env。
- key 只按需探测（`os.environ.get`），不读整个 `.env`，不把 key 写进日志/返回体；错误信息只带 host（`errors.scrub` 兜底）。
- 限速表在 `config.HOST_DELAYS`：
  - PubChem ≤5 req/s → 0.2s
  - ChEMBL "moderate" → 0.5s（实测单请求可达 9s，见 flaky-upstream-apis）
  - UniProt / RCSB data → 0.2s；RCSB search → 0.5s
  - NCBI E-utilities → 0.34s（无 key 3/s 的倒数）
- 自动化测试一律 mock，禁止真实调用；`scripts/live_smoke.py` 每次会话最多 1–2 轮。
