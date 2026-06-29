#!/usr/bin/env python3
"""BOS project-schema validator (P017 / candidate A1).

Validates every `projects/*.md` "## IOs (machine-readable)" YAML block against
the IO schema, at AUTHOR TIME — the gap that let a divergent IO schema
(title/critical/closed instead of name/criticality/done) silently 500 the
dashboard home for the whole team for ~9 days before anyone noticed.

Two-tier tolerance, identical in spirit to the dashboard reader
(.claude/skills/dashboard/generate.py):

  HARD FAILURES (would break a parser / take a page down) -> exit 2 + Slack:
    - YAML doesn't parse
    - `ios:` is not a list, or `project:` is not a mapping
    - an IO entry is not a mapping
    - an IO is missing required `id` or `name`
    - `children` / `depends_on` is not a list

  WARNINGS (tolerated downstream but worth surfacing) -> exit 1, no Slack:
    - unknown `status` / `criticality` enum value
    - duplicate IO id within a project
    - `depends_on` referencing an id that doesn't exist in the project
    - unparseable `target_date`
    - file has no IOs block at all (likely an unintended omission)

Quiet-on-green like the other canaries: clean run prints a one-line summary and
exits 0. Slack fires ONLY on hard failures.

Usage:
    bos_lint.py                      # lint ./projects, human report
    bos_lint.py --root /path
    bos_lint.py --slack              # also Slack-alert on hard failures
    bos_lint.py --strict             # treat warnings as failures (pre-push gate)
    bos_lint.py --quiet              # print only on problems

Dependencies: Python 3.8+, PyYAML.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

try:
    import yaml
except ImportError:
    sys.stderr.write("ERROR: PyYAML required (pip install pyyaml)\n")
    sys.exit(3)

BOS_ROOT = Path.cwd()  # run from your BOS root, or pass --root
_IOS_BLOCK_RE = re.compile(
    r"## IOs \(machine-readable\)[\s\S]*?```yaml\n([\s\S]*?)\n```", re.MULTILINE
)
_VALID_STATUSES = {"open", "in-progress", "done", "blocked", "deferred", "needs-update"}
_VALID_CRITICALITY = {"critical", "supporting", "parallel"}


class HardError(Exception):
    """A structural problem that would break a parser."""


def _walk_io(entry, path_prefix: str, ids: List[str], warnings: List[str]) -> None:
    """Validate one IO node recursively. Raises HardError on structural breakage;
    appends soft issues to `warnings`. Collects ids for dup/depends_on checks."""
    if not isinstance(entry, dict):
        raise HardError(f"{path_prefix}: IO entry is not a mapping ({entry!r:.60})")
    if "id" not in entry or "name" not in entry:
        raise HardError(f"{path_prefix}: IO missing required id/name ({entry!r:.80})")

    io_id = str(entry["id"])
    ids.append(io_id)
    where = f"{path_prefix}/{io_id}"

    status = entry.get("status", "open")
    if status not in _VALID_STATUSES:
        warnings.append(f"{where}: non-standard status {status!r} "
                        f"(valid: {', '.join(sorted(_VALID_STATUSES))})")
    crit = entry.get("criticality", "supporting")
    if crit not in _VALID_CRITICALITY:
        warnings.append(f"{where}: non-standard criticality {crit!r} "
                        f"(valid: {', '.join(sorted(_VALID_CRITICALITY))})")

    td = entry.get("target_date")
    if td is not None and not isinstance(td, datetime):
        # PyYAML parses YYYY-MM-DD to a date already; a str here means it didn't.
        if isinstance(td, str):
            try:
                datetime.strptime(td.strip(), "%Y-%m-%d")
            except ValueError:
                warnings.append(f"{where}: unparseable target_date {td!r} (want YYYY-MM-DD)")

    deps = entry.get("depends_on")
    if deps is not None and not isinstance(deps, list):
        raise HardError(f"{where}: depends_on is not a list")

    children = entry.get("children")
    if children is not None and not isinstance(children, list):
        raise HardError(f"{where}: children is not a list")
    for child in (children or []):
        _walk_io(child, where, ids, warnings)


def lint_file(path: Path, is_toplevel: bool = True) -> Tuple[List[str], List[str]]:
    """Return (hard_errors, warnings) for one project file.

    `is_toplevel` (file sits directly in projects/, not a subdir) controls the
    "no IOs block" warning: a top-level project file with no block likely forgot
    one; a nested reference file (e.g. a book chapter under home-for-dinner/) is
    legitimately block-free and is skipped silently, matching the dashboard reader.
    """
    hard: List[str] = []
    warnings: List[str] = []
    rel = path.name
    text = path.read_text(encoding="utf-8", errors="replace")
    m = _IOS_BLOCK_RE.search(text)
    if not m:
        if is_toplevel:
            warnings.append(f"{rel}: no '## IOs (machine-readable)' block found")
        return hard, warnings

    try:
        data = yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:
        hard.append(f"{rel}: IOs block YAML does not parse — {str(e).splitlines()[0]}")
        return hard, warnings

    if not isinstance(data, dict):
        hard.append(f"{rel}: IOs block did not parse to a mapping")
        return hard, warnings

    if "project" in data and not isinstance(data.get("project"), dict):
        hard.append(f"{rel}: `project:` key is not a mapping")

    ios = data.get("ios")
    if ios is None:
        warnings.append(f"{rel}: IOs block has no `ios:` key")
        return hard, warnings
    if not isinstance(ios, list):
        hard.append(f"{rel}: `ios:` is not a list")
        return hard, warnings

    ids: List[str] = []
    try:
        for entry in ios:
            _walk_io(entry, rel, ids, warnings)
    except HardError as e:
        hard.append(str(e))
        return hard, warnings  # stop at first structural break in this file

    # Soft cross-checks once the tree is structurally sound.
    seen = set()
    for i in ids:
        if i in seen:
            warnings.append(f"{rel}: duplicate IO id {i!r}")
        seen.add(i)
    for entry in ios:
        _check_depends(entry, rel, set(ids), warnings)

    return hard, warnings


def _check_depends(entry, rel, all_ids, warnings) -> None:
    if isinstance(entry, dict):
        for dep in (entry.get("depends_on") or []):
            if dep not in all_ids:
                warnings.append(f"{rel}/{entry.get('id')}: depends_on {dep!r} "
                                f"is not an id in this project")
        for child in (entry.get("children") or []):
            _check_depends(child, rel, all_ids, warnings)


def post_slack(webhook: str, text: str) -> None:
    req = urllib.request.Request(
        webhook, data=json.dumps({"text": text}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        resp.read()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Validate BOS project IO schemas")
    ap.add_argument("--root", default=str(BOS_ROOT))
    ap.add_argument("--slack", action="store_true", help="Slack-alert on hard failures")
    ap.add_argument("--strict", action="store_true", help="treat warnings as failures")
    ap.add_argument("--quiet", action="store_true", help="print only on problems")
    args = ap.parse_args(argv)

    projects_dir = Path(args.root) / "projects"
    if not projects_dir.is_dir():
        sys.stderr.write(f"ERROR: {projects_dir} not found\n")
        return 3

    all_hard: List[str] = []
    all_warn: List[str] = []
    n_files = 0
    for path in sorted(projects_dir.rglob("*.md")):
        n_files += 1
        hard, warn = lint_file(path, is_toplevel=(path.parent == projects_dir))
        all_hard.extend(hard)
        all_warn.extend(warn)

    if all_hard or not args.quiet:
        print(f"bos_lint: checked {n_files} project file(s) — "
              f"{len(all_hard)} hard error(s), {len(all_warn)} warning(s)")
    for h in all_hard:
        print(f"  ✗ HARD  {h}")
    if all_warn and (all_hard or not args.quiet):
        for w in all_warn:
            print(f"  ⚠ warn  {w}")

    if all_hard and args.slack:
        webhook = os.environ.get("SLACK_WEBHOOK_URL")
        if webhook:
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            lines = [":rotating_light: *BOS schema validation FAILED*",
                     f"_{now}_ — {len(all_hard)} structural error(s) in projects/:", ""]
            lines += [f"• {h}" for h in all_hard]
            lines.append("")
            lines.append("These will break the dashboard/heartbeat reader. Fix the file(s) and re-run "
                         "`automations/reliability/bos_lint.py`.")
            try:
                post_slack(webhook, "\n".join(lines))
            except Exception as e:
                sys.stderr.write(f"(slack post failed: {e})\n")

    if all_hard:
        return 2
    if all_warn and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
