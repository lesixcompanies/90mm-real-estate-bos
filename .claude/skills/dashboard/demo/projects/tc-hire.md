# Transaction Coordinator Hire — P004

Buy back ~6 hours/week of admin so capacity shifts to dollar-productive work — a direct lift on the time constraint.

## IOs (machine-readable)

```yaml
project:
  display_name: Transaction Coordinator Hire
  p_number: P004
  goal: |
    Hand off contract-to-close admin to a part-time transaction coordinator so the
    fixed weekly hours go to listings and clients, not paperwork.
  why: |
    The constraint is hours, not money — the fastest way to lift it is to remove
    low-value work from the calendar entirely.
  tactic: |
    Scope the role, hire a part-time contract TC, and hand off behind a checklist.
  sufficiency_assumption: |
    A scoped role + the right hire + a clean handoff checklist reclaim the hours.
  constraint_interaction: elevate
ios:
  - id: role-scope
    name: Scope the TC role + tasks to offload
    step: elevate
    criticality: supporting
    mode: date-paced
    status: done
    target_date: 2026-06-15
    tactic: List every contract-to-close task; mark which to hand off first.
    sufficiency_assumption: null
    children: []
  - id: hire-tc
    name: Hire + onboard a part-time transaction coordinator
    step: elevate
    criticality: critical
    mode: date-paced
    status: in-progress
    target_date: 2026-07-18
    necessary_assumption: |
      Until someone owns the admin, the hours never actually free up.
    strategy: Hire an experienced contract TC, paid per file, start with one live deal.
    tactic: Post the role, screen three, trial one on the next contract.
    sufficiency_assumption: null
    children: []
  - id: handoff-checklist
    name: Write the contract-to-close handoff checklist
    step: elevate
    criticality: supporting
    mode: date-paced
    status: open
    depends_on:
      - hire-tc
    tactic: Document each step + who owns it so handoff is clean and repeatable.
    sufficiency_assumption: null
    children: []
```
