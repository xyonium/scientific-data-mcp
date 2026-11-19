# AlphaFold DB / Open Targets / Reactome（v0.7.0）

> 2026-11-19。三个基础免 key 源；AlphaFold 并入 `protein_record`，不新增工具。

## AlphaFold DB

- 并入 `protein_record(kind="alphafold", identifier="P04637")`；返回 `{accession, predictions: [...]}`，最多 20 个模型。
- Endpoint：`https://alphafold.ebi.ac.uk/api/prediction/{accession}`；无 key。
- 一个 UniProt 条目可能返回多个 isoform（P04637 有 9 个）；每条含 `entry_id`、`version`、`start/end`、`plddt`、`pdb_url`/`cif_url`/`pae_image_url`。
- 无效格式返回 **400**（不是 404）：provider 转成 `ValueError`，工具返回普通错误（不标 drift）。404 走正常 `NotFound`。
- `include_sequence` 对 alphafold 无效。

## Open Targets

- 工具 `opentargets(query, entity="target"|"disease", limit=5)`。
- GraphQL `https://api.platform.opentargets.org/api/v4/graphql`；两步：`search` 解析 hit，再 `target(ensemblId)` / `disease(efoId)` 取 associations。
- `score` 是 Open Targets association score（0-1），不是 p 值；`count` 是关联总数，`items` 才是本页。
- GraphQL `errors` → `UpstreamDrift`；`data.target/disease` 为 null → `NotFound`。
- 只返回上游字段；`functionDescriptions` 可能很长。

## Reactome

- 工具 `pathways(query, species="Homo sapiens", limit=10)`；`species=""` 查所有物种。
- Endpoint：`https://reactome.org/ContentService/search/query`，参数 `query`、`species`、`types=Pathway`、`cluster=true`。
- 响应是分组 `results[].entries[]`；只保留 `type=="Pathway"`，按 `stId` 去重；`name` 里的 `<span class="highlighting">` 必须剥掉并 HTML unescape。
- 缺 `results` → drift；空列表正常。`total` 用 `numberOfMatches`。

## 验证

- 143 tests；keyed live 22/22（AlphaFold P04637、Open Targets TP53、Reactome TP53）。
