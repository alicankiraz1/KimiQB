# Changelog

## 0.3.0

- Added deterministic Kimi Code session prompt compilation via `session_run.py`.
- Added gated apply-run artifact control via `apply_run.py`, including `direct` and `kimi_session_serial` modes.
- Added apply behavior, downstream session/apply dry-run, and prompt metric smoke gates.
- Added a stdlib release exporter and public privacy scanner for sanitized package provenance.
- Bumped the public contract to `artifact_schema_version: 3` and `handoff_contract_version: 2`.

## 0.2.1

- Ported gate-integrity planner semantics into KimiQB while preserving the Kimi Code plugin shape.
- Added `artifact_schema_version: 2` and `handoff_contract_version: 1` documentation.
- Added canonical Kimi Code session handoffs under `skills/kimiqb/references/handoffs/`.
- Added project comprehension and probe-policy references.
- Added Ledger v2 guidance with validator compatibility for legacy ledgers.
- Extended the planner-doc validator with comprehension, audit readiness, semantic Step 4 queue, unsafe path, and `NO_ACTION_REQUIRED` checks.
- Added deterministic fixture corpus checks and wired them into `make check`.
- Hardened sanitized export to require a clean index/worktree and use a `KimiQB/` archive prefix.
- Documented managed Kimi plugin copy parity and reload/new-session activation.

## 0.1.0

- Initial Kimi Code plugin package with `/skill:kimiqb`, repo-aware planning, Step 1.5 Autopsy, ontology, ledger continuity, sub-plan generation, QA audit, and gated implementation handoff.
