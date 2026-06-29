---
name: heartbeat
description: >
  Your BOS's daily "what needs you" surface. A deterministic, silent-by-default
  check that reads your BOS state and writes one brief to inbox/desk-queue.md when
  something needs attention — overdue objectives, due-soon critical work, aging
  queue items, malformed project files, a stale decision log. It NEVER acts; it
  only reads your files and writes the queue. Ships wired into a SessionStart hook
  so it runs automatically once a day. Use when the user asks to "run the
  heartbeat", "what needs me", or wants the morning brief on demand.
---

# Heartbeat Skill

The BOS is good at holding state, but by default it's *pull* — you have to go look.
The heartbeat makes it *push*: once a day it tells you what needs you, so nothing
quietly slips.

It is **deterministic** (every signal is a date, a count, or a status — no LLM,
nothing to hallucinate) and **silent-by-default** (on a clean day it writes
nothing). It **never acts** — it only reads your markdown and writes the queue.

## It's automatic — no setup

This skill ships wired into a **SessionStart hook** (`.claude/settings.json`). The
first time you open Claude Code each day, the heartbeat runs itself, refreshes
`inbox/desk-queue.md`, and surfaces "you have N items waiting" at the top of the
session. No cron, no configuration, works wherever Claude Code runs.

## What it surfaces

- **Overdue objectives** — open IOs past their target date
- **Due soon (critical)** — critical IOs within 7 days of target
- **Aging queue** — items open in `inbox/desk-queue.md` for 7+ days
- **Schema** — project files the dashboard reader had to skip (malformed)
- **Decision log** — no decision logged in 14+ days

It owns exactly one `## [open] … — from Heartbeat` block in the queue: each run
replaces yesterday's, and clears it entirely on a silent day. It never touches
items you (or anything else) put there.

## Run it on demand

```
python3 .claude/skills/heartbeat/heartbeat.py --dry-run   # preview, writes nothing
python3 .claude/skills/heartbeat/heartbeat.py             # write the brief now
```

(It reuses the dashboard skill's reader, so it needs **PyYAML** — `pip install
pyyaml`. If PyYAML isn't installed, the hook silently does nothing rather than
breaking your session.)

## Optional: a scheduled morning brief (cron)

The SessionStart hook covers most people. If you want a brief that lands every
morning whether or not you open the editor, add a cron job (macOS/Linux):

```
# 7am on weekdays — never weekends/evenings
0 7 * * 1-5 cd /path/to/your/bos && python3 .claude/skills/heartbeat/heartbeat.py
```

## Optional: a Slack ping

Copy `.env.example` to `.env` in this folder and set `SLACK_WEBHOOK_URL` to a
personal channel. The desk-queue is always the primary surface; Slack is just an
extra nudge. Point it at your own channel — it can fire daily.

## Discipline (do not weaken)

Silent-by-default and never-acts are the whole point. A heartbeat that chatters
gets muted; one that takes actions can't be trusted to run unattended. Keep it
reading-and-surfacing only.
