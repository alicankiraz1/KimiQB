# Apply Fixer Role

Use this role only after task review or security review requires fixes. The fixer works on the same active task, not on unrelated cleanup.

## Required Inputs

- original `Brief.md`
- failed review findings
- current patch or source state
- allowed and forbidden paths

## Required Report

Write `Fix-Report.json` with:

- `task_id`
- `brief_sha256`
- `fixer_agent_id`
- `fixes`
- validation evidence
- remaining concerns

After fixes, the controller must transition through `RE_REVIEW` before `VERIFIED`.

## Model Profile

Default `model_profile`: `balanced`; sandbox `workspace-write`.
