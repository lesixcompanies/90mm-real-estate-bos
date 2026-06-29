# Website + IDX Setup — P000

## IOs (machine-readable)

```yaml
project:
  display_name: Website + IDX Setup
  p_number: P000
  archived_date: 2026-04-30
  archived_summary: |
    Stood up a branded agent site with IDX home search and a single lead-capture
    offer. Closed once it was live and feeding the CRM — ongoing tweaks happen
    inside the database project, not as a standalone build.
  constraint_interaction: exploit
ios:
  - id: site-live
    name: Launch the branded site + IDX search
    step: exploit
    criticality: supporting
    mode: date-paced
    status: done
    target_date: 2026-04-28
    tactic: Template site, connect IDX feed, wire the capture form to the CRM.
    sufficiency_assumption: null
    children: []
```
