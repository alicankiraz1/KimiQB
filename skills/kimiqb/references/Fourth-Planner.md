# Step 4 Implementation Handoff Prompt Template

This reference is not an auto-executed KimiQB planning step.

Use it only after Step 3 writes `Planner-docs/Sub-Planing-Audit.md` and the audit says Step 4 can begin. Print the copy block below for the user to paste into a new Kimi Code session.

If the audit status is `BLOCKED`, do not print this prompt. Print the minimal unblock prompt from the audit instead.

If the audit status is `PASS_WITH_WARNINGS` and any P0/P1 finding exists, do not print this prompt. Print a repair prompt targeting those P0/P1 findings first.

If the audit status is `PASS_WITH_WARNINGS` with only P2/P3 findings, this prompt may be printed, but state that the implementation run must keep those warnings visible.

## Copy Block

```text
Planner-docs/Main-Planing.md, Planner-docs/Sub-Planing-Index.md, Planner-docs/Sub-Planing-Audit.md ve Planner-docs/Faz-*-Plans/*.md dosyalarını kaynak kabul et. Audit içindeki ilk READY veya READY_WITH_WARNINGS alt planı seç; P0/P1 audit bulgusu varsa uygulamaya geçmeden dur ve onarım promptu öner.

if installed/available, use relevant Kimi Code skills/plugins by scope: implementation için superpowers:executing-plans veya superpowers:subagent-driven-development, kod değişikliklerinde superpowers:test-driven-development, bitirmeden önce superpowers:verification-before-completion, güvenlik/policy/secret/command execution işleri için security-focused Kimi-compatible skills/plugins. Bu beceriler/eklentiler yüklü değilse durma; continue using the audit, seçilen alt plan, repo talimatları ve mevcut doğrulama komutlarıyla aynı prensipleri uygula. GitHub publish/PR işleri sadece açıkça istendiğinde kullan.

Tek seferde bir küçük, geri alınabilir, testlenebilir geliştirme dilimi uygula. Önce git status, README.md, AGENTS.md, Makefile, audit ve seçilen alt planı oku. Testi veya doğrulama komutunu önce belirle; minimal değişikliği yap; odaklı testleri ve ilgili make smoke/check hedefini çalıştır; sonucu exact blocker/success olarak raporla. Secret, token, private key veya local credential yazma. Token kullanımına dikkat et: tüm alt planları context’e yükleme, index/audit ile yön bul, sadece seçilen alt planı ve gerekli dosyaları oku.
```

## Operator Notes

- Keep the implementation run scoped to one sub-plan and one reversible slice.
- Do not load every sub-plan into context unless the audit requires cross-plan repair.
- Prefer existing repo validation commands over invented commands.
- Report exact blocker strings and separate code-delivery status from external config or credential blockers.
- Do not commit, push, open a PR, deploy, or mutate external systems unless the user explicitly asks in the Step 4 run.
