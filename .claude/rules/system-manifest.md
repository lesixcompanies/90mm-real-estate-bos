# System Manifest

*Read this file first on every session. It tells you where everything is and what each file contains — without you having to read every file. Only read the specific files relevant to the current task.*

*Update this manifest whenever a file is created or significantly modified.*

*Pruning discipline: this file loads in FULL every session, so its size is a per-session token cost paid forever. Keep it lean — (1) route deep reference detail DOWN to an on-demand file behind a one-line pointer rather than letting a section grow unbounded here, and (2) prune by "still live-referenced?" — when a file is deleted or decommissioned, remove its row; don't just append.*

---

## Rules and Behavior
| File | Contains |
|------|----------|
| .claude/rules/soul.md | How to communicate with this person — emotional texture, hard truth delivery, decision support style, non-negotiables |
| .claude/rules/communication-style.md | Formatting, vocabulary, tone, pacing preferences |
| .claude/rules/diagnostic-methodology.md | How constraint-based diagnostics work — four dimensions, core principles |
| .claude/rules/change-sequence.md | Full change sequence with 9 layers of legitimate resistance — when to use each thinking process, decision logging rubric |
| .claude/rules/system-manifest.md | This file — index of everything in the system |
| .claude/rules/plan-format.md | Standing rule — every plan-mode plan uses the six-part TOC change-sequence structure (UDEs → Root Cause/CRT → Problematic Assumption/EC → Injections/FRT → Risks & Countermeasures/NBR → Plan of Action/S&TT). Governs the format of the plan file itself. |
| .claude/rules/memory-architecture.md | Recording facts with integrity — two disciplines for how facts get written into BOS files: extract-don't-summarize (no lossy paraphrase) and temporal validity (`valid-as-of` tags + supersede-don't-overwrite on volatile facts like prices/dates/statuses). |

## Thinking Process Skills
| File | Contains |
|------|----------|
| .claude/skills/current-reality-tree/SKILL.md | CRT skill — diagnostic tool, surfaces root cause, addresses Layers 0-2 |
| .claude/skills/evaporating-cloud/SKILL.md | EC skill — surfaces underlying conflict and assumptions, addresses Layer 3 |
| .claude/skills/future-reality-tree/SKILL.md | FRT skill — tests proposed direction with real numbers, addresses Layer 4 |
| .claude/skills/negative-branch-reservation/SKILL.md | NBR skill — tests for unintended consequences, addresses Layer 5 |
| .claude/skills/strategy-tactics-tree/SKILL.md | S&T Tree skill — builds execution plan with activation inventory, addresses Layers 6-8 |

## Execution Skills
| File | Contains |
|------|----------|
| .claude/skills/dashboard/SKILL.md | Generates a self-contained static `dashboard.html` from your BOS markdown — bottleneck-first (your constraint + health badge + the 3-4 objectives that move it on top, full project S&T trees collapsed below). No server, no credentials, opens offline. Bundles `generate.py` (the generator, with per-file degradation), `bos_lint.py` (project-file schema validator), and a fictional demo BOS. Needs PyYAML. Run `/dashboard`. |
| .claude/skills/heartbeat/SKILL.md | Deterministic, silent-by-default daily "what needs you" surface. Reads BOS state (overdue/due-soon IOs, aging queue, malformed files, stale decision log) and writes one brief to `inbox/desk-queue.md`; NEVER acts. Runs automatically via the SessionStart hook in `.claude/settings.json` (once/day). Optional cron + Slack documented in its SKILL.md. |

## Sub-Agents
| File | Contains |
|------|----------|
| .claude/agents/README.md | Documentation on creating sub-agents, model routing, MCP connections |
| .claude/agents/critic.md | Framework agent. Clean-context adversarial reviewer (read-only, Opus). Roasts a plan/offer/project/decision through the user's own constraint + soul.md via the TOC lens. Fires on explicit critique intent only ("roast this," "pressure-test this"), never proactively. Invocable by name. |

## Context — About the Person and Business
<!-- Populated during diagnostic. Update entries as files are created. -->
| File | Contains |
|------|----------|
| context/me.md | *Not yet populated* |
| context/business.md | *Not yet populated* |
| context/current-priorities.md | *Not yet populated* |
| context/goals.md | *Not yet populated* |
| context/constraints.md | *Not yet populated* |

## Pipeline
<!-- Populated during diagnostic. Structure depends on business type. -->
| File | Contains |
|------|----------|
| pipeline/pipeline.md | *Not yet populated — structure determined during diagnostic* |

## Diagnostics
| File | Contains |
|------|----------|
| diagnostics/ | *Empty until first diagnostic completes* |

## Processes
| File | Contains |
|------|----------|
| processes/documented/ | *Empty — processes move here as they are formalized* |
| processes/undocumented/ | *Empty until diagnostic identifies process gaps* |

## Decisions
| File | Contains |
|------|----------|
| decisions/log.md | Append-only decision log — every decision traced to constraint |

## Templates
| File | Contains |
|------|----------|
| templates/session-summary.md | End-of-session closeout with constraint impact and change sequence tracking |
| templates/weekly-review.md | *Created by deployment prompt — business-specific metrics* |
| templates/monthly-review.md | *Created by deployment prompt — business-specific metrics* |

## References
| File | Contains |
|------|----------|
| references/industry-crt.md | Real estate industry Current Reality Tree — causal logic for diagnostic questions (use when business connects to real estate) |

## Projects
| File | Contains |
|------|----------|
| projects/ | *Empty until S&T Tree creates project folders* |

## Archives
| File | Contains |
|------|----------|
| archives/ | *Empty — completed/outdated material moves here with date prefix* |

---

*When reading this manifest to decide which files to load: match the person's request to the "Contains" column. Load only what's relevant. If in doubt, load context/constraints.md and context/current-priorities.md — those are almost always relevant.*
