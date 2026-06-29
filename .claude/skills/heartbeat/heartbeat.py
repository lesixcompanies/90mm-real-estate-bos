#!/usr/bin/env python3
"""Bounded proactive heartbeat — your BOS's daily "what needs you" surface.

DETERMINISTIC and SILENT-BY-DEFAULT. Once a day it reads your BOS state and
either stays completely silent (nothing actionable) or writes ONE brief to
inbox/desk-queue.md. It NEVER acts — it only reads your files and writes the
queue. There is no LLM and nothing to hallucinate: every signal is a date, a
count, or a status the system already knows.

Signals:
  - overdue open IOs and due-soon CRITICAL IOs (via the dashboard reader)
  - malformed project files the reader had to skip (schema warnings)
  - aging desk-queue items (open > 7 days, excluding the heartbeat's own block)
  - decision-log staleness (no decision logged in 14+ days)

How it becomes "a regular thing": this ships wired into a SessionStart hook
(.claude/settings.json), so the FIRST time you open Claude Code each day it runs
itself and refreshes the queue, then surfaces "you have N items waiting" at the
top of the session. No cron, no setup, works wherever Claude Code runs. (An
optional cron for a scheduled morning brief is documented in SKILL.md.)

Desk-queue discipline: the heartbeat owns exactly ONE open block tagged
"— from Heartbeat". Each run replaces its prior block (today's snapshot
supersedes yesterday's) and clears it entirely on a silent day. It never touches
items you or anything else put in the queue.

Usage:
    heartbeat.py --session-start   # hook mode: once/day run + surface the count
    heartbeat.py --dry-run         # print the brief; write nothing
    heartbeat.py                   # write the brief to inbox/desk-queue.md
    heartbeat.py --root /path
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

# Import the dashboard skill's markdown reader (sibling skill) so the heartbeat
# and the dashboard see the BOS identically.
_DASH = Path(__file__).resolve().parent.parent / "dashboard"
sys.path.insert(0, str(_DASH))
try:
    import generate as dash  # read_bos, flatten_ios, compute_io_status, find_bos_root, ...
except Exception as e:  # pragma: no cover - surfaced to the user, never fatal to a session
    sys.stderr.write(f"heartbeat: could not load the dashboard reader ({e})\n")
    dash = None

DECISION_GAP_DAYS = 14
QUEUE_AGE_DAYS = 7
MAX_OVERDUE_LISTED = 8

Signal = Tuple[str, str]
_QUEUE_OPEN_RE = re.compile(r"^## \[open\]\s+(\d{4}-\d{2}-\d{2})[^\n]*$", re.MULTILINE)
_HEARTBEAT_BLOCK_RE = re.compile(
    r"\n## \[open\][^\n]*— from Heartbeat\b.*?(?=\n## |\Z)", re.DOTALL)

_QUEUE_HEADER = """# Desk Queue

Items that need your attention. The heartbeat appends a daily brief here; you can
add your own `## [open] YYYY-MM-DD — from <name>` blocks too. Mark an item `[done]`
once handled.
"""


def _gather(root: Path) -> List[Signal]:
    today = date.today()
    sig: List[Signal] = []
    if dash is None:
        return sig
    state = dash.read_bos(root)

    overdue: List[Tuple[int, str]] = []
    duesoon: List[Tuple[int, str]] = []
    for proj in state.projects:
        for io in dash.flatten_ios(proj.tree):
            if io.status not in dash.OPEN_STATUSES or not io.target_date:
                continue
            days = (io.target_date - today).days
            st = dash.compute_io_status(io, today)
            if st.color == dash.RED and days < 0:
                overdue.append((days, f"{proj.meta.display_name}: “{io.name}” {-days}d overdue"))
            elif st.color == dash.YELLOW and io.criticality == "critical" and days >= 0:
                duesoon.append((days, f"{proj.meta.display_name}: critical “{io.name}” due in {days}d"))
    for _, text in sorted(overdue)[:MAX_OVERDUE_LISTED]:
        sig.append(("overdue IO", text))
    if len(overdue) > MAX_OVERDUE_LISTED:
        sig.append(("overdue IO", f"…and {len(overdue) - MAX_OVERDUE_LISTED} more overdue"))
    for _, text in sorted(duesoon):
        sig.append(("due soon", text))

    for w in state.warnings:
        sig.append(("schema", w))

    for d, line in _open_queue_items(root):
        if "from Heartbeat" in line:
            continue
        age = (today - d).days
        if age >= QUEUE_AGE_DAYS:
            sig.append(("aging queue", f"{age}d old: {line.strip()}"))

    if state.decisions:
        last = max(dd.date for dd in state.decisions)
        gap = (today - last).days
        if gap >= DECISION_GAP_DAYS:
            sig.append(("decisions", f"no decision logged in {gap} days (last {last.isoformat()})"))
    return sig


def _open_queue_items(root: Path) -> List[Tuple[date, str]]:
    q = root / "inbox" / "desk-queue.md"
    if not q.exists():
        return []
    out = []
    for m in _QUEUE_OPEN_RE.finditer(q.read_text(encoding="utf-8", errors="replace")):
        try:
            out.append((datetime.strptime(m.group(1), "%Y-%m-%d").date(), m.group(0)))
        except ValueError:
            continue
    return out


def _compose(sig: List[Signal], now: datetime) -> str:
    order = ["schema", "overdue IO", "due soon", "aging queue", "decisions"]
    label = {"schema": "⚠ Schema", "overdue IO": "⏰ Overdue objectives",
             "due soon": "\U0001f4c5 Due soon (critical)", "aging queue": "\U0001f4e5 Aging queue",
             "decisions": "\U0001f4dd Decision log"}
    by_cat = {}
    for cat, text in sig:
        by_cat.setdefault(cat, []).append(text)
    lines = [f"## [open] {now:%Y-%m-%d %H:%M} — from Heartbeat",
             "**Action:** Review what the system flagged today (auto-surfaced; nothing was acted on).",
             ""]
    for cat in order:
        items = by_cat.get(cat)
        if not items:
            continue
        lines.append(f"**{label.get(cat, cat)}:**")
        lines += [f"- {t}" for t in items]
        lines.append("")
    lines.append("**Source:** Heartbeat")
    return "\n".join(lines)


def _write_queue(root: Path, brief: Optional[str]) -> None:
    q = root / "inbox" / "desk-queue.md"
    q.parent.mkdir(parents=True, exist_ok=True)
    text = q.read_text(encoding="utf-8", errors="replace") if q.exists() else _QUEUE_HEADER
    text = _HEARTBEAT_BLOCK_RE.sub("", text).rstrip()
    if brief:
        text = text + "\n\n" + brief + "\n"
    else:
        text = text + "\n"
    q.write_text(text, encoding="utf-8")


def _open_count(root: Path) -> int:
    return len(_open_queue_items(root))


def _stamp_path(root: Path) -> Path:
    return root / "inbox" / ".heartbeat-stamp"


def _ran_today(root: Path) -> bool:
    p = _stamp_path(root)
    try:
        return p.read_text().strip() == date.today().isoformat()
    except OSError:
        return False


def _set_stamp(root: Path) -> None:
    p = _stamp_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        p.write_text(date.today().isoformat())
    except OSError:
        pass


def _post_slack_optional(n: int, now: datetime) -> None:
    env = Path(__file__).resolve().parent / ".env"
    webhook = None
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line.startswith("SLACK_WEBHOOK_URL=") and len(line) > len("SLACK_WEBHOOK_URL="):
                webhook = line.split("=", 1)[1].strip()
    if not webhook:
        return
    import urllib.request
    text = f":sunrise: Heartbeat — {n} item(s) need you. See inbox/desk-queue.md."
    try:
        req = urllib.request.Request(webhook, data=json.dumps({"text": text}).encode(),
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=15).read()
    except Exception:
        pass


def _run(root: Path) -> int:
    """Full scan: write or clear the queue. Returns the signal count."""
    sig = _gather(root)
    now = datetime.now()
    _write_queue(root, _compose(sig, now) if sig else None)
    if sig:
        _post_slack_optional(len(sig), now)
    return len(sig)


def _emit_session_context(root: Path) -> None:
    """Print SessionStart additionalContext JSON if the queue has open items."""
    n = _open_count(root)
    if n <= 0:
        return
    ctx = (f"\U0001f4e5 You have {n} open item(s) in inbox/desk-queue.md "
           f"(the heartbeat surfaces overdue objectives, due-soon work, and aging queue "
           f"items). Read that file and address or clear each one.")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                              "additionalContext": ctx}}))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Bounded proactive heartbeat")
    ap.add_argument("--root", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--session-start", action="store_true",
                    help="hook mode: once/day full run + surface the open-item count; always exit 0")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve() if args.root else (
        dash.find_bos_root() if dash else Path.cwd())

    # Hook mode never fails a session.
    if args.session_start:
        try:
            if not _ran_today(root):
                _run(root)
                _set_stamp(root)
            _emit_session_context(root)
        except Exception:
            pass
        return 0

    if args.dry_run:
        sig = _gather(root)
        now = datetime.now()
        if not sig:
            print(f"[{now:%Y-%m-%d %H:%M}] heartbeat: nothing actionable — silent.")
        else:
            print(f"[{now:%Y-%m-%d %H:%M}] heartbeat: {len(sig)} signal(s) — WOULD write:\n")
            print(_compose(sig, now))
        return 0

    n = _run(root)
    _set_stamp(root)
    now = datetime.now()
    if n:
        print(f"[{now:%Y-%m-%d %H:%M}] heartbeat: wrote {n} signal(s) to inbox/desk-queue.md")
    else:
        print(f"[{now:%Y-%m-%d %H:%M}] heartbeat: silent (nothing actionable).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
