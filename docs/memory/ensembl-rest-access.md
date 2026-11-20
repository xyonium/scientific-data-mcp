# Ensembl REST：暂停探测（2026-11-20）

> **结论：不要再请求 `rest.ensembl.org`，包括 ping、lookup、可用性探测。** 该源暂停接入，直到人工明确恢复。

## 发生了什么

- 为实现 `gene_record(kind="ensembl")`，在短时间内对 `rest.ensembl.org` 发了多轮请求：ping、symbol、id、400/404 边界、不同 `Accept`/UA/HTTP 版本、换 ALB IP、换出口节点；遇到 403/504 后还做了重试与变体探测。
- 结果从“偶尔 200”变成持续 `403 Forbidden`（`server: awselb/2.0`）或 `504`；用户报告多个服务器节点随后也不能访问，只剩少数节点可用。
- 无法证明 100% 是我们触发的，但请求模式（短时突发 + 403 后重试 + 换 IP/路径）是典型会触发 WAF/风控的行为；我们应按“可能是我们造成的”处理。

## 硬规则

1. **不主动探测** `rest.ensembl.org`，不跑 ping/健康检查，不把它加进 smoke/CI/定时任务。
2. 任何 403/429 **立即停止**，不重试、不换路径、不换 UA、不换 IP/节点。
3. 不通过轮换出口节点绕过封锁；只在用户明确指定且批准的单节点上手动试。
4. 若将来恢复：单节点、≥5s 间隔、每次只发 1 个请求、失败即停并冷却 ≥24h；先由用户确认节点可用。
5. Ensembl 未实现为 provider；当前代码/脚本没有访问它的路径。

## 替代

- 基因记录用 NCBI Gene（`gene_record` 默认）。
- 蛋白/结构/注释用 UniProt/PDB/InterPro/QuickGO。
- 表达用 GTEx（`gene_expression`）。
- Ensembl 只在用户明确恢复并给出可用、允许自动访问的节点后再考虑。
