# KimiQB Dynamic Session Compiler

The Dynamic Session Compiler turns KimiQB source contracts into a deterministic Session spec and a unique Session preview run before a user starts a new Kimi Code session.

It is not an executor. It does not run validation commands, edit global Kimi Code configuration, install dependencies, sync plugin caches, commit, push, create pull requests, deploy, or mutate external systems.

## Inputs

- Target repository root.
- Session stage: `step15`, `step2`, `step3`, or `step4`.
- Canonical handoff source when the stage has one.
- Stage session spec under `references/session-specs/`.
- Relevant existing `Planner-docs/` artifacts.
- Optional output directory inside the target repository.

## Outputs

The compiler writes a per-invocation run directory:

```text
Planner-docs/Session-Runs/<session-run-id>/
  Session-Run.json
  Session-Prompt.md
  Session-Result.json
```

`Session-Run.json` records source snapshot hashes, deterministic `session_spec_id`, invocation-specific `session_run_id`, stage, handoff contract version, artifact schema version, output paths, pinned template hashes, compiler hash, `session_policy_digest`, Step 2 `planning_horizon` metadata, active sub-plan inventories, source sub-plan paths and SHA-256 hashes, structured `implementation_contract` objects when present, `implementation_contract_digest`, `validation_command_ids`, contract-derived Step 4 work steps, strict validation checkpoints, `budget_contract`, `token_usage`, and safety policy. `Session-Prompt.md` is the user-facing Session prompt. `Session-Result.json` is a preview result describing whether the prompt is ready or blocked and records `session_run_sha256`, budget and token-usage state, plus `prompt_sha256` when a prompt is rendered.

`Session-Prompt.md` must be rendered deterministically from a valid `Session-Run.json`. Rendering must first validate schema version, secret hygiene, source snapshot integrity, current stage snapshot match, source-bound implementation contracts, strict checkpoint policy, the recomputed Session policy envelope, allowed/forbidden path policy, and glob overlap.

`session_spec_id` is stable for the same source snapshot, mode, objective, and active scope. `session_run_id` includes an invocation suffix so repeated prepares create separate run directories unless the caller explicitly supplies the same `--output-dir`. Rendering must reject template bundle, compiler, source snapshot, or stored digest drift before writing output.

`prepare` must run the bundled validator for the selected stage prerequisite before writing an execution prompt. Missing prerequisites or validator failures write `Session-Result.json` with `status: blocked` and remove/avoid `Session-Prompt.md`.

Validation also rejects semantic drift in run controls: unsupported stage modes, blank objectives, empty work steps, unsafe validation checkpoints, recursive subagent depth, invalid context-token risk declarations, invalid budget limits, selected-task budget overflow, and dishonest token-usage state. These fields are execution safety controls, not display-only metadata.

Stage snapshots are stage-aware. Step 3 treats `Sub-Planing-Audit.md` as expected mutable output while keeping Step 2 source artifacts immutable. Step 4 treats `Planing-Ledger.md`, `.kimiqb/apply-runs/**`, and implementation paths declared by READY queue contracts as mutable outputs while keeping the Main Plan, index, audit, and selected source sub-plans immutable.

## Security Rules

- Output directory must be inside the target repository.
- Default output is `Planner-docs/Session-Runs/<session-run-id>/`.
- Source snapshots include hashes and relative paths only.
- Active scope must use portable repo-relative roots such as `"."`, not local absolute paths.
- Allowed and forbidden write patterns must be repo-relative. Absolute paths, traversal, unsafe wildcards, and overlapping allowed/forbidden patterns are blockers.
- Existing run directories must not be overwritten unless `--replace` is explicit. `--resume` requires an explicit output directory and validates the existing `Session-Run.json` before rendering or reporting it.
- The compiler must never include secrets, environment values, local credentials, or full logs.
- The compiler must never execute validation commands from planner docs.
- Step 4 prompts must preserve no-commit/no-push/no-PR/no-deploy defaults unless the user explicitly opts in during the implementation run.

## Stage Behavior

- `step15`: prepare Step 1.5 Autopsy context for existing projects.
- `step2`: prepare adaptive wave/full/refresh/repair planning handoff with active sub-plan inventory, no-subplans `planning_horizon` derived from `Main-Planing.md`, contract-signal summaries, `validation_command_ids`, and structured `implementation_contract` objects when present.
- `step3`: prepare Step 3 preflight and audit handoff with active sub-plan inventory, contract-signal summaries, and structured `implementation_contract` objects when present.
- `step4`: prepare gated apply handoff with READY/READY_WITH_WARNINGS audit queue entries, contract-signal summaries, `validation_command_ids`, and structured `implementation_contract` objects. Work steps must be derived from parent signals, implementation paths, validation command IDs, dependency state, security review requirements, and expected outputs; actual implementation remains user-triggered.

If required stage inputs are missing, the compiler writes `Session-Result.json` with `status: blocked` and blocker IDs. It must not write an execution `Session-Prompt.md` for blocked prerequisites.
