# Listing Conversion System — P002

Turn more listing appointments into signed agreements with a repeatable presentation, so each hard-won appointment is worth more.

## IOs (machine-readable)

```yaml
project:
  display_name: Listing Conversion System
  p_number: P002
  goal: |
    Lift the listing-appointment-to-signed rate by running the same strong
    presentation every time instead of winging it.
  why: |
    Appointments are the scarce input; converting more of them is pure throughput
    with no extra lead spend or hours.
  tactic: |
    A locked listing script + a pre-listing packet + crisp objection responses,
    practiced until they are second nature.
  sufficiency_assumption: |
    Script + packet + objection prep cover the three places appointments are lost.
  constraint_interaction: exploit
ios:
  - id: listing-script
    name: Lock the listing-presentation script
    step: exploit
    criticality: critical
    mode: date-paced
    status: in-progress
    target_date: 2026-07-17
    necessary_assumption: |
      Everything else (packet, objections) hangs off a settled core presentation.
    strategy: Adapt a proven framework to the local market; rehearse to fluency.
    tactic: Draft, run it past a mentor, record one practice run, finalize.
    sufficiency_assumption: null
    children: []
  - id: pre-listing-packet
    name: Build the pre-listing packet
    step: exploit
    criticality: supporting
    mode: date-paced
    status: done
    target_date: 2026-06-10
    tactic: Bio, process, pricing approach, testimonials — one branded PDF.
    sufficiency_assumption: null
    children: []
  - id: objection-guide
    name: Write the top-10 objection responses
    step: exploit
    criticality: supporting
    mode: date-paced
    status: done
    target_date: 2026-06-24
    strategy: Commission, "why not flat-fee," timing, price — scripted and practiced.
    tactic: List the ten, draft a response each, drill the hardest three.
    sufficiency_assumption: null
    children: []
```
