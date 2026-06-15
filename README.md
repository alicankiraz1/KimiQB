# KimiQB

**Vibecoding-first planning for Kimi Code.** KimiQB turns a project repository into a durable planning package: main plan, existing-project autopsy, optional project ontology, optional planning ledger, phase sub-plans, QA audit, and a gated implementation handoff.

KimiQB installs the `/skill:kimiqb` skill for Kimi Code CLI. It is built for software, AI, infrastructure, security, and automation projects where planning must be evidence-backed, reviewable, and ready for step-by-step execution.

KimiQB asks intake questions in the user's language when practical. Generated Planner-docs artifacts are English by default unless the user explicitly requests another body language. Required document headings remain English for validator stability.

## Why KimiQB

- **Repo-aware intake:** KimiQB inspects the current repository before asking questions, then proposes evidence-backed defaults for project name, intent, target end state, constraints, autonomy, review cadence, and token/context risk.
- **Vibecoding-first planning:** Plans preserve a clear target while favoring small reversible slices, fast validation signals, explicit deferrals, and evidence-backed adaptation.
- **Durable planning docs:** Output is written under `Planner-docs/` so long planning work survives context changes and can be reviewed like normal project documentation.
- **Project Autopsy + Ontology:** Existing projects get a focused `Autopsy.md` report and may get `Project-Ontology.md` for vocabulary, entities, workflows, boundaries, integrations, and invariants.
- **Planning ledger:** `Planing-Ledger.md` can preserve concise planning and implementation history for replanning and Step 4 continuity.
- **Subagent-aware guidance:** KimiQB recommends subagents only when they reduce context pollution or separate exploration, implementation, verification, and security review.
- **Full phase decomposition:** The main plan can be expanded into ordered phase folders and detailed sub-plan files, using Autopsy, Ontology, and Ledger feedback when available.
- **QA before implementation:** The audit step checks coverage, naming, ordering, section structure, readiness, security/governance, ontology consistency, planning-history continuity, and vibecoding slice quality.
- **Gated execution handoff:** KimiQB does not implement product changes itself during planning. It prints a separate implementation prompt only when the audit says implementation can begin.

## Workflow

| Step | What KimiQB Does | Output |
| --- | --- | --- |
| 1. Repo Scan + Main Plan | Reads the repository, optional ledger/ontology history, asks four enriched intake questions, and creates the master plan. | `Planner-docs/Main-Planing.md` |
| 1.5 Autopsy | For existing projects, audits current project structure and may preserve project vocabulary/boundaries. | `Planner-docs/Autopsy.md`, optional `Planner-docs/Project-Ontology.md` |
| 2. Phase Sub-Plans | Expands every main phase into detailed implementation-ready sub-plans. | `Planner-docs/Sub-Planing-Index.md`, `Planner-docs/Faz-*-Plans/*.md` |
| 3. QA Audit | Audits coverage, structure, quality, readiness, ontology consistency, planning continuity, and governance without repairing files. | `Planner-docs/Sub-Planing-Audit.md` |
| 4. Gated Handoff | Prints a copy-ready implementation prompt and tells implementation sessions to append concise ledger entries. | Text-only new-session prompt, optional `Planner-docs/Planing-Ledger.md` updates |

Step 1 can run in the current Kimi Code session. Steps 2, 3, and 4 are intentionally handed off as text prompts for new Kimi Code sessions so the user stays in control of long-running work.

## Quick Start

Install from a local checkout inside Kimi Code:

```text
/plugins install /path/to/KimiQB
/plugins reload
/new
```

Install from GitHub when the repository exists and your environment has access:

```text
/plugins install https://github.com/alicankiraz1/KimiQB
/plugins reload
/new
```

Verify installation:

```text
/plugins info kimiqb
/skill:kimiqb inspect this repo and plan this project
```

## Generated Artifacts

KimiQB writes planning artifacts under the target project's `Planner-docs/` directory:

```text
Planner-docs/
  Main-Planing.md
  Autopsy.md
  Project-Ontology.md
  Planing-Ledger.md
  Sub-Planing-Index.md
  Sub-Planing-Audit.md
  Faz-0-Plans/
    Faz0.1-*.md
  Faz-1-Plans/
    Faz1.1-*.md
```

The `Planing` spelling is intentionally preserved because the bundled planner prompts and validators use these exact filenames.

## Validator

KimiQB includes a read-only validator:

```bash
python3 skills/kimiqb/scripts/validate_planner_docs.py --root /path/to/project --mode step1
python3 skills/kimiqb/scripts/validate_planner_docs.py --root /path/to/project --mode autopsy --strict
python3 skills/kimiqb/scripts/validate_planner_docs.py --root /path/to/project --mode step2 --strict
python3 skills/kimiqb/scripts/validate_planner_docs.py --root /path/to/project --mode step3 --strict
python3 skills/kimiqb/scripts/validate_planner_docs.py --root /path/to/project --mode step4
```

The validator checks required sections, optional ontology/ledger headings, phase folders, filename conventions, index references, duplicate numbering, unindexed files, length-bounded secret patterns, and Step 4 readiness. P0/P1 audit findings block the implementation handoff.

Repository maintainers can run the dependency-free package check with:

```bash
make check
```

Inside a git checkout, `make check` performs tracked-file secret hygiene and archive hygiene. In an extracted package without `.git/`, it falls back to package-level filesystem hygiene and prints explicit package-mode labels.

## Safety Model

KimiQB is planning-first. Steps 1-3 should not:

- implement product features;
- refactor source code;
- install dependencies;
- run destructive commands;
- commit, push, deploy, or open pull requests;
- write secrets, tokens, credentials, private keys, or local sensitive environment values into planning files.

Generated plans should distinguish documentation readiness, local readiness, live readiness, production readiness, and operational evidence.

## Repository Layout

```text
kimi.plugin.json
.github/workflows/validate.yml
Makefile
skills/kimiqb/
  SKILL.md
  scripts/validate_planner_docs.py
  references/
    First-Planner.md
    Autopsy-Planner.md
    Second-Planner.md
    Third-Planner.md
    Fourth-Planner.md
    repo-aware-intake.md
    workflow-quality.md
    vibecoding-principles.md
    subagent-playbook.md
    planning-ledger.md
    project-ontology.md
    assessment-and-budget.md
    engineering-principles.md
docs/
  INSTALLATION.md
  MAINTAINING.md
  USAGE.md
scripts/
  adapt_from_codexqb.py
  validate.sh
tests/
LICENSE
README.md
```

## Documentation

- [Installation](docs/INSTALLATION.md)
- [Usage](docs/USAGE.md)
- [Maintaining KimiQB](docs/MAINTAINING.md)

## License

MIT. See [LICENSE](LICENSE).
