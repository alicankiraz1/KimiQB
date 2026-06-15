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
  "skills/kimiqb/references/vibecoding-principles.md"
  "skills/kimiqb/references/subagent-playbook.md"
  "skills/kimiqb/references/planning-ledger.md"
  "skills/kimiqb/references/project-ontology.md"
  "skills/kimiqb/references/assessment-and-budget.md"
  "skills/kimiqb/references/engineering-principles.md"
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

import re
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
    "Antigravity",
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
public_personal_path_exclusions = {
    "docs/superpowers/plans/2026-06-14-kimiqb.md",
    "scripts/adapt_from_codexqb.py",
}
blocked_suffixes = {".key", ".pem", ".pyc", ".zip"}
findings: list[str] = []
personal_path_pattern = re.compile(r"/Users/[A-Za-z0-9._-]+")

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
    if normalized not in public_personal_path_exclusions and personal_path_pattern.search(text):
        findings.append(f"{normalized}: contains personal local path")

if findings:
    print("stale_codex_or_legacy_references_found")
    for finding in findings:
        print(finding)
    sys.exit(1)
PY

python3 - <<'PY'
from pathlib import Path
import re
import subprocess
import sys

def in_git_checkout() -> bool:
    return subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def package_paths() -> list[Path]:
    ignored_parts = {
        ".git",
        "__MACOSX",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "artifacts",
        "build",
        "dist",
        "logs",
        "tmp",
    }
    paths: list[Path] = []
    for path in Path(".").rglob("*"):
        if not path.is_file():
            continue
        if ignored_parts.intersection(path.parts):
            continue
        if path.name == ".DS_Store":
            continue
        paths.append(path)
    return paths


if in_git_checkout():
    tracked = subprocess.run(["git", "ls-files", "-z"], check=True, capture_output=True).stdout
    paths = [Path(item.decode("utf-8")) for item in tracked.split(b"\0") if item]
    failure_label = "tracked_secret_hygiene_failed"
else:
    paths = package_paths()
    failure_label = "package_secret_hygiene_failed"
    print("package_secret_hygiene_mode=filesystem")

secret_patterns = [
    ("openrouter_api_key", re.compile(r"\bsk-or-v1-[A-Za-z0-9_-]{20,}\b")),
    ("openai_api_key", re.compile(r"\bsk-(?!or-v1-)[A-Za-z0-9_-]{20,}\b")),
    ("github_pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("github_legacy_pat", re.compile(r"\bghp_[A-Za-z0-9]{20,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private_key", re.compile(r"BEGIN (?:RSA|OPENSSH|DSA|EC|PRIVATE) KEY")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
]
openrouter_env = re.compile(r"\bOPENROUTER_API_KEY\s*=\s*([^\s#]+)", re.IGNORECASE)
allowed_openrouter_values = {
    "$OPENROUTER_API_KEY",
    "<redacted>",
    "redacted",
    "your_openrouter_api_key",
}

findings: list[str] = []
for path in paths:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        continue

    for line_number, line in enumerate(text.splitlines(), start=1):
        for name, pattern in secret_patterns:
            if pattern.search(line):
                findings.append(f"{path}:{line_number}: {name}")

        match = openrouter_env.search(line)
        if match:
            value = match.group(1).strip().strip("'\"")
            if value and value not in allowed_openrouter_values:
                findings.append(f"{path}:{line_number}: openrouter_env_value")

if findings:
    print(failure_label)
    for finding in findings:
        print(finding)
    sys.exit(1)
PY

python3 - <<'PY'
import io
from pathlib import Path
import re
import subprocess
import sys
import tarfile

bad = re.compile(
    r"(^|/)(\.git|__pycache__|\.env|artifacts|logs|tmp|__MACOSX)(/|$)"
    r"|\.pyc$|\.pem$|\.key$|\.local($|\.)"
)

def in_git_checkout() -> bool:
    return subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def package_offenders() -> list[str]:
    ignored_parts = {
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "build",
        "dist",
    }
    offenders: list[str] = []
    for path in Path(".").rglob("*"):
        if not path.is_file():
            continue
        if ignored_parts.intersection(path.parts):
            continue
        rel = path.as_posix()
        if bad.search(rel):
            offenders.append(rel)
    return offenders


if in_git_checkout():
    archive = subprocess.run(["git", "archive", "--format=tar", "HEAD"], check=True, capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tar:
        offenders = [member.name for member in tar.getmembers() if bad.search(member.name)]
    failure_label = "archive_hygiene_failed"
else:
    offenders = package_offenders()
    failure_label = "package_hygiene_failed"
    print("package_hygiene_mode=filesystem")

if offenders:
    print(failure_label)
    for offender in offenders:
        print(offender)
    sys.exit(1)
PY

if [[ "${KIMIQB_VALIDATE_SKIP_UNITTESTS:-0}" == "1" ]]; then
  echo "unit_tests_skipped=1"
else
  python3 -m unittest discover -s tests -v
fi

if command -v kimi >/dev/null 2>&1; then
  kimi --version
else
  echo "kimi_cli=missing_from_path"
fi
