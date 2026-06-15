# KimiQB Vibecoding, Ledger, Ontology, and Package-Hardening Plan

## Summary

Adapt CodexQB planning-continuity hardening into KimiQB while keeping the target as Kimi Code. Preserve `/skill:kimiqb`, `KimiQB`, `Kimi Code`, `kimi.plugin.json`, `${KIMI_SKILL_DIR}`, and `skills/kimiqb/...`.

## Scope

- Add vibecoding-first planning references.
- Add optional continuity artifacts:
  - `Planner-docs/Project-Ontology.md`
  - `Planner-docs/Planing-Ledger.md`
- Add Step 1.5 autopsy validation mode.
- Keep Step 4 queue execution continuous across verified slices.
- Add subagent-aware implementation and audit guidance.
- Harden package validation for both git checkouts and extracted packages.
- Update docs, tests, and installed local KimiQB copy.

## Implementation Checklist

1. Add Kimi-adapted reference docs under `skills/kimiqb/references/`.
2. Wire Step 1, Step 1.5, Step 2, Step 3, and Step 4 to read optional autopsy, ontology, and ledger evidence when present.
3. Extend `validate_planner_docs.py` with:
   - `ONTOLOGY_HEADINGS`
   - `LEDGER_HEADINGS`
   - `validate_optional_continuity_docs`
   - `validate_autopsy_required`
   - `--mode autopsy`
4. Extend package validation with:
   - tracked-file secret scan in git checkouts;
   - filesystem secret scan outside git;
   - archive hygiene in git checkouts;
   - package hygiene outside git;
   - `KIMIQB_VALIDATE_SKIP_UNITTESTS=1` for extracted package smoke tests.
5. Update Kimi-facing docs and metadata.
6. Run unit, package, hygiene, and install-update verification.
7. Commit locally without pushing.

## Stop Gates

- KimiQB would be retargeted away from Kimi Code.
- Public plugin/docs regain stale CodexQB invocation terms.
- Validation prints secret values instead of path, line, and pattern name.
- CodexQB source checkout becomes dirty.
- Tests or package validation fail without a defensible blocker.
