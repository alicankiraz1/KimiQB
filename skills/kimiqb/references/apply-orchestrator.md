# KimiQB Subagent Apply Orchestrator

The Apply Orchestrator defines a resumable Step 4 artifact protocol. It does not execute implementation by itself.

## Runtime Location

Target repositories store apply artifacts under:

```text
.kimiqb/apply-runs/<apply-run-id>/
  Apply-Run.json
  Progress.json
  Events.jsonl
  Writer-Lock.json
  AR-<apply-run-id>-T<nnn>/Brief.md
  AR-<apply-run-id>-T<nnn>/Dispatch-Packet.json
  AR-<apply-run-id>-T<nnn>/Agent-Run-<role>-<nn>.json
  AR-<apply-run-id>-T<nnn>/Implementer-Report.json
  AR-<apply-run-id>-T<nnn>/Review-Package.patch
  AR-<apply-run-id>-T<nnn>/Task-Review.json
  AR-<apply-run-id>-T<nnn>/Fix-Report.json
  Final-Review.json
  Result.json
```

These runtime directories are created in the target repository, not in the KimiQB source tree except for tests and examples.
Non-`no_action` runs derive initial task briefs from Step 4 READY or READY_WITH_WARNINGS entries in `Planner-docs/Sub-Planing-Audit.md` when available. The audit-derived source sub-plan path and hash are recorded in both `Progress.json` and `Brief.md`.
When present in the active sub-plan, the controller also copies the source sub-plan SHA-256, the full structured Implementation Contract, `implementation_contract_digest`, `task_contract_digest`, and fresh-context contract signals into each task: acceptance criteria, allowed/forbidden paths, parent signals, dependencies, framework ownership, algorithmic invariants, planned validation commands, `validation_command_ids`, outputs, risk/security requirements, and the security review flag. The same structured contract is included in `Brief.md`, verified reports, and subagent dispatch prompts so fresh agents can work from the task contract without inheriting parent chat history.
`apply_run.py prepare` must run strict Step 4 validation before writing action artifacts. `Apply-Run.json.step4_readiness` records validator status, a validator output hash, and the execution queue state used to accept READY tasks or `NO_ACTION_REQUIRED`.
Use `apply_run.py prepare` for new runs; `init` remains a compatibility alias. Use `apply_run.py dispatch` before `kimi_session_serial` implementation to write a fresh-context `Dispatch-Packet.json` that can be converted into a Kimi Code `kimi_session_dispatch_artifact` call by the parent agent. After the parent calls the actual Kimi Code tool, use `apply_run.py record-agent` to record the spawned agent id and later the completed or failed result. Use `apply_run.py transition` for state changes so `Events.jsonl` remains the append-only transition truth. Use `apply_run.py recover-lock` only for expired writer locks to move an abandoned `IMPLEMENTING` task to `BLOCKED` or `NEEDS_CONTEXT`. Use `apply_run.py reconcile` for external adapter fallback before dispatch, and `apply_run.py finalize` only after all tasks are VERIFIED and final review has passed. `Progress.json` is the current state snapshot.
`apply_spec_id` is deterministic for the selected mode, source snapshot, workspace baseline, and Step 4 READY queue. `apply_run_id` is unique per invocation. To continue a run, pass `--resume` with the exact `--output-dir`; to intentionally regenerate one directory, pass `--replace`.

## Schema Contract

`Apply-Run.json` is the immutable run envelope: schema versions, requested mode, current mode, spec/run IDs, `apply_policy_digest`, source snapshot, `workspace_baseline`, Step 4 readiness summary, workspace posture, `budget_contract`, `token_usage`, safety defaults, agent profiles, and external adapter policy. The policy digest is recomputed during validation from the approved workspace, readiness, safety, budget, agent-profile, and external-adapter envelope so self-consistent tampering is rejected. The baseline records branch/base commit, Git status and staged/unstaged diff hashes, untracked inventory hash, and a non-Git file inventory hash when applicable. Workspace posture records `workspace_requested`, `workspace_detected`, `workspace_verified`, `workspace_mode`, `worktree_path`, `base_branch`, `working_branch`, `dirty_state`, and `user_approval`. `.kimiqb/` runtime artifacts are excluded from these baseline hashes. `Progress.json` is mutable operational state: task list, task states, dispatch status, agent run records, writer locks, verified task IDs, final-review requirement, fix-cycle count, and resume cursor. `Events.jsonl` is the append-only transition truth. Per-task directories use the exact task ID and contain the brief, dispatch packet, agent-run records, implementer report, review package, task review, and fix report. `Result.json` repeats the budget and token-usage state so finalized runs do not lose budget provenance.

For a task to become `VERIFIED`, `Implementer-Report.json.files_changed` must be non-empty, safe repo-relative paths, and a subset of the task Implementation Contract paths. `Review-Package.patch` must be non-empty, its SHA-256 must match `Implementer-Report.json.diff_sha256`, and its diff file list must match the reported changed files. `validation_evidence` must be a passing safe command whose `id` and `argv` match one of the task's planned validation commands and must include a redacted output or artifact hash such as `output_sha256`, `combined_output_sha256`, or `artifact_sha256`.

Implementation drift may include tracked unstaged files listed in the task contract and reported by the implementer/fixer. Untracked new files are accepted only for exact contract paths whose `implementation_paths` entry declares `state: proposed`; staged files and contract-external files remain blockers.

The default budget contract caps selected implementation tasks at 4, subagent attempts per role at 2, and fix cycles at 2. Token ceilings are recorded for planning discipline, but runtime token usage remains `not_observed` unless the controller receives real usage data. Validators reject artifacts that raise attempts or fix cycles above the recorded budget, exceed the selected-task cap, or claim partial unobserved token usage.

Action modes (`direct`, `kimi_session_serial`, and `external_adapter`) must not prepare against a non-Git workspace by default. If a non-Git workspace is unavoidable, the caller must pass `--allow-non-git-unsafe`; `Apply-Run.json` then records `workspace_mode: non_git_unsafe` and `user_approval: true`. Without that explicit approval, prepare fails with `non_git_workspace_requires_explicit_approval`. `no_action` mode may record a non-Git workspace without this unsafe approval because it does not queue implementation tasks.

Action modes must also treat protected or dirty Git current worktrees as unverified. If `working_branch` is `main`, `master`, or `unknown`, or `dirty_state` is `dirty`, prepare fails unless the caller passes `--allow-unverified-git-worktree`; the resulting artifact records `workspace_mode: unverified_current_worktree` and `user_approval: true`. A future verified isolated worktree controller may use `workspace_mode: verified_isolated_worktree`.

The packaged public schema reference is `references/apply-run-schema.json`. Runtime validation remains dependency-free in `scripts/apply_run.py`; the schema file exists so users, reviewers, and generated package checks can inspect the artifact contract without reverse-engineering Python code.

## Modes

- `direct`: parent-only execution for a bounded selected batch.
- `kimi_session_serial`: parent controller dispatches one fresh implementer at a time, then runs independent reviews.
- `external_adapter`: optional adapter when Superpowers is already installed; KimiQB remains top-level controller. Availability must be checked before dispatch. If unavailable, run `apply_run.py reconcile` so the artifact mode becomes `kimi_session_serial` before implementation starts.
- `no_action`: record NO_ACTION_REQUIRED without starting implementation.

## State Machine

Allowed task states:

- `PREFLIGHT`
- `BRIEFED`
- `IMPLEMENTING`
- `IMPLEMENTED`
- `TASK_REVIEW`
- `SECURITY_REVIEW`
- `FIXING`
- `RE_REVIEW`
- `VERIFIED`
- `BLOCKED`
- `NEEDS_CONTEXT`

Each active slice must pass spec review before quality/security review. Failed review requires same-slice fix and re-review before completion.
Existing apply-run directories are not overwritten by default. Use explicit resume/replace behavior when continuing or intentionally regenerating artifacts.

Transitions must follow:

```text
PREFLIGHT -> BRIEFED
BRIEFED -> IMPLEMENTING | BLOCKED | NEEDS_CONTEXT
IMPLEMENTING -> IMPLEMENTED | BLOCKED | NEEDS_CONTEXT
IMPLEMENTED -> TASK_REVIEW
TASK_REVIEW -> SECURITY_REVIEW | FIXING | VERIFIED
FIXING -> RE_REVIEW | BLOCKED | NEEDS_CONTEXT
RE_REVIEW -> SECURITY_REVIEW | VERIFIED | FIXING
SECURITY_REVIEW -> VERIFIED | FIXING | BLOCKED | NEEDS_CONTEXT
```

`IMPLEMENTING` acquires `Writer-Lock.json` atomically. Leaving `IMPLEMENTING` releases it. Expired writer locks are validation blockers until `recover-lock` records a recovery transition to `BLOCKED` or `NEEDS_CONTEXT`. Validation rejects state snapshots that are not backed by a contiguous transition event.

For `kimi_session_serial`, `BRIEFED -> IMPLEMENTING` additionally requires `Dispatch-Packet.json` plus a `record-agent --status spawned` event for the implementer. `IMPLEMENTING -> IMPLEMENTED` requires `record-agent --status completed` for that implementer attempt. Failed agent starts are recorded with `--status failed`; after that, the controller may prepare a new dispatch packet for the same task before implementation starts. The packet records `spawn_tool: kimi_session_dispatch_artifact`, role, profile, sandbox, fresh brief hash, prompt hash, `fork_context: false`, and the exact message the parent Kimi Code controller should pass to the subagent. The script prepares and validates these artifacts but does not call Kimi Code tools itself.

## Role Templates and Model Profiles

Fresh-context role templates live under `references/apply/`:

- `controller.md`
- `implementer.md`
- `task-reviewer.md`
- `security-reviewer.md`
- `fixer.md`
- `final-reviewer.md`

`Apply-Run.json` includes role-level `agent_profiles` with stable model profiles instead of hardcoded model names: `fast`, `balanced`, `strong`, `security_strong`, and `inherit` when a user explicitly asks to inherit the active session. Reviewers default to read-only sandboxes; the implementer and fixer are the only default workspace-write roles.

## Review Result Shape

```json
{
  "task_id": "AR-apply-kimi_session_serial-<digest>-<invocation>-T001",
  "spec_compliance": "pass",
  "task_quality": "approved",
  "security_review": "pass",
  "reviewer_agent_id": "reviewer-1",
  "security_reviewer_agent_id": "security-reviewer-1",
  "brief_sha256": "<sha256>",
  "blocking_findings": [],
  "fixes_required": [],
  "evidence": ["targeted validation passed"],
  "re_review_required": false
}
```

## Safety

- Commit policy defaults to `none`.
- Commit, push, PR, deploy, live probes, and destructive external mutation are opt-in only.
- Only one writer modifies files per slice unless the user explicitly requests separate branches or worktrees.
- Subagents are read-only by default except the selected fresh-slice implementer.
- Required or performed security review must record `security_reviewer_agent_id` in `Task-Review.json`, and that identity must differ from `implementer_agent_id`.
- `kimi_session_serial` implementation must have a dispatch packet and spawned agent record before writer lock acquisition, and a completed agent record before the task can move to IMPLEMENTED.
- `Progress.json` is the authoritative operational state for resume.
- `Events.jsonl` is the append-only transition truth.
- `Apply-Run.json.workspace_baseline` must match the current workspace baseline before resume; mismatches are blockers until the controller reconciles or starts a new run.
- JSON snapshots are written with temp-file plus replace; writer lock uses create-exclusive semantics and expired locks must be recovered with an explicit controller event.
- `no_action` runs must not contain queued tasks.
- Task IDs must use the controller-generated `AR-<apply-run-id>-T<nnn>` format and resolve inside the apply-run directory.
- `external_adapter` runs must record adapter availability and metadata before dispatch; unavailable adapters must be reconciled to `kimi_session_serial`.
- VERIFIED tasks require matching brief hashes, implementer identity, changed-file inventory, passing validation evidence, independent reviewer identity, review evidence, and final repo-level validation evidence.
