# 配置与 API key 获取指南

先说结论：**二十八个基础源里二十七个完全免 key，什么都不配也能用。** 四个可选 key：NCBI E-utilities（PubMed 3→10 req/s）、Materials Project（材料工具）、BioGRID（互作 source）、openFDA（只提额度）；MP 未配时 `material` 不注册，BioGRID 未配时 `protein_interactions(source="biogrid")` 报明确错误。PubChem / ChEMBL / UniProt / RCSB PDB / WHO / STRING / ClinicalTrials.gov / AlphaFold DB / Open Targets / Reactome / InterPro / QuickGO / HPO / DailyMed / GDC / cBioPortal / GTEx / Ensembl / ChEBI / BindingDB / GWAS Catalog / Monarch 官方**不签发 key**；KEGG 学术免费、商用需许可。NCBI Gene / ClinVar / GEO 与 PubMed 共用 NCBI key。

> 配好后把值写进你的配置处：
> - **mcpo**：`config.json` 的 `scientific-data.env` 块
> - **Docker / compose**：`environment:` 或 `--env-file`
> - **本地 / uvx**：shell 环境变量（本服务**不读 `.env`**，没有 dotenv 依赖）

---

## 第 0 级 · 推荐（免费，1 分钟）

### 1. NCBI E-utilities key（`NCBI_API_KEY`）+ 联系邮箱（`NCBI_EMAIL`）

影响所有 NCBI E-utilities 源（`pubmed_record` / `gene_record` / `clinvar` / `geo_datasets`）的吞吐：无 key 3 req/s，有 key 10 req/s；单次调用两者都能成功，key 不是必需。

1. 打开 [NCBI 账号页](https://account.ncbi.nlm.nih.gov/) 注册或登录（Google/ORCID/机构账号均可）
2. 登录后进 [Account Settings](https://www.ncbi.nlm.nih.gov/account/settings/)
3. 找到 **API Key Management** → **Create an API Key**
4. 复制生成的 key（一串字母数字）→ 设 `NCBI_API_KEY`
5. 建议同时设 `NCBI_EMAIL=you@example.com`：E-utilities 用它作为联系邮箱（NCBI 对高频调用会先联系而不是直接封）

```bash
export NCBI_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
export NCBI_EMAIL=you@example.com
```

验证：

```bash
python scripts/live_smoke.py   # pubmed_record 一项 PASS 即通
```

> key 通过 E-utilities 唯一支持的 query 参数传递，因此会出现在请求 URL 里；本项目在 `build_service()` 里把 httpx 的 INFO 请求日志压到 WARNING，避免 key 落进日志。错误信息只带 host，不带 URL。

### 2. Materials Project key（`MATERIALS_PROJECT_API_KEY`）

影响 `material` 工具：没有 key 时它**不注册**（不是报错），配置后服务启动即多 1 个工具。

1. 打开 [materialsproject.org](https://materialsproject.org/) 注册/登录（免费账号）
2. 进入 Dashboard → **API** 页（[materialsproject.org/api](https://materialsproject.org/api)）生成 API key
3. 设 `MATERIALS_PROJECT_API_KEY=<key>`；请求头为 `X-API-KEY`
4. 免费额度足以做常规查询；MP 明确会对侵略性流量限速/封 IP，本项目对 `api.materialsproject.org` 固定 1 req/s

验证：`MATERIALS_PROJECT_API_KEY=... python scripts/live_smoke.py` 会多跑两条材料用例（无 key 时自动跳过）。

### 3. BioGRID access key（`BIOGRID_ACCESS_KEY`）

影响 `protein_interactions(source="biogrid")`：没有 key 时 BioGRID provider 缺席，但工具仍注册（STRING 可用），biogrid source 返回明确错误；配置后该 source 可用，不增加工具数。

1. 打开 [webservice.thebiogrid.org](https://webservice.thebiogrid.org/)
2. 在首页表单填写姓名、email、用途（project）→ **Generate access key**，即时签发 32 位 key（无需登录流程）
3. 设 `BIOGRID_ACCESS_KEY=<key>`；请求以 query 参数 `accesskey` 传递
4. 未公布正式限额；本项目固定 1 req/s，按需使用

验证：`BIOGRID_ACCESS_KEY=... python scripts/live_smoke.py` 会多跑 `TP53` 互作用例。

### 4. openFDA API key（`OPENFDA_API_KEY`，可选，只提额度）

影响 `openfda` 的限额，不影响可用性：**不配也能查**，只是额度低。

1. 打开 [open.fda.gov/apis/authentication](https://open.fda.gov/apis/authentication/) 填表申请（只需 email 等基本信息，免费）
2. 收到 key 后设 `OPENFDA_API_KEY=<key>`；请求以 query 参数 `api_key` 传递
3. 限额：无 key **240 req/min + 1,000 req/day per IP**；有 key **240 req/min + 120,000 req/day per key**
4. 工具始终注册；key 只用于提额度，不会隐藏工具

---

## 第 1 级 · M6 扩展源（尚未接入，先给入口）

以下源有**免费注册 key**，属于 `docs/计划.md` 的 M6 候选；当前版本**没有实现**，变量名是接入时的约定。填了也不会生效，等 provider 落地后再按这里申请。

| 变量（约定） | 源 | 免费额度 | 申请入口 |
|--------------|----|----------|----------|
| `NOAA_TOKEN` | NOAA CDO | 免费 token，5 req/s | [ncdc.noaa.gov/cdo-web/token](https://www.ncdc.noaa.gov/cdo-web/token) |
| `NASA_API_KEY` | NASA Open APIs | 免费 key，1,000 req/hr（DEMO_KEY 30/hr） | [api.nasa.gov](https://api.nasa.gov/) |

无 key 的 M6 候选（DisGeNET、OMIM 等）不需要申请，接入时直接免 key。

---

## 不需要 key 的当前源

| 源 | 官方说明 | 本项目限速 |
|----|----------|-----------|
| PubChem PUG-REST | 免 key，动态限速 | 5 req/s（0.2s 间隔） |
| ChEMBL EBI REST | 免 key，"keep request rates moderate" | 0.5s 间隔 |
| UniProt REST | 免 key | 0.2s 间隔 |
| RCSB PDB Data/Search | 免 key | 0.2s / 0.5s |
| WHO GHO OData | 免 key | 0.5s |
| STRING | 免 key | 0.5s |
| openFDA | 免 key（可选 key 提额度） | 0.5s |
| ClinicalTrials.gov v2 | 免 key | 0.5s |
| AlphaFold DB | 免 key | 0.5s |
| Open Targets | 免 key（GraphQL） | 0.5s |
| Reactome | 免 key | 0.5s |
| NCBI Gene | 免 key（可选 NCBI key 提速） | 0.34s / 0.1s |
| ClinVar | 免 key（可选 NCBI key 提速） | 0.34s / 0.1s |
| InterPro | 免 key | 0.5s |
| QuickGO | 免 key | 0.5s |
| HPO | 免 key | 0.5s |
| GEO (NCBI) | 免 key（可选 NCBI key 提速） | 0.34s / 0.1s |
| KEGG | 学术免费（商用需许可） | 0.5s |
| DailyMed | 免 key | 0.5s |
| GDC | 免 key | 0.5s |
| cBioPortal | 免 key | 0.5s |
| GTEx | 免 key | 0.5s |
| Ensembl | 免 key；低频（1 请求/次，5s，403 不重试） | 5s |
| ChEBI | 免 key（OLS4） | 0.5s |
| BindingDB | 免 key；~1 req/s | 1s |
| GWAS Catalog | 免 key | 0.5s |
| Monarch | 免 key | 0.5s |

限速表在 `src/scientific_data_mcp/config.py` 的 `HOST_DELAYS`。

---

## 纪律

- key 只放环境变量，**永不进 git**（`.env` 已在 `.gitignore`）。
- 应用不主动读 `.env`：本地测试先 `set -a; . .env; set +a`。
- key 只按需探测（`os.environ.get`），不打印、不写返回体；错误只带 host。
- 自动化测试一律 mock，不消耗真实额度；`scripts/live_smoke.py` 每会话最多跑 1–2 轮。
