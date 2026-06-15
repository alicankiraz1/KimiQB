# Usage

KimiQB runs a vibecoding-first repo-aware planning workflow with an optional Step 1.5 Autopsy for existing projects, optional ontology memory, optional planning ledger continuity, and a gated implementation handoff.

KimiQB asks intake questions in the user's language when practical. Generated Planner-docs artifacts are English by default unless the user explicitly requests another body language. Required document headings remain English for validator stability.

## Step 1: Main Plan

Open the project repository you want Kimi Code to analyze and ask:

```text
/skill:kimiqb inspect this repo and plan this project
```

KimiQB first performs a bounded read-only scan of the current repository. It may inspect files such as `README.md`, `AGENTS.md`, manifests, CI workflows, docs indexes, deployment files, tests, top-level service directories, and existing `Planner-docs/Planing-Ledger.md` or `Planner-docs/Project-Ontology.md` when present.

Then it asks four intake questions, one at a time:

- `PROJECT_NAME`: the project name.
- `PROJECT_INTENT`: what the project is for and what it should become.
- `TARGET_END_STATE`: what done looks like across product, engineering, operations, security, and user value.
- `KNOWN_CONSTRAINTS`: team, infrastructure, budget, timeline, stack, compliance, must-use tools, must-not-use tools, desired autonomy level, human review cadence, and token/context budget.

For existing repositories, the questions should include repo-derived defaults or draft summaries. For empty or minimal repositories, KimiQB should clearly say repository evidence is limited and ask the concise generic version of each question.

After the answers are collected, KimiQB loads `First-Planner.md`, substitutes the values, inspects the repository, and creates or updates:

```text
Planner-docs/Main-Planing.md
```

Step 1 is allowed to modify only that file.

## Step 1.5: Existing Project Autopsy

When the target repository is an existing or partially built project, KimiQB runs `Autopsy-Planner.md` after Step 1.

Expected outputs:

```text
Planner-docs/Autopsy.md
Planner-docs/Project-Ontology.md
```

The Autopsy report analyzes project sections, feature inventory, placeholders/stubs/skeletons, technical debt, missing or broken integrations, test and CI gaps, security/governance issues, operational readiness, and alignment with `Planner-docs/Main-Planing.md`. When repository evidence is strong enough, `Project-Ontology.md` captures vocabulary, entities, workflows, module boundaries, integrations, invariants, and open ontology questions.

Step 1.5 is skipped for empty or nearly empty repositories. In that case, `Autopsy.md` and `Project-Ontology.md` are not required and Step 2 should continue without them.

Manual autopsy validation:

```bash
python3 skills/kimiqb/scripts/validate_planner_docs.py --root /path/to/project --mode autopsy --strict
```

## Step 2: Phase Sub-Plans

After Step 1, KimiQB prints a text block for a new Kimi Code session. Copy it into a fresh session when you want long-running phase decomposition:

```text
/skill:kimiqb Run Step 2 according to references/Second-Planner.md.

Read all main phases in Planner-docs/Main-Planing.md. If Planner-docs/Autopsy.md, Planner-docs/Project-Ontology.md, or Planner-docs/Planing-Ledger.md exists, read it fully as supporting evidence and account for it in the sub-phase plans. Plan in a vibecoding-first style: small reversible slices, fast validation signals, explicit deferrals, security boundaries, and long-running Kimi Code session readiness. For each phase, create Faz-<n>-Plans folders and detailed Faz<n>.<m>-*.md sub-plan files under Planner-docs. Do not stop until all phases are covered. Modify only Planner-docs.
```

Expected outputs:

```text
Planner-docs/Sub-Planing-Index.md
Planner-docs/Faz-<n>-Plans/Faz<n>.<m>-*.md
```

Step 2 is allowed to modify only files under `Planner-docs/`. It should treat Autopsy, Ontology, and Ledger files as evidence, not as unquestioned truth.

At the end of Step 2, KimiQB should run the bundled validator or an equivalent all-file validation, summarize the result, and print the Step 3 handoff block. Do not rely on sampled reads alone for Step 2 structure checks.

Manual validation from a KimiQB repository checkout:

```bash
python3 skills/kimiqb/scripts/validate_planner_docs.py --root /path/to/project --mode step2 --strict
```

## Step 3: Sub-Plan QA Audit

After Step 2, KimiQB prints another text block for a new Kimi Code session:

```text
/skill:kimiqb Run Step 3 according to references/Third-Planner.md.

Audit Planner-docs/Main-Planing.md, Planner-docs/Sub-Planing-Index.md, Planner-docs/Faz-*-Plans/*.md, and any supporting Planner-docs/Autopsy.md, Planner-docs/Project-Ontology.md, or Planner-docs/Planing-Ledger.md. Analyze main-phase coverage, file naming, sequencing, required section structure, index consistency, content quality, scope drift, readiness realism, ontology consistency, planning-history continuity, security/governance, vibecoding slice quality, and Step 4 readiness. Do not fix any plan files; produce only Planner-docs/Sub-Planing-Audit.md. Do not stop until all phases and sub-plans have been reviewed.
```

Expected output:

```text
Planner-docs/Sub-Planing-Audit.md
```

Step 3 is an audit step. It reports problems but does not fix the sub-plans.

Manual validation:

```bash
python3 skills/kimiqb/scripts/validate_planner_docs.py --root /path/to/project --mode step3 --strict
```

If the validator exits nonzero because it found structural issues, Step 3 should still write the audit unless required source files are missing.

## Step 4: Gated Implementation Handoff

After Step 3, KimiQB may print a Step 4 implementation prompt. This prompt is for a separate implementation session; KimiQB itself does not implement product changes during Steps 1-3.

KimiQB should print the Step 4 prompt only when:

- `Planner-docs/Sub-Planing-Audit.md` exists;
- the audit status is `PASS`, or `PASS_WITH_WARNINGS` with no P0/P1 findings;
- the Step 4 validator passes.

Manual readiness check:

```bash
python3 skills/kimiqb/scripts/validate_planner_docs.py --root /path/to/project --mode step4
```

If the audit is `BLOCKED` or contains P0/P1 findings, repair the planning package first. If only P2/P3 warnings remain, the implementation prompt may be used but the warnings should stay visible.

The implementation handoff tells Kimi Code to use relevant skills/plugins by scope, use subagents only when they reduce context pollution or separate evidence gathering from implementation/review, execute the READY/READY_WITH_WARNINGS queue continuously in small reversible slices, test before or with code changes, report exact blockers, avoid secrets, and limit token use by reading the audit/index first and only the active sub-plan afterward.

Step 4 should append or update `Planner-docs/Planing-Ledger.md` with concise verified-slice or stop-event summaries. The ledger is a replanning memory artifact, not a transcript dump.

Step 4 should not stop after the first successful slice. It should continue to the next acceptance criterion or next eligible sub-plan until the queue is complete or a stop gate is hit, such as a P0/P1 finding, failing test, missing source file, required credential/live approval, unsafe external mutation, unrelated dirty worktree, or token/context budget pressure.

## Direct Step Invocation

You can invoke Step 2 or Step 3 directly:

```text
/skill:kimiqb run Step 2 on the existing Planner-docs/Main-Planing.md
```

```text
/skill:kimiqb run Step 3 and audit the existing sub-plans
```

You can invoke Step 1.5 directly when a main plan already exists:

```text
/skill:kimiqb run Step 1.5 Autopsy for this existing project
```

You can ask for the Step 4 prompt text after a completed audit:

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

## Safety Expectations

KimiQB is not an implementation tool. It is designed to produce planning artifacts only during Steps 1-3.

If KimiQB finds missing source files or missing planner outputs, it should follow the blocker behavior in the active planner prompt instead of inventing speculative output.
