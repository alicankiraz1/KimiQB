# Usage

KimiQB runs a vibecoding-first repo-aware planning workflow with optional Step 1.5 Autopsy, optional project comprehension, ontology memory, Ledger v2 continuity, and gated implementation handoffs.

For large repositories, KimiQB may use subagent-aware guidance to separate exploration, readiness/security audit, implementation-path discovery, and review while the parent session owns final artifact writes.

Package contract:

- `artifact_schema_version: 2`
- `handoff_contract_version: 1`

KimiQB asks intake questions in the user's language when practical. Generated Planner-docs artifacts are English by default unless the user explicitly requests another content language. Required document headings remain English for validator stability.

## Step 1: Main Plan

Open the project repository you want Kimi Code to analyze and ask:

```text
/skill:kimiqb inspect this repo and plan this project
```

KimiQB first performs a bounded read-only scan of the current repository. It may inspect files such as `README.md`, `AGENTS.md`, manifests, CI workflows, docs indexes, deployment files, tests, service directories, and existing continuity files:

```text
Planner-docs/Planing-Ledger.md
Planner-docs/Project-Ontology.md
Planner-docs/Project-Comprehension.md
```

It then asks four intake questions, one at a time:

- `PROJECT_NAME`
- `PROJECT_INTENT`
- `TARGET_END_STATE`
- `KNOWN_CONSTRAINTS`

After the answers are collected, KimiQB creates or updates:

```text
Planner-docs/Main-Planing.md
```

Step 1 is allowed to modify only that file unless the user explicitly asks for a continuity note.

## Step 1.5: Existing Project Autopsy

For existing or partially built repositories, KimiQB runs `Autopsy-Planner.md` after Step 1.

Expected outputs:

```text
Planner-docs/Autopsy.md
Planner-docs/Project-Ontology.md
Planner-docs/Project-Comprehension.md
```

`Project-Comprehension.md` is optional and should be created when the repository is non-trivial enough to need durable evidence, confidence, traceability, architecture reflexion, quality scenario, and open hypothesis records. Empty or nearly empty repositories skip Step 1.5.

Manual autopsy validation:

```bash
python3 skills/kimiqb/scripts/validate_planner_docs.py --root /path/to/project --mode autopsy --strict
```

## Step 2: Phase Sub-Plans

After Step 1 feedback is handled, KimiQB prints or returns the canonical Step 2 handoff:

```text
/skill:kimiqb Read and return the exact canonical handoff from references/handoffs/run-step2.md, then execute it.
```

The handoff contract lives in:

```text
skills/kimiqb/references/handoffs/run-step2.md
```

Expected outputs:

```text
Planner-docs/Sub-Planing-Index.md
Planner-docs/Faz-<n>-Plans/Faz<n>.<m>-*.md
```

Step 2 is allowed to modify only files under `Planner-docs/`. It should treat Autopsy, Ontology, Comprehension, and Ledger files as evidence, not as unquestioned truth.

Manual validation:

```bash
python3 skills/kimiqb/scripts/validate_planner_docs.py --root /path/to/project --mode step2 --strict
```

## Step 3: Sub-Plan QA Audit

After Step 2, KimiQB prints or returns the canonical Step 3 handoff:

```text
/skill:kimiqb Read and return the exact canonical handoff from references/handoffs/run-step3.md, then execute it.
```

The handoff contract lives in:

```text
skills/kimiqb/references/handoffs/run-step3.md
```

Before writing the audit, run the preflight when available:

```bash
python3 skills/kimiqb/scripts/validate_planner_docs.py --root /path/to/project --mode step3-preflight --strict
```

Expected output:

```text
Planner-docs/Sub-Planing-Audit.md
```

Step 3 audits coverage, naming, sequencing, required section structure, index consistency, evidence quality, confidence calibration, trace coverage, architecture drift, ontology consistency, planning-history continuity, security/governance, and Step 4 readiness. It reports problems but does not repair sub-plans.

Post-audit validation:

```bash
python3 skills/kimiqb/scripts/validate_planner_docs.py --root /path/to/project --mode step3 --strict
```

## Step 4: Gated Implementation Handoff

Step 4 is not executed by KimiQB during planning. KimiQB may print the canonical Step 4 handoff only when the audit allows implementation:

```text
/skill:kimiqb Read and return the exact canonical handoff from references/handoffs/run-step4.md, then execute it.
```

The handoff contract lives in:

```text
skills/kimiqb/references/handoffs/run-step4.md
```

Readiness check:

```bash
python3 skills/kimiqb/scripts/validate_planner_docs.py --root /path/to/project --mode step4
```

Step 4 may proceed when the audit status is `PASS`, or `PASS_WITH_WARNINGS` with no P0/P1 findings. It must not start implementation when the audit is `BLOCKED`, has P0/P1 findings, uses unsafe target paths, requires Ledger v2 migration before execution, or reports `NO_ACTION_REQUIRED`.

Semantic queue statuses:

- `READY`
- `READY_WITH_WARNINGS`
- `BLOCKED`
- `COMPLETE`
- `SUPERSEDED`
- `DEFERRED`
- `NO_ACTION_REQUIRED`

When implementation does run, it should append or update `Planner-docs/Planing-Ledger.md` with concise verified-slice or stop-event summaries. The ledger is a replanning memory artifact, not a transcript dump.

## Direct Step Invocation

You can invoke a step directly when the required `Planner-docs/` inputs already exist:

```text
/skill:kimiqb run Step 1.5 Autopsy for this existing project
```

```text
/skill:kimiqb run Step 2 on the existing Planner-docs/Main-Planing.md
```

```text
/skill:kimiqb run Step 3 and audit the existing sub-plans
```

```text
/skill:kimiqb print the Step 4 implementation handoff prompt if the audit allows it
```

## Validator Output

The validator prints deterministic summary lines such as:

```text
planner_docs_validation=passed
mode=step2
phase_folder_count=9
subplan_count=35
warning_count=0
error_count=0
```

It exits nonzero on structural failures. With `--strict`, repeated or generic section warnings are treated as failures. Secret scanning uses length-bounded token patterns so normal filenames such as `task-spec.yaml` are not flagged.

## Fixture Corpus

Maintainers can run the deterministic fixture corpus without invoking Kimi Code:

```bash
python3 evals/run_fixture_corpus_checks.py
```

The fixture corpus keeps expected comprehension signals, trace IDs, architecture statuses, and quality checks stable for future live evaluations.

## Safety Expectations

KimiQB is not an implementation tool during Steps 1-3. If required source files or planner outputs are missing, it should follow the blocker behavior in the active planner prompt instead of inventing speculative output.
