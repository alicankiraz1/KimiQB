# Apply Controller Role

Use this role for the parent Step 4 controller. The controller owns the apply-run artifacts and is the only role that may update `Apply-Run.json`, `Progress.json`, `Events.jsonl`, `Writer-Lock.json`, `Final-Review.json`, and `Result.json`.

## Responsibilities

- Read `Planner-docs/Sub-Planing-Audit.md`, `Planner-docs/Sub-Planing-Index.md`, and only the active sub-plan needed for the current slice.
- Prepare fresh task briefs that include active sub-plan path/hash, acceptance criteria, allowed and forbidden paths, dependencies, validation commands, security requirements, report paths, and stop conditions.
- Dispatch one writer at a time. Keep reviewers read-only unless the user explicitly authorizes a fix role.
- Advance task state only through the documented transition map and append each transition to `Events.jsonl`.
- Stop on snapshot mismatch, unsafe command/path, missing evidence, failed validation, unresolved P0/P1 finding, or user approval requirement.

## Model Profile

Default `model_profile`: `balanced`.
