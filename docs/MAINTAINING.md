# Maintaining KimiQB

This document covers validation and release maintenance for KimiQB.

Current release contract:

- `version: 0.2.1`
- `artifact_schema_version: 2`
- `handoff_contract_version: 1`

## Dependency-Free Repo Check

Run the default repository validation before every release:

```bash
make check
```

This checks the Kimi plugin manifest, required package files, Kimi skill frontmatter, stale public invocation names, tracked-file secret hygiene, archive hygiene, the deterministic fixture corpus, and the Python unit test suite. It intentionally uses only shell and Python standard-library commands so CI does not depend on local Kimi internals.

When the repository has no `.git/` metadata, the same script switches to package-level filesystem checks and prints explicit mode labels:

```bash
KIMIQB_VALIDATE_SKIP_UNITTESTS=1 make check
```

Expected extracted-package output includes `package_secret_hygiene_mode=filesystem`, `package_hygiene_mode=filesystem`, `unit_tests_skipped=1`, and `fixture_corpus_checks=passed`.

## Source Porting Policy

CodexQB source is read-only for this repository. The adapter script may read from the local source checkout:

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

The generated public skill and reference files must use `/skill:kimiqb`, `${KIMI_SKILL_DIR}`, Kimi Code session wording, canonical handoffs under `references/handoffs/`, and no Codex-only plugin surfaces.

## Validate Planner Docs

The skill ships a read-only validator for generated `Planner-docs/` outputs. From a KimiQB repository checkout, run:

```bash
python3 skills/kimiqb/scripts/validate_planner_docs.py --root /path/to/project --mode step1
python3 skills/kimiqb/scripts/validate_planner_docs.py --root /path/to/project --mode autopsy --strict
python3 skills/kimiqb/scripts/validate_planner_docs.py --root /path/to/project --mode step2 --strict
python3 skills/kimiqb/scripts/validate_planner_docs.py --root /path/to/project --mode step3-preflight --strict
python3 skills/kimiqb/scripts/validate_planner_docs.py --root /path/to/project --mode step3 --strict
python3 skills/kimiqb/scripts/validate_planner_docs.py --root /path/to/project --mode step4
```

When changing the validator, test at least:

- required headings for Step 1, Autopsy, Step 2, Step 3, and Step 4;
- optional `Project-Comprehension.md`, `Project-Ontology.md`, and `Planing-Ledger.md` heading validation;
- Ledger v2 headings and legacy v1 compatibility;
- ontology question statuses and comprehension confidence/status values;
- unsafe sub-plan path rejection;
- audit readiness tables, finding statuses, `NO_ACTION_REQUIRED`, `READY`, `READY_WITH_WARNINGS`, and `BLOCKED`;
- strict Step 4 migration rules;
- normal filenames containing `sk-` such as `task-spec.yaml`;
- fake long secret tokens that should be detected without printing the token value.

Run the tracked validator test suite:

```bash
python3 -m unittest discover -s tests -v
```

## Fixture Corpus

Run the deterministic fixture corpus directly when changing comprehension, traceability, or gate-integrity semantics:

```bash
python3 evals/run_fixture_corpus_checks.py
```

The fixture corpus must contain stable `expected.json` files for:

- `clean-layered-service`
- `drifted-architecture`
- `distributed-domain-feature`
- `hidden-coupling-signal`
- `stale-ledger`
- `runtime-only-behavior`
- `security-boundary-risk`

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

## Managed Copy Parity

When applying KimiQB to the local installed Kimi Code plugin, sync the managed copy with cache excludes:

```bash
rsync -a --delete \
  --exclude '.git/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude '.pytest_cache/' \
  --exclude '.mypy_cache/' \
  --exclude '.ruff_cache/' \
  --exclude 'KimiQB-sanitized.zip' \
  /path/to/KimiQB/ "$KIMI_CODE_HOME/plugins/managed/kimiqb/"
diff -ru -x __pycache__ -x '*.pyc' -x .git -x .pytest_cache -x .mypy_cache -x .ruff_cache \
  /path/to/KimiQB/ "$KIMI_CODE_HOME/plugins/managed/kimiqb/"
```

After syncing, require `/plugins reload` or `/new` for activation.

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

This target requires a clean index and clean worktree, then writes `KimiQB-sanitized.zip` with a `KimiQB/` archive prefix. It excludes historical `docs/superpowers/plans/` planning notes from the distributable package so stale local planning context is not shipped.

After exporting, smoke the zip without git metadata:

```bash
tmpdir="$(mktemp -d)"
unzip -q KimiQB-sanitized.zip -d "$tmpdir"
(cd "$tmpdir/KimiQB" && KIMIQB_VALIDATE_SKIP_UNITTESTS=1 make check)
```

The package-level fallback must not print secret values. It reports only path, line, and pattern name.

## Release Flow

1. Update `kimi.plugin.json`.
2. Update `skills/kimiqb/SKILL.md`, canonical handoffs, and references as needed.
3. Update `skills/kimiqb/references/repo-aware-intake.md` if Step 1 intake behavior changes.
4. Update `skills/kimiqb/references/Autopsy-Planner.md` if Step 1.5 autopsy, ontology, or comprehension behavior changes.
5. Update `skills/kimiqb/references/planning-ledger.md` and `skills/kimiqb/references/project-ontology.md` if continuity artifact requirements change.
6. Update `skills/kimiqb/references/Fourth-Planner.md` and `skills/kimiqb/references/handoffs/run-step4.md` if implementation handoff, queue continuation, stop gates, or ledger behavior changes.
7. Update `skills/kimiqb/scripts/validate_planner_docs.py` if planner structure, autopsy mode, optional continuity docs, or readiness gates change.
8. Run `python3 evals/run_fixture_corpus_checks.py`.
9. Run `make check`.
10. Run the extracted-package smoke check against `KimiQB-sanitized.zip`.
11. If Kimi Code CLI is available, reinstall or sync the local plugin, then smoke `/skill:kimiqb`.
12. Confirm the CodexQB source checkout is still clean.
13. Commit with a focused message.
14. Do not push, create a pull request, publish a release, or install into a live shared environment unless explicitly requested.

## Contribution Guidelines

- Keep the skill concise.
- Keep long planner prompts in `references/`.
- Preserve the `Planner-docs/*Planing*` filenames required by the bundled prompts.
- Keep generated planner artifact headings English for validator stability.
- Do not add MCP servers, hooks, or runtime commands unless the plugin manifest and validator are updated accordingly.
- Do not put secrets or environment-specific credentials into docs, planner prompts, or examples.
