# Session Spec: Step 2

Stage ID: `step2`

Purpose: compile a Session prompt for adaptive Step 2 wave planning.

Required source references:
- `references/Second-Planner.md`
- `references/handoffs/run-step2.md`
- `references/workflow-quality.md`
- `references/planning-ledger.md`
- `references/project-ontology.md`

Safety:
- Detail only the active planning horizon unless full planning is explicit.
- Represent later phases as deferred roadmap cards.
- Use structured validation command contracts where possible.
- Do not implement product code.

Ready condition:
- Session prompt includes the canonical Step 2 handoff and points Step 2 final output to the canonical Step 3 handoff.
