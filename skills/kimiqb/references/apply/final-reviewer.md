# Apply Final Reviewer Role

Use this role after the selected batch is complete. The final reviewer is independent from slice implementers and checks integration, evidence, ledger accuracy, and unresolved minor findings.

## Required Report

Write `Final-Review.json` with:

- `status`: `pass`, `not_started`, or a blocking failure status
- `reviewed_task_ids`
- base/head or snapshot evidence
- `global_validations` with argv and exit code
- open minor findings
- integration verdict
- concise evidence

## Model Profile

Default `model_profile`: `strong`; sandbox `read-only`.
