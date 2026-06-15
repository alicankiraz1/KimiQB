# Maintaining KimiQB

This document covers validation and release maintenance for KimiQB.

## Dependency-Free Repo Check

Run the default repository validation before every release:

```bash
make check
```

This checks the Kimi plugin manifest, required package files, Kimi skill frontmatter, stale public invocation names, and the Python unit test suite. It intentionally uses only shell and Python standard-library commands so CI does not depend on local Kimi internals.

## Source Porting Policy

CodexQB source is read-only for this repository. The adapter script may read from the local CodexQB checkout:

```text
/path/to/CodexQB
```

It must write only inside the KimiQB checkout. Confirm this after adapter runs:

```bash
git -C /path/to/CodexQB status --short
```

Expected output is empty.

## Adapter Script

Regenerate the Kimi-facing skill tree from the current local source:

```bash
python3 scripts/adapt_from_codexqb.py
```

Then run:

```bash
python3 -m unittest tests.test_skill_content -v
```

The generated public skill and reference files must use `/skill:kimiqb`, `${KIMI_SKILL_DIR}`, and Kimi Code session wording.

## Validate Planner Docs

The skill ships a read-only validator for generated `Planner-docs/` outputs. From a KimiQB repository checkout, run:

```bash
python3 skills/kimiqb/scripts/validate_planner_docs.py --root /path/to/project --mode step1
python3 skills/kimiqb/scripts/validate_planner_docs.py --root /path/to/project --mode step2 --strict
python3 skills/kimiqb/scripts/validate_planner_docs.py --root /path/to/project --mode step3 --strict
python3 skills/kimiqb/scripts/validate_planner_docs.py --root /path/to/project --mode step4
```

When changing the validator, test at least:

- a valid Step 2 fixture;
- a missing-section fixture;
- a normal filename containing `sk-` such as `task-spec.yaml`;
- a fake long secret token that should be detected;
- roadmap table extraction with historical phase references such as `Faz 0B-10` or `Phase 11`;
- optional `Autopsy.md` validation when present, and no failure when it is absent;
- Step 4 readiness gating for missing audit, `BLOCKED`, `PASS`, `PASS_WITH_WARNINGS`, and prose such as `No P0/P1 findings`.

Run the tracked validator test suite:

```bash
python3 -m unittest discover -s tests -v
```

## Kimi CLI Smoke

The dependency-free check does not require Kimi Code CLI. If `kimi` is available on PATH, manually smoke the plugin:

```bash
kimi --version
```

Inside Kimi Code:

```text
/plugins install /path/to/KimiQB
/plugins info kimiqb
/plugins reload
/new
/skill:kimiqb inspect this repo and plan this project
```

Expected behavior: the plugin is installed, `/plugins info kimiqb` shows manifest metadata, and the skill starts by scanning the repo and asking `Question 1 / 4 - PROJECT_NAME`.

## Check For Stale Invocation Names

KimiQB should use `/skill:kimiqb` as the skill invocation. The default release check scans public package files for stale package, path, and install references:

```bash
make check
```

Tests and `scripts/adapt_from_codexqb.py` are excluded from this public-surface scan because they intentionally contain source-porting fixture text.

## Sanitized Export

Do not create release zips with Finder or generic directory compression, because ignored files such as `.git/`, `__pycache__/`, `.env`, `artifacts/`, `logs/`, or `tmp/` can be included.

Use the tracked-file export target:

```bash
make export-sanitized
```

This writes `KimiQB-sanitized.zip` with `git archive`.

## Release Flow

1. Update `kimi.plugin.json`.
2. Update `skills/kimiqb/SKILL.md` and references as needed.
3. Update `skills/kimiqb/references/repo-aware-intake.md` if Step 1 intake behavior changes.
4. Update `skills/kimiqb/references/Autopsy-Planner.md` if Step 1.5 autopsy behavior changes.
5. Update `skills/kimiqb/references/Fourth-Planner.md` if implementation handoff behavior changes.
6. Update `skills/kimiqb/scripts/validate_planner_docs.py` if planner structure or readiness gates change.
7. Run `make check`.
8. If Kimi Code CLI is available, reinstall the local plugin and smoke `/skill:kimiqb`.
9. Confirm the CodexQB source checkout is still clean.
10. Commit with a focused message.
11. Do not push, create a GitHub repository, publish a release, or install into a live shared environment unless explicitly requested.

## Contribution Guidelines

- Keep the skill concise.
- Keep long planner prompts in `references/`.
- Preserve the `Planner-docs/*Planing*` filenames required by the bundled prompts.
- Do not add MCP servers, hooks, or runtime commands unless the plugin manifest and validator are updated accordingly.
- Do not put secrets or environment-specific credentials into docs, planner prompts, or examples.
