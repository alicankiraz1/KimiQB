#!/usr/bin/env python3
"""Port CodexQB skill files into a KimiQB plugin tree.

This script reads CodexQB files and writes only into the current KimiQB
checkout. It intentionally does not modify the CodexQB source repository.
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CODEXQB_ROOT = Path(
    os.environ.get(
        "CODEXQB_ROOT",
        "/Users/alicankiraz/Desktop/BillionDollarsIdeas/CodexQB",
    )
)
SOURCE_SKILL_ROOT = CODEXQB_ROOT / "plugins/codexqb/skills/codexqb"
DEST_SKILL_ROOT = REPO_ROOT / "skills/kimiqb"

REFERENCE_FILES = [
    "First-Planner.md",
    "Autopsy-Planner.md",
    "Second-Planner.md",
    "Third-Planner.md",
    "Fourth-Planner.md",
    "goal-compiler.md",
    "apply-orchestrator.md",
    "apply-run-schema.json",
    "repo-aware-intake.md",
    "workflow-quality.md",
    "vibecoding-principles.md",
    "subagent-playbook.md",
    "planning-ledger.md",
    "project-ontology.md",
    "project-comprehension-methods.md",
    "probe-policy.md",
    "assessment-and-budget.md",
    "engineering-principles.md",
]

REFERENCE_RENAMES = {
    "goal-compiler.md": "session-compiler.md",
}

HANDOFF_FILES = [
    "run-step2.md",
    "run-step3.md",
    "run-step4.md",
]

APPLY_REFERENCE_FILES = [
    "controller.md",
    "implementer.md",
    "task-reviewer.md",
    "security-reviewer.md",
    "fixer.md",
    "final-reviewer.md",
]

SESSION_SPEC_FILES = [
    "step15.md",
    "step2.md",
    "step3.md",
    "step4.md",
]

SCRIPT_FILES = [
    ("safety_contracts.py", "safety_contracts.py"),
    ("validate_planner_docs.py", "validate_planner_docs.py"),
    ("goal_run.py", "session_run.py"),
    ("apply_run.py", "apply_run.py"),
]

TEXT_REPLACEMENTS = [
    ("codexqb_schema_version", "kimiqb_schema_version"),
    ("CODEXQB", "KIMIQB"),
    ("Use $codexqb. Run Step", "/skill:kimiqb Run Step"),
    ("Use $codexqb. Read and return", "/skill:kimiqb Read and return"),
    ("Use $codexqb.", "/skill:kimiqb"),
    ("Use $codexqb", "/skill:kimiqb"),
    ("$codexqb", "/skill:kimiqb"),
    ("If installed/available", "if installed/available"),
    ("CodexQB Probe Policy", "KimiQB Probe Policy"),
    ("CodexQB Project Comprehension Methods", "KimiQB Project Comprehension Methods"),
    ("CodexQB Planning Ledger", "KimiQB Planning Ledger"),
    ("CodexQB uses", "KimiQB uses"),
    ("CodexQB believes", "KimiQB believes"),
    ("CodexQB generates", "KimiQB generates"),
    ("CodexQB planning-ledger guidance", "KimiQB planning-ledger guidance"),
    ("Long CodexQB runs", "Long KimiQB runs"),
    ("Parent CodexQB", "Parent KimiQB"),
    ("CodexQB", "KimiQB"),
    ("codexqb", "kimiqb"),
    (
        "plugins/kimiqb/skills/kimiqb/scripts/validate_planner_docs.py",
        "skills/kimiqb/scripts/validate_planner_docs.py",
    ),
    ("plugins/kimiqb/skills/kimiqb", "skills/kimiqb"),
    ("plugins/kimiqb/.codex-plugin/plugin.json", "kimi.plugin.json"),
    (".codex-plugin/plugin.json", "kimi.plugin.json"),
    (".codex-plugin", "kimi.plugin.json"),
    (".codexqb", ".kimiqb"),
    (
        "plugins/codexqb/skills/codexqb/scripts/validate_planner_docs.py",
        "skills/kimiqb/scripts/validate_planner_docs.py",
    ),
    ("plugins/codexqb/skills/codexqb", "skills/kimiqb"),
    ("Codex/GitHub", "Kimi Code/GitHub"),
    ("Codex skills/plugins by scope", "Kimi-compatible skills/plugins by scope"),
    ("Codex skills/plugins", "Kimi Code skills/plugins"),
    ("Codex skills", "Kimi Code skills"),
    ("Codex skill", "Kimi Code skill"),
    ("Codex plugin", "Kimi Code plugin"),
    ("Codex thread", "Kimi Code session"),
    ("Codex prompt", "Kimi Code prompt"),
    ("You are Codex", "You are Kimi Code"),
    ("Codex to", "Kimi Code to"),
    ("Codex should", "Kimi Code should"),
    ("Codex ", "Kimi Code "),
    ("Goal Run Contract", "Kimi Code Session Contract"),
    ("canonical Goal Run Contract", "canonical Kimi Code Session Contract"),
    ("Step 2 Goal Handoff", "Step 2 Kimi Code Session Handoff"),
    ("Step 3 Goal Handoff", "Step 3 Kimi Code Session Handoff"),
    ("Step 4 Goal Handoff", "Step 4 Kimi Code Session Handoff"),
    ("Goal-following behavior", "Long-session behavior"),
    ("Goal mode prompts", "new Kimi Code session prompts"),
    ("Goal mode prompt", "new Kimi Code session prompt"),
    ("Goal mode text", "Kimi Code session text"),
    ("Goal mode work", "Kimi Code long-session work"),
    ("Goal mode", "new Kimi Code session"),
    ("Goal Mode", "Long-Running Kimi Code Session"),
    ("Goal handoff", "Kimi Code session handoff"),
    ("Goal-mode", "Kimi Code session"),
    ("Goal runs", "long-running Kimi Code sessions"),
    ("Goal run", "long-running Kimi Code session"),
    ("Goal following", "long-session following"),
    ("Goal batch", "Kimi Code session batch"),
    ("Goal-mode readiness", "Kimi Code session readiness"),
    ("open Goal mode", "start a new Kimi Code session"),
    ("copy it into Goal mode", "copy it into a new Kimi Code session"),
    ("paste into Goal mode", "paste into a new Kimi Code session"),
    ("Hedefi Takip Et", "a new Kimi Code session"),
    ("click `a new Kimi Code session`", "start a new Kimi Code session"),
    ("paste into `a new Kimi Code session`", "paste into a new Kimi Code session"),
    ("for `a new Kimi Code session`", "for a new Kimi Code session"),
    ("`a new Kimi Code session`", "a new Kimi Code session"),
    ("codex-security", "security-focused Kimi-compatible skills/plugins"),
    ("goal-compiler.md", "session-compiler.md"),
    ("goal-specs", "session-specs"),
    ("goal_run.py", "session_run.py"),
    ("Goal-Prompt.md", "Session-Prompt.md"),
    ("Goal-Run.json", "Session-Run.json"),
    ("goal_run_status", "session_run_status"),
    ("goal_run_schema_version", "session_run_schema_version"),
    ("subagent_serial", "kimi_session_serial"),
    ("multi_agent_v1.spawn_agent", "kimi_session_dispatch_artifact"),
    ("external_superpowers", "external_adapter"),
]

SESSION_TEXT_REPLACEMENTS = [
    ("GOAL", "SESSION"),
    ("Goal", "Session"),
    ("goal", "session"),
]


def read_source(relative: str) -> str:
    path = SOURCE_SKILL_ROOT / relative
    return path.read_text(encoding="utf-8")


def adapt_text(text: str) -> str:
    for old, new in TEXT_REPLACEMENTS:
        text = text.replace(old, new)
    text = re.sub(r"`references/([^`]+)`", r"`${KIMI_SKILL_DIR}/references/\1`", text)
    text = re.sub(
        r"`scripts/validate_planner_docs.py`",
        r"`${KIMI_SKILL_DIR}/scripts/validate_planner_docs.py`",
        text,
    )
    text = text.replace(
        "native Kimi Code skill workflow, not a Claude migration",
        "native Kimi Code skill workflow",
    )
    text = text.replace(
        "Do not run `migrate-to-codex` for this workflow. This is a native Kimi Code skill workflow.",
        "Do not run migration workflows for this package. This is a native Kimi Code skill workflow.",
    )
    text = text.replace(
        "new Kimi Code session handoffs must",
        "Kimi Code session handoffs must",
    )
    text = text.replace(
        "open new Kimi Code session",
        "start a new Kimi Code session",
    )
    return text


def adapt_session_text(text: str) -> str:
    text = adapt_text(text)
    for old, new in SESSION_TEXT_REPLACEMENTS:
        text = text.replace(old, new)
    text = text.replace("Session/Question/Evidence", "Goal/Question/Evidence")
    text = text.replace("session-oriented", "goal-oriented")
    return text


def write_text(relative: str, text: str) -> None:
    path = DEST_SKILL_ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_skill() -> str:
    source = read_source("SKILL.md")
    body = source.split("---", 2)[2].lstrip()
    body = adapt_text(body)
    body = body.replace(
        "text-only new Kimi Code session prompts",
        "copy-ready prompts for a new Kimi Code session",
    )
    body = body.replace(
        "unless the user explicitly asks for a different flow",
        "unless the user explicitly asks for a direct run",
    )
    body = body.replace(
        "KimiQB asks intake questions in the user's language when practical. Generated Planner-docs artifacts are English by default unless the user explicitly requests another content language.",
        "KimiQB asks intake questions in the user's language when practical. Generated Planner-docs artifacts are English by default unless the user explicitly requests another content language.",
    )
    body = body.replace(
        "Use subagents only when they reduce context pollution or improve evidence quality",
        "Use Kimi Code subagents only when they reduce context pollution or improve evidence quality",
    )
    return """---
name: kimiqb
description: Vibecoding-first project planning workflow for Kimi Code. Use to create Planner-docs/Main-Planing.md, run an existing-project autopsy, maintain comprehension, ontology, and ledger context, decompose phases into sub-plans, audit readiness, and print a gated implementation handoff.
type: prompt
whenToUse: When the user asks Kimi Code to plan a software, AI, infrastructure, security, automation, or product repository before implementation.
disableModelInvocation: false
---

""" + body


def main() -> None:
    if not SOURCE_SKILL_ROOT.is_dir():
        raise SystemExit(f"missing CodexQB source skill root: {SOURCE_SKILL_ROOT}")

    (DEST_SKILL_ROOT / "references/handoffs").mkdir(parents=True, exist_ok=True)
    (DEST_SKILL_ROOT / "references/apply").mkdir(parents=True, exist_ok=True)
    (DEST_SKILL_ROOT / "references/session-specs").mkdir(parents=True, exist_ok=True)
    (DEST_SKILL_ROOT / "scripts").mkdir(parents=True, exist_ok=True)

    write_text("SKILL.md", build_skill())

    for filename in REFERENCE_FILES:
        source_text = read_source(f"references/{filename}")
        destination = REFERENCE_RENAMES.get(filename, filename)
        write_text(f"references/{destination}", adapt_text(source_text))

    for filename in HANDOFF_FILES:
        source_text = read_source(f"references/handoffs/{filename}")
        write_text(f"references/handoffs/{filename}", adapt_text(source_text))

    for filename in APPLY_REFERENCE_FILES:
        source_text = read_source(f"references/apply/{filename}")
        write_text(f"references/apply/{filename}", adapt_text(source_text))

    for filename in SESSION_SPEC_FILES:
        source_text = read_source(f"references/goal-specs/{filename}")
        write_text(f"references/session-specs/{filename}", adapt_session_text(source_text))

    for source_name, destination_name in SCRIPT_FILES:
        source_path = SOURCE_SKILL_ROOT / "scripts" / source_name
        destination_path = DEST_SKILL_ROOT / "scripts" / destination_name
        if source_name == "goal_run.py":
            script_text = adapt_session_text(source_path.read_text(encoding="utf-8"))
        else:
            script_text = adapt_text(source_path.read_text(encoding="utf-8"))
        destination_path.write_text(script_text, encoding="utf-8")
        shutil.copymode(source_path, destination_path)

    print(f"ported_skill_root={DEST_SKILL_ROOT}")


if __name__ == "__main__":
    main()
