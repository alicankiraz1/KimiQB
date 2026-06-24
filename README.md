# KimiQB

**Vibecoding-first planning for Kimi Code.** KimiQB installs the `/skill:kimiqb` skill and turns a repository into a durable planning package: main plan, existing-project autopsy, optional project comprehension, ontology, Ledger v2 continuity, phase sub-plans, QA audit, and a gated implementation handoff.

Current package contract:

- `version: 0.2.1`
- `artifact_schema_version: 2`
- `handoff_contract_version: 1`
- Repository: `https://github.com/alicankiraz1/KimiQB`

KimiQB asks intake questions in the user's language when practical. Generated Planner-docs artifacts are English by default unless the user explicitly requests another content language. Required document headings remain English for validator stability.

## Why KimiQB

- Repo-aware intake with evidence-backed defaults for intent, end state, constraints, autonomy, and context risk.
- Optional Step 1.5 autopsy for existing projects, including `Planner-docs/Project-Ontology.md` and `Planner-docs/Project-Comprehension.md` when the repository is non-trivial.
- Ledger v2 continuity through `Planner-docs/Planing-Ledger.md`, with legacy ledger compatibility in the validator.
- Canonical Kimi Code session handoffs under `skills/kimiqb/references/handoffs/` so Step 2, Step 3, and Step 4 use one maintained contract.
- Subagent-aware guidance for large repo exploration, readiness/security audit, and implementation/review separation when that reduces context load.
- Semantic Step 4 queue gates: `READY`, `READY_WITH_WARNINGS`, `BLOCKED`, and `NO_ACTION_REQUIRED`.
- Dependency-free validation and a deterministic fixture corpus for gate-integrity checks.

## 0.2.1 Gate Integrity

KimiQB 0.2.1 ports the CodexQB gate-integrity planner behavior into a Kimi Code plugin without copying Codex-only runtime surfaces. Public use stays Kimi-facing: install through Kimi Code plugins, invoke with `/skill:kimiqb`, keep planner helpers under `${KIMI_SKILL_DIR}`, and reload with `/plugins reload` or `/new` after updates.

The 0.2.1 contract focuses on planner artifact quality:

- required English headings for generated Planner-docs artifacts so validation is stable across user languages;
- optional project comprehension checks for evidence, confidence, traceability, architecture reflexion, quality scenarios, and open hypotheses;
- Ledger v2 continuity with legacy ledger compatibility;
- Step 3 preflight validation before audit writing;
- semantic Step 4 readiness gates, including `NO_ACTION_REQUIRED`;
- unsafe target-path rejection and strict Step 4 migration rules;
- deterministic fixture-corpus coverage for representative planning states.

## Workflow

| Step | What KimiQB Does | Output |
| --- | --- | --- |
| 1. Repo Scan + Main Plan | Reads repo evidence and optional continuity docs, asks four intake questions, then creates the master plan. | `Planner-docs/Main-Planing.md` |
| 1.5 Autopsy | Audits existing project reality and may preserve ontology/comprehension context. | `Planner-docs/Autopsy.md`, optional `Planner-docs/Project-Ontology.md`, optional `Planner-docs/Project-Comprehension.md` |
| 2. Phase Sub-Plans | Expands every main phase into detailed implementation-ready sub-plans. | `Planner-docs/Sub-Planing-Index.md`, `Planner-docs/Faz-*-Plans/*.md` |
| 3. QA Audit | Runs a preflight, audits coverage/readiness/evidence, and assigns Step 4 queue statuses. | `Planner-docs/Sub-Planing-Audit.md` |
| 4. Gated Handoff | Prints the implementation-session prompt only when audit and validator gates allow it. | Text-only Kimi Code session handoff, optional ledger updates during implementation |

Steps 2, 3, and 4 are intentionally handed off as text prompts for new Kimi Code sessions unless the user explicitly asks for a direct run.

## Quick Start

Install from GitHub inside Kimi Code:

```text
/plugins install https://github.com/alicankiraz1/KimiQB
/plugins reload
/new
```

Install from a local checkout inside Kimi Code:

```text
/plugins install /path/to/KimiQB
/plugins reload
/new
```

Verify installation:

```text
/plugins info kimiqb
/skill:kimiqb inspect this repo and plan this project
```

After source changes, reinstall or sync the managed copy, then use `/plugins reload` and `/new` so Kimi Code reloads the skill.

## Generated Artifacts

KimiQB writes planning artifacts under the target project's `Planner-docs/` directory:

```text
Planner-docs/
  Main-Planing.md
  Autopsy.md
  Project-Ontology.md
  Project-Comprehension.md
  Planing-Ledger.md
  Sub-Planing-Index.md
  Sub-Planing-Audit.md
  Faz-0-Plans/
    Faz0.1-*.md
```

The `Planing` spelling is intentionally preserved because the bundled prompts and validators use these exact filenames.

## Validator

KimiQB includes a dependency-free read-only validator:

```bash
python3 skills/kimiqb/scripts/validate_planner_docs.py --root /path/to/project --mode step1
python3 skills/kimiqb/scripts/validate_planner_docs.py --root /path/to/project --mode autopsy --strict
python3 skills/kimiqb/scripts/validate_planner_docs.py --root /path/to/project --mode step2 --strict
python3 skills/kimiqb/scripts/validate_planner_docs.py --root /path/to/project --mode step3-preflight --strict
python3 skills/kimiqb/scripts/validate_planner_docs.py --root /path/to/project --mode step3 --strict
python3 skills/kimiqb/scripts/validate_planner_docs.py --root /path/to/project --mode step4
```

The validator checks required headings, optional comprehension/ontology/ledger documents, Ledger v2 with legacy compatibility, ontology question statuses, audit readiness tables, finding statuses, unsafe sub-plan paths, strict Step 4 migration rules, secret hygiene, and semantic Step 4 queue gates.

Repository maintainers can run the package gate with:

```bash
make check
```

`make check` also runs the deterministic fixture corpus:

```bash
python3 evals/run_fixture_corpus_checks.py
```

Inside an extracted package without `.git/`, use:

```bash
KIMIQB_VALIDATE_SKIP_UNITTESTS=1 make check
```

## Maintainer Release Gates

Before pushing a KimiQB release or syncing a managed plugin copy, run the local gates from the repository root:

```bash
python3 evals/run_fixture_corpus_checks.py
python3 -m unittest discover -s tests -v
make check
git diff --check
```

For a distributable archive:

```bash
make export-sanitized
tmpdir="$(mktemp -d)"
unzip -q KimiQB-sanitized.zip -d "$tmpdir"
(cd "$tmpdir/KimiQB" && KIMIQB_VALIDATE_SKIP_UNITTESTS=1 make check)
```

When using the local managed Kimi Code copy, reinstall or sync with cache excludes and then start a fresh Kimi session. The source checkout, sanitized archive, and managed copy should be treated as separate validation targets.

## Repository Layout

```text
kimi.plugin.json
.github/workflows/validate.yml
Makefile
evals/
  fixtures/
  run_fixture_corpus_checks.py
skills/kimiqb/
  SKILL.md
  scripts/validate_planner_docs.py
  references/
    First-Planner.md
    Autopsy-Planner.md
    Second-Planner.md
    Third-Planner.md
    Fourth-Planner.md
    handoffs/
      run-step2.md
      run-step3.md
      run-step4.md
    project-comprehension-methods.md
    probe-policy.md
docs/
  INSTALLATION.md
  MAINTAINING.md
  USAGE.md
scripts/
  adapt_from_codexqb.py
  validate.sh
tests/
CHANGELOG.md
LICENSE
README.md
```

## Safety Model

KimiQB is planning-first. Steps 1-3 should not implement product features, refactor source code, install dependencies, commit, push, deploy, open pull requests, or write secrets into planning files. Step 4 is a separate implementation-session prompt and only starts when audit gates allow it.

## Documentation

- [Installation](docs/INSTALLATION.md)
- [Usage](docs/USAGE.md)
- [Maintaining KimiQB](docs/MAINTAINING.md)
- [Changelog](CHANGELOG.md)

## License

MIT. See [LICENSE](LICENSE).
