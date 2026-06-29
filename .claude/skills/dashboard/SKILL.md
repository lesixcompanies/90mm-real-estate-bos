---
name: dashboard
description: >
  Generates a self-contained static dashboard.html for this BOS — a
  bottleneck-first view: your system constraint + a health badge and the 3-4
  big-ticket objectives that move it on top, with the Five Focusing Steps, full
  per-project S&T trees, and history collapsed below (progressive disclosure).
  Derived entirely from your BOS markdown with no server, no credentials, and no
  external dependencies. Use when the user asks to "generate / refresh / open the
  dashboard", wants a snapshot of where their operating system stands, or runs
  /dashboard. It is a point-in-time snapshot — re-run it to get the current
  picture.
---

# Dashboard Skill

Produces one self-contained `dashboard.html` at the BOS root that you open in a
browser. Zero infrastructure: a Python script reads your BOS markdown and writes
a single HTML file with all CSS/JS inlined. No server, no credentials, no CDN, no
accounts. It is a **snapshot** — regenerate whenever you want the current state.

This is the *structural* view of your operating system, derived entirely from the
files you already have. Live-metrics panels (social, analytics, payments) are
intentionally out of scope — they need integrations and credentials a static,
shippable dashboard can't carry.

## What it renders

**Top (always visible):**
- **Your Bottleneck** — your system constraint in plain words + a GREEN/YELLOW/RED
  **Bottleneck Health** badge (the overall verdict). Degrades to a "run the
  diagnostic" prompt if no constraint is defined yet.
- **What Moves Your Bottleneck Now** — the **3–4 big-ticket intermediate
  objectives (IOs)** that most move the bottleneck right now, each with a
  **Resolve** (exploit/subordinate) or **Elevate** chip, its project link,
  target/countdown, and a plain-language why-it's-here line.

**Collapsed below (progressive disclosure):**
- **The Five Focusing Steps** — Identify + Exploit/Subordinate/Elevate project
  attention + Re-evaluate posture.
- **Projects — full S&T trees** — per project, the Level-1 mini-dashboard
  (Purpose / Why / Tactic / Sufficiency / constraint interaction + verdict) and
  the Level 2–n IO tree (Open / Closed, five S&T fields, targets, dependencies).
- **History & cadence** — recent decisions, re-evaluation cadence, drag indicator.
- **Archived projects** — date-sorted list with summaries.

### The priority rubric (how the 3–4 items are chosen)

Pure TOC-signal ranking over the **open frontier** (open IOs with no open
children, so the concrete next objective surfaces — not a parent): (1) does its
project act on the constraint (`constraint_interaction` tagged) > untagged; then
(2) criticality (critical > supporting/parallel); then (3) date-paced urgency
(red > yellow > green > grey); tiebreak earliest target date. Top 4. No new
scoring model — it surfaces the top of what your system already knows.

## How to run it

From the BOS root:

```
python3 .claude/skills/dashboard/generate.py
```

It writes `dashboard.html` at the BOS root and prints a one-line summary (project
count, decision count, any skipped files). Then tell the user:

> Open `dashboard.html` in your browser. Re-run `/dashboard` any time to refresh
> the snapshot.

### Options

- `--root /path/to/bos` — explicit BOS root (default: auto-detected by walking up
  from the current directory to the folder holding `CLAUDE.md` + `projects/`).
- `--out path.html` — explicit output path (default: `<root>/dashboard.html`).
- `--print` — also echo the output path.

### Dependency

The generator needs **PyYAML** (`pip install pyyaml`). The *output* HTML has no
dependencies at all. If the run fails with a PyYAML import error, install it and
re-run (`python3 -m pip install pyyaml`).

## Validate your project files (bundled)

`bos_lint.py` checks every `projects/*.md` IO block against the schema, so a typo
never silently breaks the dashboard:

```
python3 .claude/skills/dashboard/bos_lint.py
```

It is tolerant by design: it **hard-fails only on structural breakage** (YAML that
won't parse, a malformed IO tree, a missing `id`/`name`) and merely **warns** on
minor enum drift. Run it after editing a project file, or wire it into a pre-commit
check. Exit codes: 0 clean, 1 warnings, 2 hard failures.

## Try it on the bundled demo

A complete fictional example BOS ships at `.claude/skills/dashboard/demo/` so you
can see a populated dashboard before filling in your own:

```
python3 .claude/skills/dashboard/generate.py --root .claude/skills/dashboard/demo --out demo.html
```

## Robustness contract (do not weaken)

The reader **degrades per file**. A project file with broken YAML or a malformed
IO tree is skipped with a visible warning at the top of the dashboard; the rest of
your BOS still renders. Never let one bad file take the whole page down. Minor enum
drift (an off-spec `status` or `criticality` value) is tolerated and rendered
leniently rather than skipped. If the generator reports skipped files, relay the
warnings so the user can fix the offending file and regenerate.

## Architecture (for maintainers)

`generate.py` is one self-contained file in three sections: a **reader**
(markdown → typed data model, with the per-file degradation contract above), a
**renderer** (data model → one inlined HTML string), and a **CLI**. Keep it a
single dependency-light file (stdlib + PyYAML) so it stays runnable by a
non-technical user with no infrastructure.
