# Session Spec: Step 4

Stage ID: `step4`

Purpose: compile a gated apply prompt preview from the Step 4 handoff.

Required source references:
- `references/Fourth-Planner.md`
- `references/handoffs/run-step4.md`
- `references/subagent-playbook.md`
- `references/probe-policy.md`

Safety:
- Step 4 is not auto-executed by the compiler.
- Apply modes are `direct`, `kimi_session_serial`, `external_adapter`, and `no_action`.
- Commit, push, PR, deploy, and external mutation remain opt-in.
- Non-trivial slices use fresh implementer, spec review, quality/security review, fix/re-review, and final review.

Ready condition:
- Session prompt preserves the canonical Step 4 Session Run Contract and explicit stop gates.
