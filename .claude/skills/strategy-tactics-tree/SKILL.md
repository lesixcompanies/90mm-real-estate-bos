---
name: strategy-tactics-tree
description: >
  Builds the execution sequence for a validated direction. Breaks the
  objective into intermediate objectives, each with a strategy (how)
  and a tactic (specific action). Creates a hierarchical plan where
  each level has a necessary condition that must be true before
  proceeding.
trigger: >
  Use ONLY after the full change sequence is complete through Layer 5:
  CRT (Layers 0-2) → EC (Layer 3) → FRT (Layer 4) → NBR (Layer 5).
  Never build an S&T Tree without validated direction.
---

# Strategy & Tactics Tree (S&T Tree)

## Purpose
Turn the validated direction into an actionable, step-by-step execution
plan. Each step has a clear objective, a strategy for achieving it, and
a specific tactic to execute. Each level has a necessary condition —
something that must be true before that step can begin.

## Structure
The S&T Tree is hierarchical:

```
Objective: [The overall goal from the validated FRT]
├── Intermediate Objective 1: [First milestone]
│   ├── Necessary Condition: [What must be true to start]
│   ├── Strategy: [The approach]
│   └── Tactic: [The specific action]
├── Intermediate Objective 2: [Second milestone]
│   ├── Necessary Condition: [IO1 must be complete + anything else]
│   ├── Strategy: [The approach]
│   └── Tactic: [The specific action]
└── [Continue until the full execution sequence is mapped]
```

## Activation Inventory
Before building the S&T Tree, generate an activation inventory — a
complete list of assets, resources, and prerequisites that must exist
for the execution to work. Present it to the agent as a checklist:

"Before we build the execution plan, let me make sure you have
everything you'll need. Do you have..."

Go through each item:
- Do you have [asset]? (yes / no / partial)
- Do you have access to [resource]? (yes / no)
- Has [prerequisite] been established? (yes / no)

Items they don't have become intermediate objectives in the S&T Tree.

## Process
1. Present the activation inventory and resolve Layer 6
2. Start with the objective from the validated FRT
3. Ask: "What's the first thing that has to happen?"
4. For that first step, define:
   - What has to be true before we can start? (necessary condition)
   - How will we approach this? (strategy)
   - What specifically will we do? (tactic)
5. Confirm each IO with the agent (Layer 7) before moving to the next
6. Continue until the full sequence is mapped
7. Present the complete tree and resolve Layer 8
8. Review the complete tree with the agent:
   "Here's the full sequence. Does every step make sense? Are we
   missing anything? Is the order right?"

## How to Present It
Build it conversationally. Don't dump a full tree on the agent. Walk
through it step by step:

"The objective is to ship the first postcard campaign by May 15. The
first thing that has to happen is [IO1]. To do that, the strategy is
[strategy], and specifically you'd [tactic]. Once that's done, the
next step is [IO2]..."

Let the agent react to each step. They may identify missing steps,
reorder things, or flag concerns (which go back to NBR if they're
Layer 5 concerns, or get addressed as Layer 7 if they're about
implementation details).

## Resistance Layers Addressed

**Layer 6: "Yes, but we can't implement the solution."**
Gate: After activation inventory is presented.
Question: "Looking at this list — is this feasible? Are there items
that feel like real obstacles?"
If obstacles → Each becomes an IO in the tree, or simplify the plan
to minimum viable version. The agent confirms feasibility before
the full tree is built.

**Layer 7: "We disagree on the details of implementation."**
Gate: At each intermediate objective during tree construction.
Question: "Does this step make sense, or would you do it differently?"
If disagreement → Adjust. The tree must reflect how the agent will
actually work, not how the system thinks they should work.

**Layer 8: "The solution is ultimately too risky and not worth it."**
Gate: After the complete tree is built, before execution.
Question: "Here's the full plan — effort, timeline, resources, and
expected return. Is this worth doing?"
If NO → Simplify, defer with a trigger date, or return to the EC for
a lower-risk direction. Never bulldoze into execution the agent
doesn't believe in.

## Output
- The complete S&T Tree with all intermediate objectives, strategies,
  tactics, and necessary conditions
- The activation inventory with status for each item
- Specific dates and deadlines where applicable
- Layers 6, 7, and 8 resolution documented
- Save the S&T Tree to the relevant project folder in projects/
- Create or update undocumented process files as needed

## What Happens Next
Execute. The S&T Tree IS the execution plan. Work through it in order.
Each completed intermediate objective gets logged in the decision log.
When the objective is achieved, the constraint should have shifted —
re-run the CRT to identify the next one and begin the change sequence
again.
