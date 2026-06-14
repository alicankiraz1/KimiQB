# Repo-Aware Step 1 Intake

Use this reference before `First-Planner.md` when KimiQB starts a normal Step 1 planning run.

The goal is to ask the same four required fields, but make the questions active, evidence-backed, and useful for an existing repository.

## Boundaries

- Ask in the user's language.
- Ask one question at a time.
- Use plain text only. Do not use pop-ups, forms, or multiple-choice UI.
- Do not write files during intake.
- Do not run networked, destructive, install, commit, push, deploy, or PR commands.
- Treat the current working directory as the project repository.
- Make it clear when a statement is inferred from repo evidence.
- If evidence is weak, say that repo evidence is limited and ask the concise generic version of the question.

## Pre-Intake Scan

Before asking `PROJECT_NAME`, inspect the repository with a bounded read-only pass.

Prefer commands like:

```bash
pwd
git status --short --branch
git branch --show-current
find . -maxdepth 2 \( -path './.git' -o -path './node_modules' -o -path './.venv' -o -path './dist' -o -path './build' -o -path './artifacts' \) -prune -o -type f -print | sort | head -120
find . -maxdepth 2 \( -path './.git' -o -path './node_modules' -o -path './.venv' -o -path './dist' -o -path './build' -o -path './artifacts' \) -prune -o -type d -print | sort | head -80
ls
```

Read likely evidence files when they exist:

- `README.md`
- `AGENTS.md`
- `Makefile`
- `package.json`
- `pyproject.toml`
- `Cargo.toml`
- `go.mod`
- `docker-compose.yml` or `compose.yml`
- `.github/workflows/*.yml`
- `docs/` index, architecture, roadmap, runbook, deployment, security, or testing files
- top-level service, package, app, config, script, test, and infra directories

Use `rg` only for targeted discovery when useful:

```bash
rg -n "architecture|roadmap|runbook|production|security|policy|workflow|worker|scheduler|gateway|adapter|dashboard|test|smoke|deploy|Kubernetes|Docker|Postgres|queue|approval|audit|artifact|observability" . --glob '!.git/**' --glob '!node_modules/**' --glob '!.venv/**' --glob '!dist/**' --glob '!build/**' --glob '!artifacts/**'
```

Keep this pass brief. Its purpose is to make the intake questions smarter, not to replace the full repository analysis in `First-Planner.md`.

## What To Infer

Infer a draft answer only when there is evidence.

- `PROJECT_NAME`: prefer README title, package/app name, repository directory name, product docs, or manifest names.
- `PROJECT_INTENT`: infer what the project does, its target users, main components, integrations, and what it seems to be trying to become.
- `TARGET_END_STATE`: draft the "done" state across product, engineering, operations, security, and user value.
- `KNOWN_CONSTRAINTS`: infer stack, deployment model, test commands, CI, compliance/security boundaries, must-use tools, must-not-use tools, timeline hints, and unknown constraints that need user confirmation.

Do not treat inferred values as final until the user confirms or edits them.

## Question Style

Start with a short setup sentence:

```text
Önce 4 kısa soruyu tek tek soracağım. Soruları depoda gördüğüm kanıtlara göre zenginleştireceğim; cevaplarından sonra ana planı üreteceğim.
```

Translate this sentence to the user's language when the user is not writing in Turkish.

### Soru 1 / 4 - PROJECT_NAME

Use this shape:

```text
Soru 1 / 4 - PROJECT_NAME (Proje Adı)

Bu planın hangi proje için hazırlanacağını netleştirelim.

Depoda gördüğüm kadarıyla bu proje "<inferred name>" gibi görünüyor. Kanıt: <short evidence such as README title, package name, or repo folder>.

Proje adını "<inferred name>" olarak alabilir miyim, yoksa farklı/resmi bir ad mı kullanmamı istersin?
```

If evidence is weak:

```text
Soru 1 / 4 - PROJECT_NAME (Proje Adı)

Repo kanıtı sınırlı, bu yüzden proje adını senden netleştirmem gerekiyor.

Bu plan hangi proje adıyla hazırlanmalı?
```

After the answer, confirm:

```text
PROJECT_NAME = "<final value>" olarak kaydedildi.
```

### Soru 2 / 4 - PROJECT_INTENT

Use this shape:

```text
Soru 2 / 4 - PROJECT_INTENT (Projenin Amacı)

Bu alan, projenin ne için var olduğunu ve neye dönüşmek istediğini açıklar.

Depodan çıkardığım taslak şu:

<1-2 concise paragraphs describing inferred intent, components, target users, and direction.>

Sorular:

1. Bu tanım doğru mu, yoksa düzeltmek/eklemek istediğin noktalar var mı?
2. Projenin dönüşmek istediği nihai hedef nedir?

Kısa birkaç cümleyle yazabilirsin; ben bunu plana profesyonelce işleyeceğim.
```

After the answer, confirm the stored value in one sentence:

```text
PROJECT_INTENT kaydedildi: <brief normalized summary>.
```

### Soru 3 / 4 - TARGET_END_STATE

Use this shape:

```text
Soru 3 / 4 - TARGET_END_STATE (Hedef Son Durum / "Bitti" Tanımı)

"Done" tanımını beş açıdan netleştirmek istiyorum. Depo kanıtına göre hazırladığım taslak:

- Ürün: <product outcome>
- Mühendislik: <engineering outcome>
- Operasyon: <operations outcome>
- Güvenlik: <security outcome>
- Kullanıcı değeri: <user-value outcome>

Bu beş boyut senin "bitti" tanımını yansıtıyor mu? Eklemek, çıkarmak veya değiştirmek istediğin bir şey var mı?
```

After the answer, confirm:

```text
TARGET_END_STATE kaydedildi: <brief normalized summary>.
```

### Soru 4 / 4 - KNOWN_CONSTRAINTS

Use this shape:

```text
Soru 4 / 4 - KNOWN_CONSTRAINTS (Bilinen Kısıtlar)

Depodan gördüğüm veya henüz net olmayan kısıt taslağı:

- Stack/araçlar: <detected stack or unknown>
- Operasyon/infra: <detected deployment/runtime or unknown>
- Test/doğrulama: <detected commands or unknown>
- Güvenlik/compliance: <detected boundaries or unknown>
- Zaman/ekip/bütçe: <known if present, otherwise unknown>
- Must-use / must-not-use: <known if present, otherwise unknown>

Bu listeye eklemem, düzeltmem veya özellikle kaçınmam gereken bir şey var mı?
```

After the answer, confirm:

```text
KNOWN_CONSTRAINTS kaydedildi: <brief normalized summary>.
```

## After Intake

When all four fields are confirmed:

1. Read `references/First-Planner.md`.
2. Substitute the confirmed field values.
3. Treat user-confirmed field values as source of truth.
4. Treat repo-inferred intake notes as supporting context only.
5. Continue with the full Step 1 repository analysis required by `First-Planner.md`.
