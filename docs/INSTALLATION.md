# Installation

KimiQB is distributed as a Kimi Code plugin repository.

## Requirements

- Kimi Code CLI with plugin support.
- A new Kimi Code session after installation so `/skill:kimiqb` is loaded into context.
- GitHub access to `alicankiraz1/KimiQB` when installing from GitHub.

If this repository is private, installation only works for users and machines that can access the repository.

## Install From A Local Checkout

Open Kimi Code in any project and run:

```text
/plugins install /Users/alicankiraz/Desktop/BillionDollarsIdeas/KimiQB
/plugins info kimiqb
/plugins reload
/new
```

Then test the skill:

```text
/skill:kimiqb inspect this repo and plan this project
```

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

Kimi Code copies installed plugins to `$KIMI_CODE_HOME/plugins/managed/<id>/`. Editing this source checkout after installation does not update the installed plugin. Reinstall KimiQB after source changes:

```text
/plugins install /Users/alicankiraz/Desktop/BillionDollarsIdeas/KimiQB
/plugins reload
/new
```

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
6. It uses the confirmed values to create or update `Planner-docs/Main-Planing.md`.
7. For existing or partially built repositories, it may create or update `Planner-docs/Autopsy.md` as Step 1.5.

## Troubleshooting

If `/skill:kimiqb` is not recognized:

- start a new Kimi Code session with `/new`;
- confirm the plugin is installed with `/plugins info kimiqb`;
- run `/plugins reload`;
- reinstall from the local path or GitHub URL;
- if installed from a private repository, confirm the current machine has GitHub access.

If source edits do not appear after reinstalling, remove the installed plugin from the Kimi plugin manager and install again from the intended path.
