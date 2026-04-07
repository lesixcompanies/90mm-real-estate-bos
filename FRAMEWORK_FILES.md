# Framework Files vs. User Files

This document defines which files belong to the framework (updated by the 90MM team) and which belong to you (created by your diagnostic, never overwritten by updates).

## Framework Files — Updated by 90MM

These files contain the methodology, thinking processes, rules, and infrastructure. When updates are released, these are the files that change. **Do not edit these files** — your edits will be overwritten on the next update.

```
.claude/skills/current-reality-tree/SKILL.md
.claude/skills/evaporating-cloud/SKILL.md
.claude/skills/future-reality-tree/SKILL.md
.claude/skills/negative-branch-reservation/SKILL.md
.claude/skills/strategy-tactics-tree/SKILL.md
.claude/rules/diagnostic-methodology.md
.claude/rules/change-sequence.md
.claude/rules/system-manifest.md
.claude/agents/README.md
.claude/settings.json
templates/session-summary.md
README.md
LICENSE
FRAMEWORK_VERSION
FRAMEWORK_FILES.md
.gitignore
references/industry-crt.md
```

## User Files — Yours, Never Overwritten

These files are created by the deployment prompt during your diagnostic and populated with your specific information. Updates never touch them.

```
CLAUDE.md                          (populated during your diagnostic)
CLAUDE.local.md                    (your local overrides)
.claude/rules/communication-style.md (built from your diagnostic)
.claude/rules/soul.md              (built from your soul diagnostic — Phase A)
context/*                          (all files — your business context)
pipeline/*                         (all files — your pipeline data)
processes/*                        (all files — your process inventory)
diagnostics/*                      (all files — your diagnostic records)
decisions/*                        (all files — your decision log)
projects/*                         (all files — your active projects)
references/*                       (all files — your SOPs and examples)
archives/*                         (all files — your archived material)
templates/weekly-review.md         (created by deployment prompt)
templates/monthly-review.md        (created by deployment prompt)
```

## Mixed Files — Created by You, May Be Extended

```
.claude/skills/*                   (any skills YOU create live here alongside
                                    the framework skills — updates won't touch
                                    skill folders that aren't in the framework
                                    files list above)
.claude/agents/*                   (any sub-agents YOU create live here —
                                    updates only touch README.md)
```

## How Updates Work

See the "Updating" section in README.md for the step-by-step process.
