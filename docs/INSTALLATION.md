# Installation

KimiQB is distributed as a Kimi Code plugin repository.

## Requirements

- Kimi Code CLI with plugin support.
- A new Kimi Code session after installation so `/skill:kimiqb` is loaded into context.
- GitHub access to `alicankiraz1/KimiQB` when installing from GitHub.

## Install From A Local Checkout

Open Kimi Code in any project and run:

```text
/plugins install /path/to/KimiQB
/plugins info kimiqb
/plugins reload
/new
```

Then test the skill:

```text
/skill:kimiqb inspect this repo and plan this project
```

The installed skill should mention vibecoding-first planning, optional `Planner-docs/Autopsy.md`, optional `Planner-docs/Project-Ontology.md`, optional `Planner-docs/Project-Comprehension.md`, optional `Planner-docs/Planing-Ledger.md`, and canonical handoffs under `references/handoffs/`.

## Install From GitHub

When the repository is published and accessible, install directly:

```text
/plugins install https://github.com/alicankiraz1/KimiQB
/plugins info kimiqb
/plugins reload
/new
```

Then test:

```text
/skill:kimiqb create a main plan for this project
```

## Managed Copy Behavior

Kimi Code copies installed plugins to `$KIMI_CODE_HOME/plugins/managed/<id>/`. Editing this source checkout after installation does not update the loaded plugin. Reinstall KimiQB after source changes:

```text
/plugins install /path/to/KimiQB
/plugins reload
/new
```

For maintenance automation, sync the managed copy with cache excludes and then verify parity:

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

After syncing, use `/plugins reload` or start `/new`; otherwise Kimi Code may continue using a stale in-memory skill.

## Verify Installation

In a target repository, ask:

```text
/skill:kimiqb inspect this repo and plan this project
```

Expected behavior:

1. KimiQB performs a bounded read-only scan of the current repository.
2. It asks for `PROJECT_NAME`, ideally with a repo-derived default.
3. It asks for `PROJECT_INTENT`, ideally with a repo-derived draft.
4. It asks for `TARGET_END_STATE`, ideally across product, engineering, operations, security, and user value.
5. It asks for `KNOWN_CONSTRAINTS`, including detected stack, infra, validation, security, and unknown constraints.
6. It creates or updates `Planner-docs/Main-Planing.md`.
7. For existing repositories, it may create or update `Planner-docs/Autopsy.md`.
8. When enough evidence exists, it may create or update `Planner-docs/Project-Ontology.md` and `Planner-docs/Project-Comprehension.md`.
9. Step 2 and Step 3 handoffs use `handoff_contract_version: 1`.
10. Step 4 should treat `Planner-docs/Planing-Ledger.md` as Ledger v2 continuity memory and update it after verified slices.

## Troubleshooting

If `/skill:kimiqb` is not recognized:

- start a new Kimi Code session with `/new`;
- confirm the plugin is installed with `/plugins info kimiqb`;
- run `/plugins reload`;
- reinstall from the local path or GitHub URL;
- if installed from a private repository, confirm the current machine has GitHub access.

If source edits do not appear after reinstalling, remove the installed plugin from the Kimi plugin manager and install again from the intended path.
