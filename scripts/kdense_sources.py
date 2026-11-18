#!/usr/bin/env python3
"""Track the K-Dense ``database-lookup`` catalogue and report changes.

The upstream skill lists every database in grouped Markdown tables under
``## Available Databases``. This script parses that section into a stable
JSON snapshot, so the quarterly GitHub Action can tell us when the upstream
catalogue grows a database we have not evaluated.

Usage:
    python scripts/kdense_sources.py --update
    python scripts/kdense_sources.py --check [--report kdense-diff.md]

Exit codes: 0 = no database added/removed; 1 = set changed (action needed);
2 = fetch/parse failure (no verdict either way).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import urllib.request
from pathlib import Path

DEFAULT_URL = (
    "https://raw.githubusercontent.com/K-Dense-AI/scientific-agent-skills/main/"
    "skills/database-lookup/SKILL.md"
)
DEFAULT_SNAPSHOT = Path("docs/research/kdense-databases.json")

_ROW_RE = re.compile(
    r"^\|\s*([^|]+?)\s*\|\s*`references/([^`]+\.md)`\s*\|(.*?)\|\s*$"
)


def parse_catalog(text: str) -> dict:
    """Parse the SKILL.md frontmatter + Available Databases tables."""
    front = ""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            front = parts[1]
    version = re.search(r'^\s*version:\s*"?([^"\n]+)"?\s*$', front, re.MULTILINE)
    reviewed = re.search(
        r'^\s*last-reviewed:\s*"?([^"\n]+)"?\s*$', front, re.MULTILINE
    )

    if "## Available Databases" not in text:
        raise ValueError("section '## Available Databases' not found")
    body = text.split("## Available Databases", 1)[1].split("\n## ", 1)[0]

    databases: list[dict] = []
    category = None
    for line in body.splitlines():
        heading = re.match(r"^###\s+(.+?)\s*$", line)
        if heading:
            category = heading.group(1).strip()
            continue
        row = _ROW_RE.match(line)
        if row and category:
            databases.append(
                {
                    "name": row.group(1).strip(),
                    "reference": f"references/{row.group(2).strip()}",
                    "category": category,
                    "coverage": row.group(3).strip(),
                }
            )
    if not databases:
        raise ValueError("no database rows parsed — upstream table shape changed")
    return {
        "skill_version": version.group(1).strip() if version else None,
        "last_reviewed": reviewed.group(1).strip() if reviewed else None,
        "databases": databases,
    }


def diff_catalogs(old: dict, new: dict) -> dict:
    """Compare by reference file (the stable id), then name/category/coverage."""
    old_map = {db["reference"]: db for db in old.get("databases", [])}
    new_map = {db["reference"]: db for db in new.get("databases", [])}
    added = [new_map[key] for key in sorted(new_map.keys() - old_map.keys())]
    removed = [old_map[key] for key in sorted(old_map.keys() - new_map.keys())]
    changed = []
    for key in sorted(old_map.keys() & new_map.keys()):
        before, after = old_map[key], new_map[key]
        fields = [
            field
            for field in ("name", "category", "coverage")
            if before.get(field) != after.get(field)
        ]
        if fields:
            changed.append({"before": before, "after": after, "fields": fields})
    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "version_before": old.get("skill_version"),
        "version_after": new.get("skill_version"),
    }


def has_set_change(diff: dict) -> bool:
    return bool(diff["added"] or diff["removed"])


def render_report(diff: dict, today: str) -> str:
    lines = [f"## K-Dense 数据源清单变化（{today}）", ""]
    lines.append(
        f"- 上游 skill 版本：`{diff['version_before']}` → `{diff['version_after']}`"
    )
    lines.append(
        f"- 数据库条目：+{len(diff['added'])} / -{len(diff['removed'])} / "
        f"~{len(diff['changed'])}"
    )
    lines.append("")
    if diff["added"]:
        lines += ["### 新增（需要评估是否接入）", "", "| 分类 | 数据库 | 参考文件 |", "|---|---|---|"]
        lines += [
            f"| {db['category']} | {db['name']} | `{db['reference']}` |"
            for db in diff["added"]
        ]
        lines.append("")
    if diff["removed"]:
        lines += ["### 移除（检查是否已接入）", "", "| 分类 | 数据库 | 参考文件 |", "|---|---|---|"]
        lines += [
            f"| {db['category']} | {db['name']} | `{db['reference']}` |"
            for db in diff["removed"]
        ]
        lines.append("")
    if diff["changed"]:
        lines += ["### 条目变更", "", "| 参考文件 | 字段 | 变更前 | 变更后 |", "|---|---|---|---|"]
        for item in diff["changed"]:
            for field in item["fields"]:
                lines.append(
                    f"| `{item['after']['reference']}` | {field} | "
                    f"{item['before'].get(field)} | {item['after'].get(field)} |"
                )
        lines.append("")
    lines += [
        "### 处理",
        "",
        "1. 逐个评估新增源：免 key / 免费注册 key / 付费，归本仓库还是 paper-search。",
        "2. 更新 `docs/计划.md` 的 M6 候选池（若值得接入）。",
        "3. 跑 `python scripts/kdense_sources.py --update` 刷新快照并提交。",
        "",
    ]
    return "\n".join(lines)


def fetch(url: str, timeout: float = 30.0) -> str:
    request = urllib.request.Request(
        url, headers={"User-Agent": "scientific-data-mcp-kdense-scan/1.0"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--update", action="store_true", help="refresh the snapshot")
    action.add_argument("--check", action="store_true", help="diff upstream vs snapshot")
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--report", type=Path, help="write the Markdown report here")
    args = parser.parse_args(argv)

    try:
        catalog = parse_catalog(fetch(args.url))
    except Exception as exc:  # noqa: BLE001 - CLI must report, not traceback
        message = f"K-Dense catalogue fetch/parse failed: {type(exc).__name__}: {exc}"
        if args.report:
            args.report.write_text(f"## K-Dense 扫描失败\n\n{message}\n", encoding="utf-8")
        print(message, file=sys.stderr)
        return 2

    today = dt.date.today().isoformat()
    if args.update:
        snapshot = {
            "source_url": args.url,
            "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            **catalog,
        }
        args.snapshot.parent.mkdir(parents=True, exist_ok=True)
        args.snapshot.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(
            f"snapshot updated: {args.snapshot} "
            f"({len(catalog['databases'])} databases, v{catalog['skill_version']})"
        )
        return 0

    if not args.snapshot.exists():
        print(f"snapshot missing: {args.snapshot}", file=sys.stderr)
        return 2
    old = json.loads(args.snapshot.read_text(encoding="utf-8"))
    diff = diff_catalogs(old, catalog)
    report = render_report(diff, today)
    if args.report:
        args.report.write_text(report + "\n", encoding="utf-8")
    print(
        f"K-Dense database-lookup v{diff['version_before']} -> v{diff['version_after']}: "
        f"+{len(diff['added'])} -{len(diff['removed'])} ~{len(diff['changed'])}"
    )
    if has_set_change(diff):
        print(report)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
