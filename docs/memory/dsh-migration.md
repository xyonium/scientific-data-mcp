# 从 Claude Code 迁到 DSH

> 2026-11-17。

## 迁移前

项目在 `eli@dockerno1:~/scientific-data-mcp`，只有 `README.md` + `docs/计划.md`，没有 git、没有代码、没有 `CLAUDE.md`；相关"记忆"散落在 dockerno1 的 Claude Code memory：

- `~/.claude/projects/-home-eli-finance-mcp/memory/`（kimi 去重、发布、配额）
- `~/.claude/projects/-home-eli-paper-search/memory/`（境外 API 不稳、docstring 纪律、边界）
- `~/.claude/CLAUDE.md`（firecrawl / codegraph 工具纪律）

## 迁移后

- 代码到本机 `/home/eli/ai-tool/scientific-data-mcp`，新建 git 仓库。
- 常驻指令：**`AGENTS.md`**。DSH 会加载 `AGENTS.md`/`CLAUDE.md`；本项目只保留 `AGENTS.md`，不再有 `.claude/`，也不依赖 Claude Code 专有机制。
- 记忆：`docs/memory/` + `MEMORY.md` 索引；`AGENTS.md` 里按域指路。原因：DSH 没有 Claude Code 那种自动 memory 注入，笔记必须显式落库并被指令引用，否则等于没写。
- 证据：finance-mcp 的 5 份 verdict 原文进 `docs/research/kimi-sources/`，作为立项依据可追溯。

## 以后

- 别再引入 `.claude/`、Claude hooks、Claude 专有 settings；需要新纪律就写 `AGENTS.md`，需要新记忆就写 `docs/memory/` 并在索引里挂一行。
- 跨项目共享的纪律（firecrawl/codegraph）放 `AGENTS.md` 的"Agent 工具纪律"，不要依赖用户级 `~/.claude/CLAUDE.md`。
