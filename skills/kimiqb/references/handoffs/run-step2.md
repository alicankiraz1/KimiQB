---
contract_version: 2
---

# Step 2 Kimi Code Session Handoff

Use /skill:kimiqb. Run Step 2 according to `references/Second-Planner.md`.

Kimi Code Session Contract:
- Outcome: decompose the active planning horizon into implementation-ready sub-plans and represent later phases as deferred roadmap cards unless the user explicitly requests full-project decomposition.
- Inputs: `Planner-docs/Main-Planing.md` plus optional `Autopsy.md`, `Project-Ontology.md`, `Project-Comprehension.md`, and `Planing-Ledger.md`.
- Boundaries: modify only `Planner-docs/`; do not implement product code or edit `Planner-docs/Main-Planing.md`.
- Source precedence: user-confirmed intent and `Main-Planing.md` first; current repository evidence second; optional continuity artifacts third. Tentative comprehension claims require validation work before becoming implementation facts.
- Validation gates: run the bundled Step 2 validator or equivalent all-file validation.
- Stop gates: missing, inconsistent, incomplete, or undecomposable `Main-Planing.md`; unrelated dirty worktree only if it blocks safe planning.
- Planning modes: `wave` is the default; use `full` only on explicit user request, `refresh` for incremental updates, and `repair` for audit-driven selected-file fixes.
- Context budget: before writing, estimate detected phases, detailed subplans, total words, Session token risk, recommended active phases, and whether the run exceeds the confirmation threshold (`>15` detailed files or very high risk).
- Subagent policy: use at most two bounded read-only reviewers when phase count is high, expected subplans exceed 12, domain risk is high, or framework ownership is uncertain; parent writes final artifacts.

Resume / Recovery Protocol:
1. Re-read this canonical Kimi Code Session Contract.
2. Read current git status and branch.
3. Re-read `Main-Planing.md`, optional autopsy, ontology, comprehension, ledger, and any existing index/sub-plans.
4. Reconcile ledger state with repository evidence before writing.
5. Do not repeat a verified slice or duplicate an existing sub-plan.
6. If the active plan snapshot changed, stop and request or perform replanning.

Read all main phases in `Planner-docs/Main-Planing.md`. If `Planner-docs/Autopsy.md`, `Planner-docs/Project-Ontology.md`, `Planner-docs/Project-Comprehension.md`, or `Planner-docs/Planing-Ledger.md` exists, read it fully as supporting evidence and account for it in the sub-phase plans. Determine the planning horizon using this precedence: explicit user request, `Main-Planing.md` Step 2 Preparation Notes, active ledger state, then KimiQB defaults. In default `wave` mode, detail only the active planning horizon and represent later phases as deferred roadmap cards in `Sub-Planing-Index.md`. Use `full` mode only when the user explicitly asks for full-project decomposition. Plan in a vibecoding-first style: small reversible slices, fast validation signals, explicit deferrals, security boundaries, evidence confidence, CQ/TRACE/ARC references, parent acceptance traceability, framework ownership boundaries, and Kimi Code session readiness. Modify only `Planner-docs`.
