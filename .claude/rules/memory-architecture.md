# Memory Architecture — recording facts with integrity

*Your BOS is a file-based memory: context, projects, decisions, and references
are the system's long-term store. How facts get written into those files
determines whether the system can be trusted months later. Two disciplines keep
that memory honest.*

## 1. Extract, don't summarize

When you record or compact a fact, store the **discrete fact or decision**, not a
narrative paraphrase of it.

Summarizing is lossy and invites quiet drift: a paraphrase a few generations deep
can assert something the source never said, with full confidence. Keep the
load-bearing specifics — the numbers, names, dates, and the actual decision — and
cut only the connective prose. If you can't preserve a fact exactly, keep it
verbatim rather than rewording it.

> Write: *"Listing fee set at 2.25% (decided 2026-03-04)."*
> Not: *"We landed on a competitive commission structure after some discussion."*

## 2. Temporal validity on volatile facts

Some facts are **volatile** — prices, dates, statuses, counts, "current" anything.
They change, and a stale one returned with confidence is worse than no answer.
Mark them so staleness is visible.

- **Tag volatile facts with `valid-as-of`.** Append an inline marker when you
  record one: `… fee is 2.25% (valid-as-of 2026-03-04)`. Now anyone (including
  the system) can see how old the number is before relying on it.
- **Supersede, don't silently overwrite.** When a volatile fact changes, show the
  change so the trail is auditable and a cached old value can be caught:
  `~~2.25% (valid-as-of 2026-03-04)~~ → 2.5% (updated 2026-06-01)`. Drop the
  struck-through prior value on the next edit once it's clearly settled.
- **Only volatile facts need this.** Stable facts (who you are, how a process
  works, a structural decision) don't carry a date — tagging everything is noise.
  The test: *would this fact go stale, and would a confident-but-wrong answer cost
  something?* If yes, tag it.
- **When recalling a tagged fact, check the age.** A `valid-as-of` that's months
  old on a fast-moving number is a prompt to verify before quoting, not to assert.

## Why this matters

The whole value of a file-based BOS is that it's transparent and you stay in
control of what the system "knows." These two disciplines protect that: extraction
keeps the record faithful to what actually happened, and temporal tagging keeps the
system from handing you a confidently wrong number. Apply them whenever you write a
fact into any BOS file.
