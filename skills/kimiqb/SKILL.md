---
name: kimiqb
description: Repo-aware project planning workflow for Kimi Code. Use to create Planner-docs/Main-Planing.md, run an existing-project autopsy, decompose phases into sub-plans, audit readiness, and print a gated implementation handoff.
type: prompt
whenToUse: When the user asks Kimi Code to plan a software, AI, infrastructure, security, automation, or product repository before implementation.
disableModelInvocation: false
---

# KimiQB

## Overview

Run the bundled planning workflow for a project repository. Keep Step 1 conversational and repo-aware, run Step 1.5 Autopsy for existing projects, and hand off Step 2 and Step 3 as copy-ready prompts for a new Kimi Code session unless the user explicitly asks for a direct run. After Step 3, provide a gated Step 4 implementation handoff prompt only when the audit says implementation can begin.

The bundled prompts are:

- `${KIMI_SKILL_DIR}/references/First-Planner.md` for Step 1 main planning.
- `${KIMI_SKILL_DIR}/references/Autopsy-Planner.md` for Step 1.5 existing-project autopsy.
- `${KIMI_SKILL_DIR}/references/Second-Planner.md` for Step 2 phase sub-planning.
- `${KIMI_SKILL_DIR}/references/Third-Planner.md` for Step 3 sub-plan QA and coverage audit.
- `${KIMI_SKILL_DIR}/references/Fourth-Planner.md` for the Step 4 implementation handoff prompt template.

Bundled support files:

- `${KIMI_SKILL_DIR}/scripts/validate_planner_docs.py` for read-only structural validation of `Planner-docs/`.
- `${KIMI_SKILL_DIR}/references/repo-aware-intake.md` for evidence-backed Step 1 intake questions.
- `${KIMI_SKILL_DIR}/references/workflow-quality.md` for reliability, validation, token discipline, and handoff practices.

## Workflow Selection

1. If the user asks for normal planner startup, run Step 1.
2. If the user directly asks for Step 1.5 or Autopsy, read `${KIMI_SKILL_DIR}/references/Autopsy-Planner.md` and execute it.
3. If the user directly asks for Step 2, read `${KIMI_SKILL_DIR}/references/Second-Planner.md` and execute it.
4. If the user directly asks for Step 3, read `${KIMI_SKILL_DIR}/references/Third-Planner.md` and execute it.
5. If the user asks only for prompt text, print the matching Step 2, Step 3, or gated Step 4 copy block without modifying files.

Do not run migration workflows for this package. This is a native Kimi Code skill workflow.

## Step 1 Intake

Read `${KIMI_SKILL_DIR}/references/repo-aware-intake.md` before asking questions.

Before asking `PROJECT_NAME`, do a bounded, read-only repository scan so the intake can suggest evidence-backed defaults. Then ask these four fields one at a time in the user's language, using plain text questions only:

1. `PROJECT_NAME`: project name, with an inferred default when possible.
2. `PROJECT_INTENT`: what the project is for and what it should become, with a repo-derived draft when possible.
3. `TARGET_END_STATE`: what done looks like from product, engineering, operations, security, and user-value perspectives, with a five-part draft when possible.
4. `KNOWN_CONSTRAINTS`: team size, infrastructure, budget, timeline, preferred stack, compliance boundaries, must-use tools, and must-not-use tools, with detected constraints and unknowns when possible.

After all four values are available:

1. Read `${KIMI_SKILL_DIR}/references/First-Planner.md`.
2. Substitute the four collected values into the matching placeholders.
3. Follow the substituted Step 1 prompt exactly.
4. Create or update only `Planner-docs/Main-Planing.md`, as required by the Step 1 prompt.
5. After completing Step 1, decide whether Step 1.5 Autopsy applies.
6. Run Step 1.5 automatically only when the repository is an existing or partially built project with meaningful evidence such as README, manifests, source/service/package directories, tests, docs, configs, or CI.
7. Skip Step 1.5 for new or nearly empty projects; do not create `Planner-docs/Autopsy.md` in that case.
8. After Step 1 and any Step 1.5 Autopsy work, ask the user in plain text whether they have feedback for the main plan and autopsy.
9. If feedback is provided, apply it under the same file boundary: update only `Planner-docs/Main-Planing.md` for main plan feedback and only `Planner-docs/Autopsy.md` for autopsy feedback.

## Step 1.5 Autopsy

Step 1.5 is for existing or partially built projects. It should not run for genuinely new or nearly empty repositories.

When Step 1.5 applies:

1. Read `${KIMI_SKILL_DIR}/references/Autopsy-Planner.md`.
2. Read `Planner-docs/Main-Planing.md`.
3. Inspect the repository with read-only commands.
4. Create or update only `Planner-docs/Autopsy.md`.
5. Do not modify source files, `Planner-docs/Main-Planing.md`, or any Step 2/3 files.
6. Treat `Autopsy.md` as Step 2 feedback, not as a replacement for the main plan.

## Step 2 Handoff

After Step 1 feedback is handled, ask whether the user wants to continue to Step 2. If yes, tell the user to copy this text into a new Kimi Code session:

```text
/skill:kimiqb Step 2'yi references/Second-Planner.md talimatlarına göre yürüt.

Planner-docs/Main-Planing.md dosyasındaki tüm ana fazları oku. Planner-docs/Autopsy.md varsa onu da destekleyici feedback kaynağı olarak tamamen oku ve alt faz planlarında dikkate al. Her faz için Planner-docs altında Faz-<n>-Plans klasörleri ve Faz<n>.<m>-*.md detaylı alt plan dosyaları oluştur. Tüm fazlar kapsanmadan durma. Sadece Planner-docs altında değişiklik yap.
```

When executing Step 2 directly:

1. Read `${KIMI_SKILL_DIR}/references/Second-Planner.md`.
2. Read `${KIMI_SKILL_DIR}/references/workflow-quality.md`.
3. Read `Planner-docs/Autopsy.md` when it exists; do not block Step 2 when it is absent.
4. Follow repository inspection, file-boundary, naming, all-file validation, and stopping rules exactly.
5. Run `${KIMI_SKILL_DIR}/scripts/validate_planner_docs.py --root . --mode step2 --strict` after generation when available. If no script path is accessible, perform equivalent all-file validation and report that fallback clearly.
6. Do not modify files outside `Planner-docs/`.
7. After the Step 2 summary, print the Step 3 handoff block from this skill.

## Step 3 Handoff

After Step 2 is complete, ask whether the user wants to continue to Step 3. If yes, tell the user to copy this text into a new Kimi Code session:

```text
/skill:kimiqb Step 3'ü references/Third-Planner.md talimatlarına göre yürüt.

Planner-docs/Main-Planing.md, Planner-docs/Sub-Planing-Index.md ve Planner-docs/Faz-*-Plans/*.md dosyalarını denetle. Ana faz coverage, dosya isimlendirme, sıralama, zorunlu bölüm yapısı, index tutarlılığı, içerik kalitesi, scope drift, readiness gerçekçiliği, güvenlik/governance ve Step 4 hazırlığını analiz et. Hiçbir plan dosyasını düzeltme; yalnızca Planner-docs/Sub-Planing-Audit.md raporunu üret. Tüm fazlar ve alt planlar incelenmeden durma.
```

When executing Step 3 directly:

1. Read `${KIMI_SKILL_DIR}/references/Third-Planner.md`.
2. Read `${KIMI_SKILL_DIR}/references/workflow-quality.md`.
3. Run `${KIMI_SKILL_DIR}/scripts/validate_planner_docs.py --root . --mode step3 --strict` first when available and incorporate its findings into the audit. If no script path is accessible, perform equivalent all-file validation and report that fallback clearly.
4. Follow audit, file-boundary, validation, and stopping rules exactly.
5. Modify only `Planner-docs/Sub-Planing-Audit.md`.
6. After the Step 3 summary, print the Step 4 handoff prompt from `${KIMI_SKILL_DIR}/references/Fourth-Planner.md` only if the audit permits implementation.

## Step 4 Handoff

Step 4 is not a KimiQB planning step and must not be executed automatically by this skill.

When Step 3 completes:

1. Read `${KIMI_SKILL_DIR}/references/Fourth-Planner.md`.
2. Run `${KIMI_SKILL_DIR}/scripts/validate_planner_docs.py --root . --mode step4` when available. If no script path is accessible, perform equivalent all-file validation and report that fallback clearly.
3. If validation passes, print the Step 4 copy block and remind the user to watch token use.
4. If validation fails because the audit is `BLOCKED` or contains P0/P1 findings, do not print the Step 4 prompt; print the minimal repair or unblock prompt instead.
5. If validation passes with non-blocking warnings, print the Step 4 prompt and state that the implementation run must keep P2/P3 warnings visible.

## Quality and Validation

- Prefer `${KIMI_SKILL_DIR}/scripts/validate_planner_docs.py` over ad hoc validation scripts.
- Use `--mode step1`, `--mode step2`, `--mode step3`, or `--mode step4` for the active workflow step.
- Use `--strict` in long-running Kimi Code sessions so generic or repeated section warnings become failures.
- Do not report section counts from memory; report counts only after reading the active prompt or running validation.
- For untracked `Planner-docs/`, use `find Planner-docs -maxdepth 4 -type f | sort`, `git status --short -- Planner-docs`, and `git diff -- Planner-docs` together.
- Keep long stdout concise. Put detailed evidence in the generated Markdown artifacts.

## Safety Rules

- Treat the current working directory as the project being planned.
- Inspect the repository before writing any planning file, using the safe read-only commands required by the active planner prompt.
- Do not implement product features, refactor source code, install dependencies, commit, push, deploy, or open pull requests during Steps 1-3.
- Do not write secrets, tokens, credentials, private keys, or local sensitive environment values into planning files.
- Preserve the required misspelled filenames exactly: `Main-Planing.md`, `Sub-Planing-Index.md`, and `Sub-Planing-Audit.md`.
- Preserve `Planner-docs/Autopsy.md` as the Step 1.5 autopsy filename.
- If a required source file is missing, follow the blocker behavior in the active planner prompt instead of inventing speculative output.

## Completion Reporting

For each executed step, report concisely:

- which planner step ran;
- which files were created or updated;
- whether the step succeeded or was blocked;
- the highest-priority next action;
- any uncertainty or blocker discovered.
