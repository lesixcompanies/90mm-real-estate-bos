# Cedar Glen Geo-Farm — P001

Own the listing flow in one 900-home neighborhood through consistent, low-cost presence — the highest throughput-per-hour lead source available.

## IOs (machine-readable)

```yaml
project:
  display_name: Cedar Glen Geo-Farm
  p_number: P001
  goal: |
    Become the obvious agent in Cedar Glen so listings come inbound, by showing up
    consistently (mail + events) instead of chasing leads one at a time.
  why: |
    A single farmed neighborhood is the cheapest repeatable listing source per hour
    once the routine is set — it compounds and respects the time boundary.
  tactic: |
    Six postcards and three neighborhood events a year on a fixed calendar, mailed
    to a clean 900-home list, with every piece pointing to one offer.
  sufficiency_assumption: |
    A clean list + a fixed calendar + one consistent offer are enough to build
    top-of-mind presence; the IOs below set those up.
  constraint_interaction: exploit
ios:
  - id: mailing-list
    name: Build + clean the 900-home mailing list
    step: exploit
    criticality: critical
    mode: date-paced
    status: done
    target_date: 2026-05-20
    tactic: County records + a skip-trace pass; dedupe against past clients.
    sufficiency_assumption: null
    children: []
  - id: june-postcard
    name: Mail the July farm postcard (900 homes)
    step: exploit
    criticality: critical
    mode: date-paced
    status: in-progress
    target_date: 2026-07-13
    necessary_assumption: |
      Consistency is the whole strategy — a skipped month resets the compounding.
    strategy: Just-sold angle with a free home-value offer; print vendor on file.
    tactic: Approve proof, send to the mail house, confirm in-home date.
    sufficiency_assumption: null
    children: []
  - id: summer-event
    name: Host the summer block party
    step: exploit
    criticality: supporting
    mode: date-paced
    status: open
    target_date: 2026-07-20
    strategy: Ice cream truck + sign-in for the list; low cost, high face time.
    tactic: Book the truck, flyer the street, set up the sign-in tablet.
    sufficiency_assumption: null
    children: []
  - id: content-calendar
    name: Map the 12-month postcard + event calendar
    step: exploit
    criticality: supporting
    mode: date-paced
    status: open
    tactic: "One page — six mail dates, three events, the offer for each."
    sufficiency_assumption: null
    children: []
```
