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

HANDOFF_FILES = [
    "run-step2.md",
    "run-step3.md",
    "run-step4.md",
]

TEXT_REPLACEMENTS = [
    ("codexqb_schema_version", "kimiqb_schema_version"),
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
    (DEST_SKILL_ROOT / "scripts").mkdir(parents=True, exist_ok=True)

    write_text("SKILL.md", build_skill())

    for filename in REFERENCE_FILES:
        source_text = read_source(f"references/{filename}")
        write_text(f"references/{filename}", adapt_text(source_text))

    for filename in HANDOFF_FILES:
        source_text = read_source(f"references/handoffs/{filename}")
        write_text(f"references/handoffs/{filename}", adapt_text(source_text))

    validator_source = SOURCE_SKILL_ROOT / "scripts/validate_planner_docs.py"
    validator_dest = DEST_SKILL_ROOT / "scripts/validate_planner_docs.py"
    validator_text = adapt_text(validator_source.read_text(encoding="utf-8"))
    validator_text = validator_text.replace("Validate KimiQB Planner-docs outputs.", "Validate KimiQB Planner-docs outputs.")
    validator_dest.write_text(validator_text, encoding="utf-8")
    shutil.copymode(validator_source, validator_dest)

    print(f"ported_skill_root={DEST_SKILL_ROOT}")


if __name__ == "__main__":
    main()
