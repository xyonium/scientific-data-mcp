# scientific-data-mcp

科研**实体数据** MCP —— 化合物 / 生物活性 / 蛋白序列与结构 / 基因 / 临床 / 通路 的**免费官方 API 直连**。

> 状态：**立项中**。详细计划与种子源清单见 [`docs/计划.md`](./docs/计划.md)。

## 定位

| 兄弟项目 | 管什么 | 不管 |
|----------|--------|------|
| [finance-mcp](../finance-mcp) | 金融/宏观行情 | 科研 |
| [paper-search](../paper-search) | 学术**文献**检索 + RAG 入 OpenWebUI | 实体数据 |
| **scientific-data-mcp**（本项目） | 科研**实体数据**：化合物、蛋白、基因、临床试验、通路 | 跨库文献检索（归 paper-search） |

## 为什么立项

kimi datasource 把一批本来就免 key 的官方科研 API（pubchem / chembl / uniprot / pdb / pubmed）包装成收费额度源。我们在 finance-mcp 侧把这批源摘除（证据 `finance-mcp/docs/research/kimi-sources/*.verdict.md`），免费直连落点即本项目。

## 种子源（已实测免费）

- **PubChem** — 化合物 / 性质（PUG-REST，免 key）
- **ChEMBL** — 药物靶点生物活性（EBI REST，免 key）
- **UniProt** — 蛋白序列 / 功能（rest.uniprot.org，免 key）
- **PDB (RCSB)** — 实验结构（data.rcsb.org，免 key）
- **PubMed** — 文献结构化元数据（E-utilities，免 key / 可选 key 提速；边界受控，不做跨库搜索）

## 参考

- [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills) — 165 个科研 agent skill 的源全景（本项目 M2–M6 扩展池）
- finance-mcp 的 provider / tool / 容器模式 — 本项目直接复用
