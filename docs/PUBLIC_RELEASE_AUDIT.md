# Public Release Audit

Audit date: 2026-06-27

## Decision

The current `main` tree is clean, but the existing `main` Git history is not suitable to make public as-is. Older commits contain local planning artifacts with machine-local path evidence.

The `public-clean-main` branch is the public-safe publication candidate. It was created from the current clean tree as a clean-history branch with no inherited private history.

## Current Branch Status

| Surface | Status | Evidence |
| --- | --- | --- |
| `main` current tree | Clean | `tracked_public_broad_findings=0`, `public_privacy_check=passed`, CI `validate` success |
| `main` Git history | Not public-safe | History scan finds older local planning artifact path evidence |
| `public-clean-main` current tree | Clean | `tracked_public_broad_findings=0`, `public_privacy_check=passed` |
| `public-clean-main` Git history | Clean | `git_history_public_findings=0` |
| Sanitized package | Clean | `zip_blocked_entries=0`, `tracked_only=True`, `working_tree_clean=True` |
| Kimi managed copy | Clean | `managed_copy_diff=clean` |

## Passing Gates

The public-safe candidate passed:

```text
make check-release
python3 scripts/check_public_privacy.py --root .
git diff --check
tracked_public_broad_findings=0
git_history_public_findings=0
```

GitHub Actions `validate` passed for `public-clean-main`.

## Publication Guidance

Do not make the existing private repository public while `main` still carries the old private history.

Safe publication options:

1. Publish from `public-clean-main` as a new clean-history public repository.
2. Replace the private repository history with the clean-history branch only after explicit approval for destructive history rewrite.

The first option is safer because it avoids force-pushing or relying on remote garbage collection of old private objects.
