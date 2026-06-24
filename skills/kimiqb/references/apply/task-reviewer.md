# Apply Task Reviewer Role

Use this role for an independent fresh-context reviewer after implementation. The reviewer reads the brief, active sub-plan, patch, implementer report, and validation evidence. The reviewer must not be the implementer.

## Required Verdicts

Return both verdicts in `Task-Review.json`:

- `spec_compliance`: `pass`, `fail`, or `cannot_verify`
- `task_quality`: `approved` or `needs_fixes`

## Required Evidence

- `task_id`
- `brief_sha256`
- `reviewer_agent_id`
- reviewed patch or package hash
- acceptance criterion evidence
- blocking findings
- `re_review_required`

## Model Profile

Default `model_profile`: `strong`; sandbox `read-only`.
