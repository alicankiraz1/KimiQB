#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 -m json.tool kimi.plugin.json >/dev/null

required_files=(
  "kimi.plugin.json"
  "skills/kimiqb/SKILL.md"
  "skills/kimiqb/scripts/validate_planner_docs.py"
  "skills/kimiqb/references/First-Planner.md"
  "skills/kimiqb/references/Autopsy-Planner.md"
  "skills/kimiqb/references/Second-Planner.md"
  "skills/kimiqb/references/Third-Planner.md"
  "skills/kimiqb/references/Fourth-Planner.md"
  "skills/kimiqb/references/repo-aware-intake.md"
  "skills/kimiqb/references/workflow-quality.md"
  "README.md"
  "docs/INSTALLATION.md"
  "docs/USAGE.md"
  "docs/MAINTAINING.md"
  "LICENSE"
)

for path in "${required_files[@]}"; do
  if [[ ! -f "$path" ]]; then
    echo "missing_required_file=$path"
    exit 1
  fi
done

python3 - <<'PY'
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

manifest = json.loads(Path("kimi.plugin.json").read_text(encoding="utf-8"))
name = manifest.get("name", "")
if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", name):
    print(f"invalid_plugin_name={name}")
    sys.exit(1)

if manifest.get("skills") != "./skills/":
    print("manifest_skills_must_be=./skills/")
    sys.exit(1)

unsupported = {"tools", "commands", "hooks", "apps", "inject", "configFile"}
found = sorted(unsupported.intersection(manifest))
if found:
    print("unsupported_manifest_fields=" + ",".join(found))
    sys.exit(1)
PY

python3 - <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

text = Path("skills/kimiqb/SKILL.md").read_text(encoding="utf-8")
required = (
    "name: kimiqb",
    "description:",
    "type: prompt",
    "whenToUse:",
    "disableModelInvocation: false",
    "${KIMI_SKILL_DIR}",
)
missing = [item for item in required if item not in text]
if missing:
    print("skill_missing_required_text=" + ",".join(missing))
    sys.exit(1)
PY

python3 - <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

needles = (
    "$codexqb",
    "Use $codexqb",
    ".codex-plugin",
    "plugins/codexqb",
    "agents/openai.yaml",
    "Hedefi Takip Et",
    "Goal mode",
    "You are Codex",
    "project-planner",
)
ignored_parts = {
    ".git",
    "__MACOSX",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "artifacts",
    "build",
    "dist",
    "logs",
    "tmp",
}
ignored_paths = {
    "scripts/adapt_from_codexqb.py",
    "scripts/validate.sh",
}
blocked_suffixes = {".key", ".pem", ".pyc", ".zip"}
findings: list[str] = []

for path in Path(".").rglob("*"):
    if not path.is_file():
        continue
    normalized = path.as_posix()
    if (
        any(part in path.parts for part in ignored_parts)
        or normalized.startswith("docs/superpowers/plans/")
        or normalized.startswith("tests/")
        or normalized in ignored_paths
    ):
        continue
    if path.suffix in blocked_suffixes:
        continue
    if path.name == ".DS_Store" or path.name.startswith(".env"):
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    for needle in needles:
        if needle in text:
            findings.append(f"{normalized}: contains stale text {needle}")
            break

if findings:
    print("stale_codex_or_legacy_references_found")
    for finding in findings:
        print(finding)
    sys.exit(1)
PY

python3 -m unittest discover -s tests -v

if command -v kimi >/dev/null 2>&1; then
  kimi --version
else
  echo "kimi_cli=missing_from_path"
fi
