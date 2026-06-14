# Step 4 Implementation Handoff Prompt Template

This reference is not an auto-executed KimiQB planning step.

Use it only after Step 3 writes `Planner-docs/Sub-Planing-Audit.md` and the audit says Step 4 can begin. Print the copy block below for the user to paste into a new Kimi Code session.

If the audit status is `BLOCKED`, do not print this prompt. Print the minimal unblock prompt from the audit instead.

If the audit status is `PASS_WITH_WARNINGS` and any P0/P1 finding exists, do not print this prompt. Print a repair prompt targeting those P0/P1 findings first.

If the audit status is `PASS_WITH_WARNINGS` with only P2/P3 findings, this prompt may be printed, but state that the implementation run must keep those warnings visible.

## Copy Block

```text
Treat Planner-docs/Main-Planing.md, Planner-docs/Sub-Planing-Index.md, Planner-docs/Sub-Planing-Audit.md, and Planner-docs/Faz-*-Plans/*.md as source material. Build an ordered implementation queue from the audit's READY and READY_WITH_WARNINGS rows, preserving the index order. If the audit contains P0/P1 findings, stop before implementation and propose a repair prompt.

if installed/available, use relevant Kimi Code skills/plugins by scope: implementation için superpowers:executing-plans veya superpowers:subagent-driven-development, kod değişikliklerinde superpowers:test-driven-development, bitirmeden önce superpowers:verification-before-completion, güvenlik/policy/secret/command execution işleri için security-focused Kimi-compatible skills/plugins. Bu beceriler/eklentiler yüklü değilse durma; continue using the audit, seçilen alt plan, repo talimatları ve mevcut doğrulama komutlarıyla aynı prensipleri uygula. GitHub publish/PR işleri sadece açıkça istendiğinde kullan.

Execute the queue continuously in this long-running Kimi Code session. For each active sub-plan, implement one small, reversible, testable improvement slice at a time. First read git status, README.md, AGENTS.md, Makefile, the audit, the index, and only the active sub-plan plus required repo files. Identify the test or validation command before editing; make the minimal change; run focused tests and the relevant make smoke/check target; report the result as an exact blocker or success. After a slice passes, continue to the next acceptance criterion or the next READY/READY_WITH_WARNINGS sub-plan instead of stopping.

Stop only when one of these stop gates is hit: P0/P1 or safety/security finding; failing test or unresolved regression; missing required source file; unclear contradiction between plan, audit, and repo reality; credential/live-environment/human-approval requirement; destructive external mutation requirement; unrelated dirty worktree or merge conflict; validation command unavailable with no equivalent fallback; token/context budget too low to continue safely; or the user explicitly asks to stop. When stopping, write a concise handoff summary with completed slices, changed files, verification commands, blocker text, and the next queue item.

Do not write secrets, tokens, private keys, or local credentials. Watch token use: do not load every sub-plan into context; use the index/audit to navigate, read only the active sub-plan, and refresh queue status from the audit/index between slices. If context compaction or budget pressure is likely, summarize progress and continue only when the next slice can still be executed safely.
```

## Operator Notes

- Keep each implementation slice small and reversible, but continue through the ordered queue after each verified slice.
- Do not load every sub-plan into context unless the active slice requires cross-plan repair.
- Prefer existing repo validation commands over invented commands.
- Report exact blocker strings and separate code-delivery status from external config or credential blockers.
- Do not commit, push, open a PR, deploy, or mutate external systems unless the user explicitly asks in the Step 4 run.
