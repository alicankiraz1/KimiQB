# Apply Implementer Role

Use this role for a fresh-context worker that implements exactly one active task brief. Do not include parent chat history beyond the brief and cited source files.

## Required Inputs

- `Brief.md`
- active sub-plan path and hash
- allowed and forbidden paths
- validation commands
- stop conditions

## Required Report

Write `Implementer-Report.json` with:

- `task_id`
- `brief_sha256`
- `implementer_agent_id`
- `status`: `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`
- `files_changed`
- `validation_evidence` with command argv, exit code, and a redacted output or artifact SHA-256 hash
- `diff_sha256`
- `concerns`

## Model Profile

Default `model_profile`: `balanced`; sandbox `workspace-write`.
