# Plan Format

*Standing framework rule: every plan produced in plan mode uses the TOC change-sequence structure. The system thinks in the change sequence; the plan must mirror it.*

## Required structure — all plan-mode plans

A plan presented for approval has exactly these six sections, in order:

1. **UDEs — Undesirable Effects.** The observable symptoms driving the work. Not causes, not solutions — what's actually going wrong / what we feel.
2. **Root Cause (CRT).** Trace the UDEs to the single core problem via cause-and-effect. Name the root cause explicitly; distinguish it from the symptom.
3. **Problematic Assumption (EC).** The conflict (cloud) sustaining the root cause, and the assumption(s) that, when broken, evaporate it.
4. **Injection(s) (FRT).** What we change to. Include the FRT check: walk how the injections dissolve each UDE.
5. **Risks & Countermeasures (NBRs).** Each negative branch the injections could spawn, paired with its trimming action. A table is fine.
6. **Plan of Action (S&TT).** The execution sequence as intermediate objectives — each with strategy (how) and tactic (specific action). Include verification.

## Notes

- This is the format of the **plan file** itself, not just a summary.
- Keep each section scannable but rigorous — the user is TOC-fluent and judges the causal logic, not the labels.
- Trivial one-step changes don't need plan mode at all; when plan mode is warranted, this structure is mandatory.
- Companion: the change sequence itself is defined in `change-sequence.md`; this rule governs how a *plan* is written, not how the diagnostic is run.
