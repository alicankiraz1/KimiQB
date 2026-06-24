# Apply Security Reviewer Role

Use this role only for high-risk tasks, sensitive paths, auth/secrets/infra changes, data migration, policy changes, or audit rows requiring security review. The security reviewer must be independent from the implementer.

## Required Report Fields

Add or verify these fields in `Task-Review.json`:

- `security_review`: `pass`, `fail`, or `not_required`
- `security_reviewer_agent_id` when review is required
- reviewed risk domains
- evidence for approval or blocking findings
- required fixes before verification

## Model Profile

Default `model_profile`: `security_strong`; sandbox `read-only`.
