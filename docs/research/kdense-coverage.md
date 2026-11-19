# K-Dense 80 库覆盖/排除矩阵

> 快照：`docs/research/kdense-databases.json`（database-lookup v1.8，80 库，last-reviewed 2026-09-30）
> 状态口径：✅ 已实现 / ⏳ M6 候选 / ⏳ 暂缓 / ➖ 归兄弟项目 / 💰 不做。
> key 栏是**访问要求**，不是“我们有没有配”：免 key = 公开；免费 key = 需注册；付费/许可受限 = 不做。

## 汇总

| 状态 | 数量 |
|---|---|
| ✅ 已实现 | 13 |
| ⏳ M6 候选 | 51 |
| ⏳ 暂缓 | 1 |
| ➖ 归 finance-mcp | 12 |
| ➖ 归 paper-search | 1 |
| 💰 不做 | 2 |
| **合计** | **80** |

不在 K-Dense 80 库、但本项目已实现：**PubMed**（来自 kimi 五个科学源，E-utilities 记录级查询）。

## 逐源矩阵

| 分类 | 源 | 状态 | key | 说明 |
|---|---|---|---|---|
| Chemistry & Drugs | BindingDB | ⏳ M6 候选 | 免 key | 免 key；M2 池，未接 |
| Chemistry & Drugs | ChEBI | ⏳ M6 候选 | 免 key | 免 key；M2 池，未接 |
| Chemistry & Drugs | ChEMBL | ✅ 已实现 | 免 key | 已接入（v0.6.0） |
| Chemistry & Drugs | DailyMed | ⏳ M6 候选 | 免 key | 免 key；M2 池，未接 |
| Chemistry & Drugs | DrugBank | 💰 不做 | 付费 | 付费；免费替代 PubChem/ChEMBL/openFDA（openFDA 已接入） |
| Chemistry & Drugs | FDA (OpenFDA) | ✅ 已实现 | 免费 key（可选） | 已接入（v0.6.0） |
| Chemistry & Drugs | KEGG | ⏳ M6 候选 | 免 key | 免 key；M2 池，未接 |
| Chemistry & Drugs | PubChem | ✅ 已实现 | 免 key | 已接入（v0.6.0） |
| Chemistry & Drugs | ZINC | ⏳ M6 候选 | 免 key | 免 key；M2 池，未接 |
| Biology & Genomics | Addgene | ⏳ M6 候选 | 机构批准 key | 机构批准 key；M3 池，未接 |
| Biology & Genomics | AlphaFold DB | ✅ 已实现 | 免 key | 已接入（v0.7.0） |
| Biology & Genomics | BRENDA | ⏳ 暂缓 | 免费注册（SOAP） | 免费但需注册 + SOAP，解析成本高，暂缓 |
| Biology & Genomics | BioGRID | ✅ 已实现 | 免费 key | 已接入（v0.6.0） |
| Biology & Genomics | EMDB | ⏳ M6 候选 | 免 key | 免 key；M3 池，未接 |
| Biology & Genomics | ENA | ⏳ M6 候选 | 免 key | 免 key；M3 池，未接 |
| Biology & Genomics | ENCODE | ⏳ M6 候选 | 免 key | 免 key；M3 池，未接 |
| Biology & Genomics | Ensembl | ⏳ M6 候选 | 免 key | 免 key；M3 池，未接 |
| Biology & Genomics | GEO (NCBI) | ⏳ M6 候选 | 免 key | 免 key；M3 池，未接 |
| Biology & Genomics | GTEx | ⏳ M6 候选 | 免 key | 免 key；M3 池，未接 |
| Biology & Genomics | Gene Ontology | ⏳ M6 候选 | 免 key | 免 key；M3 池，未接 |
| Biology & Genomics | Human Cell Atlas | ⏳ M6 候选 | 免 key | 免 key；M3 池，未接 |
| Biology & Genomics | Human Protein Atlas | ⏳ M6 候选 | 免 key | 免 key；M3 池，未接 |
| Biology & Genomics | InterPro | ⏳ M6 候选 | 免 key | 免 key；M3 池，未接 |
| Biology & Genomics | JASPAR | ⏳ M6 候选 | 免 key | 免 key；M3 池，未接 |
| Biology & Genomics | LINCS L1000 | ⏳ M6 候选 | 免费学术 key | 免费学术 key；M3 池，未接 |
| Biology & Genomics | Metabolomics Workbench | ⏳ M6 候选 | 免 key | 免 key；M3 池，未接 |
| Biology & Genomics | MouseMine | ⏳ M6 候选 | 免 key | 免 key；M3 池，未接 |
| Biology & Genomics | MyVariant.info | ⏳ M6 候选 | 免 key | 免 key；M3 池，未接 |
| Biology & Genomics | NCBI Gene | ⏳ M6 候选 | 免 key | 免 key；M3 池，未接 |
| Biology & Genomics | NCBI Protein | ⏳ M6 候选 | 免 key | 免 key；M3 池，未接 |
| Biology & Genomics | NCBI Taxonomy | ⏳ M6 候选 | 免 key | 免 key；M3 池，未接 |
| Biology & Genomics | PDB | ✅ 已实现 | 免 key | 已接入（v0.6.0） |
| Biology & Genomics | PRIDE | ⏳ M6 候选 | 免 key | 免 key；M3 池，未接 |
| Biology & Genomics | QuickGO | ⏳ M6 候选 | 免 key | 免 key；M3 池，未接 |
| Biology & Genomics | Reactome | ✅ 已实现 | 免 key | 已接入（v0.7.0） |
| Biology & Genomics | RegulomeDB | ⏳ M6 候选 | 免 key | 免 key；M3 池，未接 |
| Biology & Genomics | RummaGEO | ⏳ M6 候选 | 免 key | 免 key；M3 池，未接 |
| Biology & Genomics | SRA | ⏳ M6 候选 | 免 key | 免 key；M3 池，未接 |
| Biology & Genomics | STRING | ✅ 已实现 | 免 key | 已接入（v0.6.0） |
| Biology & Genomics | UCSC Genome Browser | ⏳ M6 候选 | 免 key | 免 key；M3 池，未接 |
| Biology & Genomics | UniProt | ✅ 已实现 | 免 key | 已接入（v0.6.0） |
| Biology & Genomics | dbSNP | ⏳ M6 候选 | 免 key | 免 key；M3 池，未接 |
| Biology & Genomics | gnomAD | ⏳ M6 候选 | 免 key | 免 key；M3 池，未接 |
| Disease & Clinical | COSMIC | 💰 不做 | 许可受限 | 许可受限；替代 openFDA/GDC/cBioPortal（openFDA 已接入） |
| Disease & Clinical | ClinPGx (PharmGKB) | ⏳ M6 候选 | 免 key | 免 key；M4 池，未接 |
| Disease & Clinical | ClinVar | ⏳ M6 候选 | 免 key | 免 key；M4 池，未接 |
| Disease & Clinical | ClinicalTrials.gov | ✅ 已实现 | 免 key | 已接入（v0.6.0） |
| Disease & Clinical | DisGeNET | ⏳ M6 候选 | 学术/许可 key | 学术/许可 key；M4 池，未接 |
| Disease & Clinical | GDC (TCGA) | ⏳ M6 候选 | 免 key | 免 key；M4 池，未接 |
| Disease & Clinical | GWAS Catalog | ⏳ M6 候选 | 免 key | 免 key；M4 池，未接 |
| Disease & Clinical | HPO | ⏳ M6 候选 | 免 key | 免 key；M4 池，未接 |
| Disease & Clinical | Monarch Initiative | ⏳ M6 候选 | 免 key | 免 key；M4 池，未接 |
| Disease & Clinical | OMIM | ⏳ M6 候选 | 学术许可 key | 学术许可 key；M4 池，未接 |
| Disease & Clinical | Open Targets | ✅ 已实现 | 免 key | 已接入（v0.7.0） |
| Disease & Clinical | cBioPortal | ⏳ M6 候选 | 免 key | 免 key；M4 池，未接 |
| Materials Science | COD | ⏳ M6 候选 | 免 key | 免 key；M5 池，未接 |
| Materials Science | Materials Project | ✅ 已实现 | 免费 key | 已接入（v0.6.0） |
| Physics & Astronomy | NASA | ⏳ M6 候选 | 免费 key | 免费 key；M5 池，未接 |
| Physics & Astronomy | NASA Exoplanet Archive | ⏳ M6 候选 | 免 key | 免 key；M5 池，未接 |
| Physics & Astronomy | NIST | ⏳ M6 候选 | 免 key | 免 key；M5 池，未接 |
| Physics & Astronomy | SDSS | ⏳ M6 候选 | 免 key | 免 key；M5 池，未接 |
| Physics & Astronomy | SIMBAD | ⏳ M6 候选 | 免 key | 免 key；M5 池，未接 |
| Earth & Environmental Sciences | EPA | ⏳ M6 候选 | 免 key | 免 key；M5 池，未接 |
| Earth & Environmental Sciences | NOAA | ⏳ M6 候选 | 免费 key | 免费 key；M5 池，未接 |
| Earth & Environmental Sciences | OpenWeatherMap | ⏳ M6 候选 | 免费 key | 免费 key；M5 池，未接 |
| Earth & Environmental Sciences | USGS | ⏳ M6 候选 | 免 key | 免 key；M5 池，未接 |
| Patents & Regulatory | SEC EDGAR | ➖ 归 finance-mcp | 免 key | 已交接：见 docs/handoff/2026-11-18-kdense-finance-gaps.md |
| Patents & Regulatory | USPTO | ➖ 归 paper-search | 账号+实名+key | 交接结论：PatentsView 暂停，暂不新增 |
| Economics & Finance | Alpha Vantage | ➖ 归 finance-mcp | 免费 key | 已交接：见 docs/handoff/2026-11-18-kdense-finance-gaps.md |
| Economics & Finance | BEA | ➖ 归 finance-mcp | 免费 key | 已交接：见 docs/handoff/2026-11-18-kdense-finance-gaps.md |
| Economics & Finance | BLS (optional for basic v1) | ➖ 归 finance-mcp | 免费 key（v1 可匿名） | 已交接：见 docs/handoff/2026-11-18-kdense-finance-gaps.md |
| Economics & Finance | Data Commons | ➖ 归 finance-mcp | 免费 key | 已交接：见 docs/handoff/2026-11-18-kdense-finance-gaps.md |
| Economics & Finance | ECB | ➖ 归 finance-mcp | 免 key | 已交接：见 docs/handoff/2026-11-18-kdense-finance-gaps.md |
| Economics & Finance | FRED | ➖ 归 finance-mcp | 免费 key | 已交接：见 docs/handoff/2026-11-18-kdense-finance-gaps.md |
| Economics & Finance | Federal Reserve | ➖ 归 finance-mcp | 免 key | 已交接：见 docs/handoff/2026-11-18-kdense-finance-gaps.md |
| Economics & Finance | US Treasury | ➖ 归 finance-mcp | 免 key | 已交接：见 docs/handoff/2026-11-18-kdense-finance-gaps.md |
| Economics & Finance | World Bank | ➖ 归 finance-mcp | 免 key | 已交接：见 docs/handoff/2026-11-18-kdense-finance-gaps.md |
| Social Sciences & Demographics | Eurostat | ➖ 归 finance-mcp | 免 key | 已交接：见 docs/handoff/2026-11-18-kdense-finance-gaps.md |
| Social Sciences & Demographics | US Census (optional below anonymous quota) | ➖ 归 finance-mcp | 免费 key（可选） | 已交接：见 docs/handoff/2026-11-18-kdense-finance-gaps.md |
| Social Sciences & Demographics | WHO GHO | ✅ 已实现 | 免 key | 已接入（v0.6.0） |

## 说明

- “M6 候选”= 已确认属于本项目域、但当前版本未接；按 `docs/计划.md` 的 M2–M5 优先级排队。
- “归 finance-mcp”/“归 paper-search” 的实际缺口见 2026-11-18 交接：finance 只缺 SEC EDGAR（+ World Bank 透传/Treasury 可选）；paper 暂不新增 USPTO。
- “暂缓”不是永久排除；季度扫描或用户需求变化时可重新评估。
- BRENDA 官方为 CC BY 4.0、需注册后走 SOAP，因此不是“付费”，归入暂缓（解析成本）。
