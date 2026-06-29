# Database Reactivation — P003

Keep past clients and sphere warm so referrals stay steady — protecting the lead pipeline without adding spend or hours.

## IOs (machine-readable)

```yaml
project:
  display_name: Database Reactivation
  p_number: P003
  goal: |
    Turn a cold contact list into a steady referral stream with light, consistent
    touches that run mostly on autopilot.
  why: |
    Referrals are the lowest-cost, highest-trust lead source; neglecting the
    database quietly starves the pipeline.
  tactic: |
    A cleaned CRM + a monthly market-update email + a quarterly personal call list.
  sufficiency_assumption: |
    Clean data + one automated touch + one personal touch keep the base warm.
  constraint_interaction: subordinate
ios:
  - id: crm-cleanup
    name: Clean + tag the CRM (past clients, sphere, leads)
    step: subordinate
    criticality: supporting
    mode: date-paced
    status: done
    target_date: 2026-06-05
    tactic: Merge duplicates, tag by relationship, fix missing emails.
    sufficiency_assumption: null
    children: []
  - id: monthly-email
    name: Ship the first monthly market-update email
    step: subordinate
    criticality: supporting
    mode: date-paced
    status: open
    target_date: 2026-07-14
    strategy: One simple template — three local stats + one personal note.
    tactic: Build the template, schedule it, send to the tagged list.
    sufficiency_assumption: null
    children: []
  - id: call-list
    name: Build the quarterly personal-call list
    step: subordinate
    criticality: parallel
    mode: date-paced
    status: open
    tactic: Top 50 by referral likelihood; 10 calls a week.
    sufficiency_assumption: null
    children: []
```
