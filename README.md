# 90-Minute Marketing Department: Business Operating System

A diagnostic-driven business operating system built on the Theory of Constraints Thinking Processes.

**Repository:** https://github.com/lesixcompanies/90mm-real-estate-bos
**License:** GNU General Public License v3.0

## What This Is

A universal methodology framework for identifying business constraints, validating the right direction for change, and building concrete execution plans. Built on TOC Thinking Processes and designed for deployment through Claude Code, Cowork, or Claude.ai Projects.

This repository contains the **methodology layer** — the thinking process skills, the change sequence, and the diagnostic framework. It does not contain audience-specific context structures, pipeline files, or review templates. Those are created by audience-specific **deployment prompts** that reference this repo.

## Who This Is For

This framework serves four audiences in the real estate industry. Each uses a dedicated deployment prompt that creates the appropriate context and pipeline structure:

- **Agents** — Identify what's limiting your practice. Build repeatable processes. Stop winging it.
- **Brokers** — Build systems for agent recruitment, retention, and development beyond transaction oversight.
- **Schools** — Connect curriculum to actual business outcomes. Break the CE irrelevance cycle.
- **Associations** — Drive member engagement through demonstrated professional development value.

## The Methodology

### The Three Questions
1. **What to change?** — Current Reality Tree identifies the core constraint.
2. **What to change to?** — Evaporating Cloud, Future Reality Tree, and Negative Branch Reservations validate the direction.
3. **How to make change happen?** — Strategy & Tactics Tree builds the execution plan.

### Nine Layers of Legitimate Resistance
Every transition between thinking processes is gated by layers of legitimate resistance (0-8) that must be resolved in order before advancing. The system never skips steps and never jumps to execution without validated direction. See `.claude/rules/change-sequence.md` for full definitions.

### Five Pre-Built Thinking Process Skills
Each skill includes trigger conditions, process steps, resistance layer mappings, conversational presentation guidance, and what happens next:

| Skill | Question Answered | Layers Addressed |
|-------|-------------------|------------------|
| Current Reality Tree | What to change? | 0, 1, 2 |
| Evaporating Cloud | What to change? | 3 |
| Future Reality Tree | What to change to? | 4 |
| Negative Branch Reservation | What to change to? | 5 |
| Strategy & Tactics Tree | How to make change happen? | 6, 7, 8 |

## How to Use It

### Prerequisites
- Claude Code installed in VS Code, Cursor, or Antigravity (OR Claude Cowork OR Claude.ai Projects)
- A paid Claude subscription
- The deployment prompt for your audience

### Setup
1. Clone this repository into your project folder:
   ```
   git clone https://github.com/lesixcompanies/90mm-real-estate-bos.git .
   ```
2. Open the folder in your IDE
3. Open Claude Code
4. Paste your audience-specific deployment prompt
5. Answer the diagnostic questions honestly — the system builds itself around your answers

### Deployment Prompt
One master deployment prompt works for all audiences. The diagnostic determines what kind of business you run — you don't need to choose in advance.

- **Master Deployment Prompt** — [Available at course page](https://community.lesix.agency/courses/offers/1d8eaa8e-b338-4106-940b-b6e9236439cb)

## Repository Structure

```
├── .claude/
│   ├── rules/
│   │   ├── diagnostic-methodology.md    # How constraint-based diagnostics work
│   │   ├── change-sequence.md           # Full change sequence with 9 resistance layers + decision logging rubric
│   │   ├── communication-style.md       # Template — populated during diagnostic
│   │   ├── soul.md                      # Template — emotional/relational communication layer, built in Phase A
│   │   └── system-manifest.md           # Lightweight index of every file — read first each session
│   ├── skills/
│   │   ├── current-reality-tree/        # CRT skill
│   │   ├── evaporating-cloud/           # EC skill
│   │   ├── future-reality-tree/         # FRT skill
│   │   ├── negative-branch-reservation/ # NBR skill
│   │   └── strategy-tactics-tree/       # S&T Tree skill
│   ├── agents/
│   │   └── README.md                    # Sub-agent documentation and examples
│   └── settings.json
├── context/                             # Audience-specific — created by deployment prompt
├── pipeline/                            # Audience-specific — created by deployment prompt
├── processes/
│   ├── documented/                      # Completed process documentation
│   └── undocumented/                    # Process gaps identified during diagnostic
├── diagnostics/                         # Diagnostic records and change sequence documentation
├── templates/
│   └── session-summary.md              # Universal session closeout template
├── references/
│   ├── industry-crt.md                  # Industry-level Current Reality Tree — diagnostic foundation
│   ├── sops/                            # Standard operating procedures
│   └── examples/                        # Example outputs and style guides
├── projects/                            # Active initiatives
├── decisions/
│   └── log.md                          # Append-only decision log
├── archives/                            # Completed or outdated material
├── CLAUDE.md                           # Main brain file — template, populated by deployment prompt
├── CLAUDE.local.md                     # Local overrides (git-ignored)
├── FRAMEWORK_VERSION                   # Current framework version number
├── FRAMEWORK_FILES.md                  # Which files are framework vs. user-generated
├── LICENSE                             # GNU General Public License v3.0
└── README.md                           # This file
```

## Sub-Agents and External Tools

The system supports sub-agents that run on different models (Haiku for cheap research, Sonnet for balanced work, Opus for complex reasoning) and external tool connections via MCP servers (Perplexity for web research, Google Workspace, CRM systems, etc.).

See `.claude/agents/README.md` for full documentation on creating sub-agents, connecting external services, and model routing strategies.

## Updating the Framework

The framework (thinking process skills, rules, templates, agents documentation) will be updated over time. Your personal data (context files, pipeline, processes, diagnostics, decisions) is never touched by updates. See `FRAMEWORK_FILES.md` for the complete list of which files are which.

### First Time Setup (One Time Only)

After you've cloned the repo and run the diagnostic, set up the upstream remote so you can pull future updates:

```
git remote add upstream https://github.com/lesixcompanies/90mm-real-estate-bos.git
```

### When an Update is Available

Check the current framework version:
```
cat FRAMEWORK_VERSION
```

Pull only the framework files — this **never touches** your context, pipeline, processes, diagnostics, decisions, projects, or CLAUDE.md:

```
git fetch upstream
git checkout upstream/main -- .claude/skills/ .claude/rules/diagnostic-methodology.md .claude/rules/change-sequence.md .claude/rules/system-manifest.md .claude/agents/README.md .claude/settings.json templates/session-summary.md references/industry-crt.md README.md LICENSE FRAMEWORK_VERSION FRAMEWORK_FILES.md .gitignore
git add -A
git commit -m "Updated framework to v[NEW VERSION]"
```

That's it. Your diagnostic data, your context files, your custom skills, your custom sub-agents, your populated CLAUDE.md — all untouched. Only the methodology files get updated.

### What If You Want to Start Over

If you want to re-run the diagnostic from scratch (fresh start, same framework):

```
git fetch upstream
git checkout upstream/main -- .
git add -A
git commit -m "Reset to framework v[VERSION] — ready for fresh diagnostic"
```

This resets everything to the clean template state. You'll need to run the deployment prompt again.

### Or Just Ask Claude Code

If you're in a Claude Code session, you can simply say: "Update the base framework from the upstream repository." Claude Code can run the git commands for you.

## What's NOT Included

This repository is the methodology framework. It does not contain:
- Pre-built execution skills (content creation, CRM integration, MLS research, etc.)
- API integrations or MCP server configurations
- Marketing templates, brand assets, or scripts
- Audience-specific context structures (created by deployment prompts)

Execution skills are built organically as the S&T Tree identifies what's needed, or through the [90-Minute Marketing Department](https://community.lesix.agency/courses/offers/1d8eaa8e-b338-4106-940b-b6e9236439cb) guided implementation program.

## Version History

- **v2.0** — Single master deployment prompt replaces five audience-specific prompts. Two-phase diagnostic: soul builder (Phase A) + business diagnostic (Phase B). Added soul.md personality layer. Added system-manifest.md for token-efficient file routing. Added decision logging rubric with automatic triggers. Updated CLAUDE.md template.
- **v1.2** — Added industry-level Current Reality Tree as reference document. All deployment prompts updated with real URLs, measurement baseline capture, voice pathway (Wispr Flow), and CRT reference instructions.
- **v1.1** — Added sub-agents directory with documentation and examples. Added framework update mechanism (FRAMEWORK_VERSION, FRAMEWORK_FILES.md, upstream pull instructions).
- **v1.0** — Initial release. Universal methodology framework with five thinking process skills, change sequence with layers 0-8, diagnostic framework.

## About

The Theory of Constraints was developed by Dr. Eli Goldratt. This framework applies TOC Thinking Processes to real estate professional development — agents, brokers, schools, and associations.

Developed by [Lesix Companies](https://lesix.agency) as part of the 90-Minute Marketing Department framework.

- **Guided implementation and pre-built execution skills:** [90MM Course](https://community.lesix.agency/courses/offers/1d8eaa8e-b338-4106-940b-b6e9236439cb)
- **One-on-one diagnostic consulting:** [90MM Coaching](https://lesix.agency/general)
- **Community and office hours:** [90MM Community](https://community.lesix.agency/communities/groups/90-minute-marketing-department/home)

## License

Copyright (c) 2026 Lesix Companies

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

See [LICENSE](LICENSE) for full terms.
