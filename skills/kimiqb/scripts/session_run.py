#!/usr/bin/env python3
"""Compile deterministic KimiQB Session run previews.

This script is intentionally non-executing: it reads source contracts, hashes
source snapshots, validates a Session-Run schema, and renders Session prompts inside
the target repo.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from safety_contracts import (  # noqa: E402
    budget_limit,
    canonical_json_digest,
    default_budget_contract,
    glob_patterns_overlap,
    has_secret_like,
    implementation_contract_source_binding,
    implementation_contract_validation_command_ids,
    is_safe_repo_path,
    path_is_inside,
    token_usage_not_observed,
    validate_budget_contract,
    validate_token_usage,
)


ARTIFACT_SCHEMA_VERSION = 3
HANDOFF_CONTRACT_VERSION = 2
SESSION_RUN_SCHEMA_VERSION = 1
PLUGIN_VERSION = "0.3.0"
SESSION_COMPILER_VERSION = 1

SCRIPT_PATH = Path(__file__).resolve()
SKILL_ROOT = SCRIPT_PATH.parents[1]
VALIDATOR_PATH = SCRIPT_PATH.with_name("validate_planner_docs.py")

STAGE_REFERENCES = {
    "step15": ["references/Autopsy-Planner.md", "references/session-specs/step15.md"],
    "step2": ["references/handoffs/run-step2.md", "references/Second-Planner.md", "references/session-specs/step2.md"],
    "step3": ["references/handoffs/run-step3.md", "references/Third-Planner.md", "references/session-specs/step3.md"],
    "step4": ["references/handoffs/run-step4.md", "references/Fourth-Planner.md", "references/session-specs/step4.md"],
}

STAGE_MODES = {
    "step15": {"wave", "autopsy", "refresh"},
    "step2": {"wave", "full", "refresh", "repair"},
    "step3": {"wave", "audit", "repair"},
    "step4": {"direct", "kimi_session_serial", "external_adapter", "no_action"},
}

PLANNER_DOC_SOURCES = [
    "Planner-docs/Main-Planing.md",
    "Planner-docs/Autopsy.md",
    "Planner-docs/Project-Ontology.md",
    "Planner-docs/Project-Comprehension.md",
    "Planner-docs/Sub-Planing-Index.md",
    "Planner-docs/Sub-Planing-Audit.md",
    "Planner-docs/Planing-Ledger.md",
]
IMMUTABLE_PLANNER_DOCS_BY_STAGE = {
    "step15": [
        "Planner-docs/Main-Planing.md",
    ],
    "step2": [
        "Planner-docs/Main-Planing.md",
        "Planner-docs/Autopsy.md",
        "Planner-docs/Project-Ontology.md",
        "Planner-docs/Project-Comprehension.md",
    ],
    "step3": [
        "Planner-docs/Main-Planing.md",
        "Planner-docs/Autopsy.md",
        "Planner-docs/Project-Ontology.md",
        "Planner-docs/Project-Comprehension.md",
        "Planner-docs/Sub-Planing-Index.md",
        "Planner-docs/Planing-Ledger.md",
    ],
    "step4": [
        "Planner-docs/Main-Planing.md",
        "Planner-docs/Autopsy.md",
        "Planner-docs/Project-Ontology.md",
        "Planner-docs/Project-Comprehension.md",
        "Planner-docs/Sub-Planing-Index.md",
        "Planner-docs/Sub-Planing-Audit.md",
    ],
}
MUTABLE_OUTPUTS_BY_STAGE = {
    "step15": [
        "Planner-docs/Autopsy.md",
        "Planner-docs/Project-Ontology.md",
        "Planner-docs/Project-Comprehension.md",
        "Planner-docs/Planing-Ledger.md",
    ],
    "step2": [
        "Planner-docs/Sub-Planing-Index.md",
        "Planner-docs/Planing-Ledger.md",
        "Planner-docs/Faz-*-Plans/*.md",
    ],
    "step3": [
        "Planner-docs/Sub-Planing-Audit.md",
    ],
    "step4": [
        "Planner-docs/Planing-Ledger.md",
        ".kimiqb/apply-runs/**",
    ],
}
WORKSPACE_BASELINE_EXCLUDED_PREFIXES = (
    ".git/",
    ".kimiqb/",
    "Planner-docs/Session-Runs/",
    "__pycache__/",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
)
WORKSPACE_BASELINE_EXCLUDED_NAMES = {"KimiQB-sanitized.zip"}
WORKSPACE_BASELINE_PRUNED_DIRS = {
    ".cache",
    ".venv",
    "artifacts",
    "build",
    "dist",
    "logs",
    "model-cache",
    "node_modules",
    "vendor",
}
SESSION_FORBIDDEN_WRITES = ["~/.kimi-code/**", ".git/**", ".env", "**/*.key", "**/*.pem"]
SESSION_STOP_GATES = [
    "snapshot mismatch",
    "P0/P1 blocker",
    "unsafe path",
    "required user confirmation missing",
    "dirty unrelated worktree",
]
SESSION_FINAL_REPORT_CONTRACT = ["files changed", "validations", "blockers", "next action"]
SESSION_SAFETY = {
    "executes_commands": False,
    "allows_global_config_edits": False,
    "allows_commit_push_pr_deploy": False,
    "output_dir_must_be_inside_repo": True,
}
SESSION_AGENT_PROFILES = {
    "explorer": {"agent_type": "explorer", "model_profile": "fast", "sandbox": "read-only"},
    "implementer": {"agent_type": "worker", "model_profile": "balanced", "sandbox": "workspace-write"},
    "task_reviewer": {"agent_type": "default", "model_profile": "strong", "sandbox": "read-only"},
    "security_reviewer": {"agent_type": "default", "model_profile": "security_strong", "sandbox": "read-only"},
    "fixer": {"agent_type": "worker", "model_profile": "balanced", "sandbox": "workspace-write"},
    "final_reviewer": {"agent_type": "default", "model_profile": "strong", "sandbox": "read-only"},
}

def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def repo_relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def is_inside(parent: Path, child: Path) -> bool:
    return path_is_inside(parent, child)


def run_git(root: Path, args: list[str]) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return completed.stdout.strip() if completed.returncode == 0 else ""


def safe_rel_path(value: str) -> bool:
    path = Path(value)
    return bool(value) and not path.is_absolute() and ".." not in path.parts


def selected_step4_subplan_paths(active_scope: dict[str, object] | None) -> set[str]:
    if not isinstance(active_scope, dict):
        return set()
    selected: set[str] = set()
    queue = active_scope.get("ready_queue")
    if not isinstance(queue, list):
        return selected
    for item in queue:
        if not isinstance(item, dict):
            continue
        path = item.get("source_subplan_path") or item.get("subplan_path")
        if isinstance(path, str) and path:
            selected.add(path)
    return selected


def step4_unselected_subplan_paths(root: Path, active_scope: dict[str, object] | None) -> set[str]:
    selected = selected_step4_subplan_paths(active_scope)
    if not selected:
        return set()
    planner = root / "Planner-docs"
    if not planner.is_dir():
        return set()
    all_subplans = {repo_relative(root, path) for path in planner.glob("Faz-*-Plans/*.md") if path.is_file()}
    return all_subplans - selected


def collect_sources(root: Path, stage: str, active_scope: dict[str, object] | None = None) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    for rel in STAGE_REFERENCES[stage]:
        path = SKILL_ROOT / rel
        data = path.read_bytes()
        sources.append({"scope": "skill", "path": rel, "sha256": sha256_bytes(data)})

    for rel in IMMUTABLE_PLANNER_DOCS_BY_STAGE[stage]:
        path = root / rel
        if path.is_file():
            data = path.read_bytes()
            sources.append({"scope": "repo", "path": rel, "sha256": sha256_bytes(data)})

    if stage in {"step3", "step4"}:
        selected_step4_paths = selected_step4_subplan_paths(active_scope) if stage == "step4" else set()
        planner = root / "Planner-docs"
        for path in sorted(planner.glob("Faz-*-Plans/*.md")) if planner.is_dir() else []:
            rel_path = repo_relative(root, path)
            if stage == "step4" and selected_step4_paths and rel_path not in selected_step4_paths:
                continue
            data = path.read_bytes()
            sources.append({"scope": "repo", "path": rel_path, "sha256": sha256_bytes(data)})

    branch = run_git(root, ["branch", "--show-current"]) or "unknown"
    commit = run_git(root, ["rev-parse", "HEAD"]) or "unknown"
    sources.append({"scope": "git", "path": "branch", "sha256": sha256_bytes(branch.encode("utf-8")), "value": branch})
    sources.append({"scope": "git", "path": "commit", "sha256": sha256_bytes(commit.encode("utf-8")), "value": commit})
    return sources


def session_mutable_output_patterns(stage: str, active_scope: dict[str, object] | None = None) -> list[str]:
    patterns = list(MUTABLE_OUTPUTS_BY_STAGE[stage])
    if stage == "step4" and isinstance(active_scope, dict):
        for item in active_scope.get("ready_queue", []):
            if not isinstance(item, dict):
                continue
            contract = item.get("implementation_contract")
            if not isinstance(contract, dict):
                continue
            paths = contract.get("implementation_paths")
            if not isinstance(paths, list):
                continue
            for entry in paths:
                if not isinstance(entry, dict):
                    continue
                path = entry.get("path")
                if isinstance(path, str) and is_safe_repo_path(path) and path not in patterns:
                    patterns.append(path)
    return patterns


def mutable_output_matches(rel_path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(rel_path, pattern) for pattern in patterns)


def mutable_output_baseline(root: Path, patterns: list[str]) -> dict[str, object]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for pattern in patterns:
        if pattern in seen:
            duplicates.append(pattern)
        seen.add(pattern)
    files: list[dict[str, object]] = []
    for pattern in patterns:
        if any(char in pattern for char in "*?[]"):
            matches = sorted(root.glob(pattern))
        else:
            matches = [root / pattern]
        for path in matches:
            if path.is_file():
                files.append(
                    {
                        "path": repo_relative(root, path),
                        "exists": True,
                        "sha256": sha256_bytes(path.read_bytes()),
                    }
                )
            elif not any(char in pattern for char in "*?[]"):
                files.append({"path": pattern, "exists": False, "sha256": None})
    return {"declared": patterns, "duplicates": duplicates, "files": files}


def workspace_path_excluded(rel_path: str, mutable_patterns: list[str], excluded_paths: set[str] | None = None) -> bool:
    if excluded_paths and rel_path in excluded_paths:
        return True
    if rel_path in WORKSPACE_BASELINE_EXCLUDED_NAMES:
        return True
    if any(rel_path == prefix.rstrip("/") or rel_path.startswith(prefix) for prefix in WORKSPACE_BASELINE_EXCLUDED_PREFIXES):
        return True
    if any(part == "__pycache__" for part in Path(rel_path).parts):
        return True
    return mutable_output_matches(rel_path, mutable_patterns)


def workspace_inventory(root: Path, mutable_patterns: list[str]) -> list[str]:
    return workspace_inventory_with_exclusions(root, mutable_patterns, set())


def workspace_inventory_with_exclusions(root: Path, mutable_patterns: list[str], excluded_paths: set[str]) -> list[str]:
    entries: list[str] = []
    if run_git(root, ["rev-parse", "--is-inside-work-tree"]) == "true":
        rel_paths = sorted(line.strip() for line in run_git(root, ["ls-files"]).splitlines() if line.strip())
        for rel in rel_paths:
            if workspace_path_excluded(rel, mutable_patterns, excluded_paths):
                continue
            path = root / rel
            if path.is_file():
                entries.append(f"{rel}\0{sha256_bytes(path.read_bytes())}")
        return entries
    for current, dirs, files in os.walk(root):
        rel_dir = Path(current).relative_to(root).as_posix()
        dirs[:] = [
            directory
            for directory in dirs
            if directory not in WORKSPACE_BASELINE_PRUNED_DIRS
            and not workspace_path_excluded((Path(rel_dir) / directory).as_posix() if rel_dir != "." else directory, mutable_patterns, excluded_paths)
        ]
        for filename in sorted(files):
            rel = (Path(rel_dir) / filename).as_posix() if rel_dir != "." else filename
            if workspace_path_excluded(rel, mutable_patterns, excluded_paths):
                continue
            path = root / rel
            if path.is_symlink():
                entries.append(f"{rel}\0symlink")
                continue
            if not path.is_file():
                continue
            entries.append(f"{rel}\0{sha256_bytes(path.read_bytes())}")
    return entries


def git_hash(root: Path, args: list[str]) -> str:
    output = run_git(root, args)
    return sha256_bytes(output.encode("utf-8"))


def workspace_baseline(root: Path, mutable_patterns: list[str], excluded_paths: set[str] | None = None) -> dict[str, object]:
    branch = run_git(root, ["branch", "--show-current"]) or "unknown"
    commit = run_git(root, ["rev-parse", "HEAD"]) or "unknown"
    excluded = excluded_paths or set()
    inventory = workspace_inventory_with_exclusions(root, mutable_patterns, excluded)
    return {
        "branch": branch,
        "base_commit": commit,
        "staged_diff_hash": git_hash(root, ["diff", "--cached", "--binary"]),
        "unstaged_diff_hash": git_hash(root, ["diff", "--binary"]),
        "untracked_inventory_hash": git_hash(root, ["ls-files", "--others", "--exclude-standard"]),
        "workspace_inventory_sha256": sha256_bytes("\n".join(inventory).encode("utf-8")),
        "workspace_inventory_count": len(inventory),
        "excluded_paths": sorted(excluded),
    }


def stage_snapshot(
    root: Path,
    stage: str,
    sources: list[dict[str, str]],
    mutable_patterns: list[str],
    *,
    template_bundle_digest: str,
    session_spec_digest_value: str,
    baseline_excluded_paths: set[str] | None = None,
) -> dict[str, object]:
    return {
        "stage": stage,
        "branch": run_git(root, ["branch", "--show-current"]) or "unknown",
        "base_commit": run_git(root, ["rev-parse", "HEAD"]) or "unknown",
        "immutable_inputs": sources,
        "immutable_input_digest": snapshot_digest(stage, sources),
        "mutable_outputs": mutable_output_baseline(root, mutable_patterns),
        "workspace_baseline": workspace_baseline(root, mutable_patterns, baseline_excluded_paths),
        "template_bundle_digest": template_bundle_digest,
        "compiler_version": SESSION_COMPILER_VERSION,
        "session_spec_digest": session_spec_digest_value,
    }


def snapshot_digest(stage: str, sources: list[dict[str, str]]) -> str:
    payload = json.dumps({"stage": stage, "sources": sources}, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(payload)


def run_id_for(stage: str, sources: list[dict[str, str]]) -> str:
    return f"session-{stage}-{snapshot_digest(stage, sources)[:12]}"


def template_bundle(stage: str) -> dict[str, object]:
    templates = []
    for rel in STAGE_REFERENCES[stage]:
        path = SKILL_ROOT / rel
        templates.append({"path": rel, "sha256": sha256_bytes(path.read_bytes())})
    compiler = {
        "path": "scripts/session_run.py",
        "version": SESSION_COMPILER_VERSION,
        "sha256": sha256_bytes(SCRIPT_PATH.read_bytes()),
    }
    payload = {"templates": templates, "compiler": compiler}
    digest = sha256_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return {"digest": digest, **payload}


def session_spec_digest(stage: str, sources: list[dict[str, str]], mode: str, objective: str, active_scope: dict[str, object]) -> str:
    payload = {
        "stage": stage,
        "sources": sources,
        "mode": mode,
        "objective": objective,
        "active_scope": active_scope,
        "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
        "handoff_contract_version": HANDOFF_CONTRACT_VERSION,
        "session_run_schema_version": SESSION_RUN_SCHEMA_VERSION,
    }
    return sha256_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def context_token_budget_for(stage: str) -> dict[str, object]:
    return {"risk": "medium", "confirmation_required": stage in {"step2", "step4"}}


def session_policy_envelope(
    stage: str,
    sources: list[dict[str, str]],
    mode: str,
    active_scope: dict[str, object],
) -> dict[str, object]:
    return {
        "required_inputs": [item["path"] for item in sources if item.get("scope") in {"repo", "skill"}],
        "allowed_writes": session_mutable_output_patterns(stage, active_scope),
        "forbidden_writes": list(SESSION_FORBIDDEN_WRITES),
        "validation_checkpoints": validation_checkpoints_for(stage),
        "stop_gates": list(SESSION_STOP_GATES),
        "subagent_plan": build_subagent_plan(stage, mode, active_scope),
        "context_token_budget": context_token_budget_for(stage),
        "budget_contract": default_budget_contract(),
        "final_report_contract": list(SESSION_FINAL_REPORT_CONTRACT),
        "user_confirmation_required": stage in {"step2", "step4"},
        "safety": dict(SESSION_SAFETY),
    }


def session_policy_digest(stage: str, sources: list[dict[str, str]], mode: str, active_scope: dict[str, object]) -> str:
    return canonical_json_digest(session_policy_envelope(stage, sources, mode, active_scope))


def invocation_suffix(value: str | None = None) -> str:
    raw = value or f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}-{os.getpid()}"
    suffix = re.sub(r"[^A-Za-z0-9_.-]+", "-", raw).strip("-._")
    if not suffix:
        raise ValueError("invalid_run_id_suffix")
    return suffix[:64]


def session_run_id_for(stage: str, spec_digest: str, run_id_suffix: str | None = None) -> str:
    return f"session-{stage}-{spec_digest[:12]}-{invocation_suffix(run_id_suffix)}"


def run_bundled_validator(root: Path, mode: str, *, strict: bool = True) -> tuple[int, str]:
    command = [sys.executable, VALIDATOR_PATH.as_posix(), "--root", root.as_posix(), "--mode", mode]
    if strict:
        command.append("--strict")
    try:
        completed = subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, f"validator_unavailable={type(exc).__name__}"
    return completed.returncode, f"{completed.stdout}\n{completed.stderr}".strip()


def stage_validator_mode(stage: str) -> str:
    return {
        "step15": "step1",
        "step2": "step1",
        "step3": "step3-preflight",
        "step4": "step4",
    }[stage]


def stage_prerequisite_blockers(root: Path, stage: str) -> list[str]:
    docs = root / "Planner-docs"
    blockers: list[str] = []
    if stage in {"step15", "step2"} and not (docs / "Main-Planing.md").is_file():
        blockers.append("missing_prerequisite=Planner-docs/Main-Planing.md")
    if stage == "step3":
        if not (docs / "Sub-Planing-Index.md").is_file():
            blockers.append("missing_prerequisite=Planner-docs/Sub-Planing-Index.md")
        if not any(docs.glob("Faz-*-Plans/Faz*.md")):
            blockers.append("missing_prerequisite=active_subplans")
    if stage == "step4":
        audit = docs / "Sub-Planing-Audit.md"
        if not audit.is_file():
            blockers.append("missing_prerequisite=Planner-docs/Sub-Planing-Audit.md")
        else:
            text = audit.read_text(encoding="utf-8", errors="replace")
            if "READY" not in text and "NO_ACTION_REQUIRED" not in text:
                blockers.append("missing_prerequisite=step4_ready_queue_or_no_action")
    if blockers:
        return blockers
    validator_mode = stage_validator_mode(stage)
    code, output = run_bundled_validator(root, validator_mode, strict=True)
    if code != 0:
        blockers.append(f"validator_failed={validator_mode}")
        blockers.append(f"validator_output_sha256={sha256_bytes(output.encode('utf-8'))}")
    return blockers


def project_name(root: Path) -> str:
    main = root / "Planner-docs" / "Main-Planing.md"
    if main.is_file():
        text = main.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"Project\s+Name\s*[:|-]\s*(.+)", text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()[:120]
    return root.name


def extract_ready_queue(root: Path) -> list[dict[str, str]]:
    audit = root / "Planner-docs" / "Sub-Planing-Audit.md"
    if not audit.is_file():
        return []
    text = audit.read_text(encoding="utf-8", errors="replace")
    items: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for match in re.finditer(
        r"\b(READY_WITH_WARNINGS|READY)\b\s*:?\s*`?((?:Planner-docs/)?Faz-\d+-Plans/Faz\d+\.\d+-[a-z0-9-]+\.md)`?",
        text,
        flags=re.IGNORECASE,
    ):
        path = match.group(2)
        if not path.startswith("Planner-docs/"):
            path = f"Planner-docs/{path}"
        key = (match.group(1).upper(), path)
        if key not in seen:
            seen.add(key)
            items.append({"readiness_status": key[0], "subplan_path": path})
    for line in text.splitlines():
        if "|" not in line or "---" in line:
            continue
        cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        path, status = cells[0], cells[1].upper()
        if status not in {"READY", "READY_WITH_WARNINGS"}:
            continue
        if not re.fullmatch(r"(?:Planner-docs/)?Faz-\d+-Plans/Faz\d+\.\d+-[a-z0-9-]+\.md", path):
            continue
        if not path.startswith("Planner-docs/"):
            path = f"Planner-docs/{path}"
        key = (status, path)
        if key not in seen:
            seen.add(key)
            items.append({"readiness_status": status, "subplan_path": path})
    return items


def extract_contract_signals(text: str) -> dict[str, list[str]]:
    patterns = {
        "acceptance_criteria": r"(?:acceptance|behavior|mp-ph\d+-as-\d+)",
        "allowed_paths": r"(?:allowed.*path|implementation[_ ]path|write[_ ]path)",
        "forbidden_paths": r"(?:forbidden[_ ]path|forbidden.*path|must not modify|do not modify)",
        "parent_signals": r"(?:parent[_ ]signal|parent acceptance|acceptance signal|signal id)",
        "dependencies": r"(?:depends_on|dependency|blocks|can_run_in_parallel|activation_conditions)",
        "framework_ownership": r"(?:framework ownership|ownership matrix|trl|vllm|peft)",
        "algorithmic_invariants": r"(?:invariant|rollout|policy fingerprint|trainer-step|stateful)",
        "structured_validation_commands": r"(?:validation[_ ]command|argv|expected_exit_code|probe_tier)",
        "security_requirements": r"(?:security[_ ]review|required security|risk[_ ]domain|secret|credential)",
    }
    signals = {key: [] for key in patterns}
    for line in text.splitlines():
        stripped = line.strip().strip("|").strip()
        if not stripped or len(stripped) > 240:
            continue
        lowered = stripped.lower()
        for key, pattern in patterns.items():
            if re.search(pattern, lowered):
                signals[key].append(stripped)
    return signals


def extract_implementation_contract(root: Path, subplan_path: str) -> dict[str, object]:
    binding = implementation_contract_source_binding(root, subplan_path)
    contract = binding.get("implementation_contract")
    return contract if isinstance(contract, dict) else {}


def validation_command_ids(implementation_contract: dict[str, object]) -> list[str]:
    return implementation_contract_validation_command_ids(implementation_contract)


def implementation_contract_digest(implementation_contract: dict[str, object]) -> str | None:
    if not implementation_contract:
        return None
    return canonical_json_digest(implementation_contract)


def subplan_scope_item(root: Path, subplan_path: str) -> dict[str, object]:
    path = root / subplan_path
    text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    contract = extract_contract_signals(text)
    binding = implementation_contract_source_binding(root, subplan_path)
    implementation_contract = binding.get("implementation_contract")
    implementation_contract = implementation_contract if isinstance(implementation_contract, dict) else {}
    item: dict[str, object] = {
        "subplan_path": subplan_path,
        "source_subplan_path": subplan_path,
        "subplan_sha256": binding.get("source_subplan_sha256") if path.is_file() else None,
        "source_subplan_sha256": binding.get("source_subplan_sha256") if path.is_file() else None,
        "contract_signals": contract,
        "implementation_contract": implementation_contract,
        "implementation_contract_digest": binding.get("implementation_contract_digest"),
    }
    structured_security = implementation_contract.get("security_review_required")
    item["security_review_required"] = (
        structured_security
        if isinstance(structured_security, bool)
        else any("required" in signal.lower() or "risk" in signal.lower() for signal in contract["security_requirements"])
    )
    item["validation_command_count"] = len(contract["structured_validation_commands"])
    structured_commands = implementation_contract.get("validation_commands")
    if isinstance(structured_commands, list):
        item["structured_validation_command_count"] = len([command for command in structured_commands if isinstance(command, dict)])
    else:
        item["structured_validation_command_count"] = 0
    item["validation_command_ids"] = binding.get("validation_command_ids", [])
    item["parent_acceptance_signal_ids"] = binding.get("parent_acceptance_signal_ids", [])
    item["risk_class"] = binding.get("risk_class", "")
    item["risk_domains"] = binding.get("risk_domains", [])
    return item


def collect_subplan_scope(root: Path, subplans: list[str]) -> list[dict[str, object]]:
    return [subplan_scope_item(root, path) for path in subplans]


def markdown_section(text: str, section_number: int, title: str) -> str:
    pattern = re.compile(
        rf"^##\s*{section_number}\.?\s+{re.escape(title)}\s*$",
        flags=re.IGNORECASE | re.MULTILINE,
    )
    match = pattern.search(text)
    if not match:
        return ""
    next_heading = re.search(r"^##\s+", text[match.end() :], flags=re.MULTILINE)
    end = match.end() + next_heading.start() if next_heading else len(text)
    return text[match.end() : end].strip()


def parse_int_list(value: str) -> list[int]:
    return [int(item) for item in re.findall(r"\d+", value)]


def active_phases_from_notes(notes: str, detected_phases: list[int]) -> list[int]:
    detected = set(detected_phases)
    lowered = notes.lower()
    range_match = re.search(r"phases?\s+(\d+)\s*(?:-|–|—|to)\s*(\d+)", lowered)
    if range_match:
        start, end = int(range_match.group(1)), int(range_match.group(2))
        low, high = sorted((start, end))
        return [phase for phase in detected_phases if low <= phase <= high]
    list_match = re.search(r"phases?\s+([0-9,\s]+)\s+(?:first|active|initial|wave)", lowered)
    if list_match:
        listed = parse_int_list(list_match.group(1))
        return [phase for phase in detected_phases if phase in set(listed)]
    if len(detected_phases) <= 3:
        return detected_phases
    return [phase for phase in detected_phases if phase in set(detected_phases[:3]) and phase in detected]


def collect_step2_planning_horizon(root: Path, mode: str, existing_subplan_count: int) -> dict[str, object]:
    main = root / "Planner-docs" / "Main-Planing.md"
    if not main.is_file():
        return {
            "planning_mode": mode,
            "detected_phases": [],
            "active_phases": [],
            "deferred_phases": [],
            "parent_acceptance_signals": [],
            "max_detailed_subplans": 10,
            "max_output_words": 12000,
            "session_token_risk": "medium",
            "review_checkpoint": "after_active_wave",
            "confirmation_threshold": ">15_files_or_very_high_token_risk",
            "user_confirmation_required": False,
            "framework_ownership_required": False,
            "algorithmic_invariants_required": False,
        }
    text = main.read_text(encoding="utf-8", errors="replace")
    roadmap = markdown_section(text, 6, "Phase-Based Master Roadmap")
    next_steps = markdown_section(text, 8, "Prioritized Next Steps")
    prep_notes = markdown_section(text, 9, "Step 2 Preparation Notes")
    detected_phases: list[int] = []
    parent_signals: list[str] = []
    for line in roadmap.splitlines():
        if "|" not in line or "---" in line.lower() or "phase" in line.lower() and "acceptance" in line.lower():
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells:
            continue
        phase_match = re.search(r"\d+", cells[0])
        if not phase_match:
            continue
        phase = int(phase_match.group(0))
        if phase not in detected_phases:
            detected_phases.append(phase)
        for signal in re.findall(r"\bMP-PH\d+-AS-\d+\b", line, flags=re.IGNORECASE):
            normalized = signal.upper()
            if normalized not in parent_signals:
                parent_signals.append(normalized)
    detected_phases.sort()

    if mode == "full":
        active_phases = detected_phases
    else:
        active_phases = active_phases_from_notes("\n".join([prep_notes, next_steps]), detected_phases)
    active_set = set(active_phases)
    deferred_phases = [phase for phase in detected_phases if phase not in active_set]
    max_detailed_subplans = 10
    estimated_subplans = existing_subplan_count if existing_subplan_count else min(max_detailed_subplans, max(1, len(active_phases) * 2))
    estimated_words = max(estimated_subplans * 1200, 1200 if active_phases else 0)
    if len(detected_phases) > 10 or estimated_subplans > 15 or estimated_words > 18000:
        risk = "very_high"
    elif len(detected_phases) > 6 or estimated_words > 10000:
        risk = "high"
    else:
        risk = "medium"
    combined = "\n".join([roadmap, next_steps, prep_notes]).lower()
    framework_required = any(keyword in combined for keyword in ["trl", "vllm", "peft", "framework ownership"])
    invariant_required = any(
        keyword in combined
        for keyword in ["grpo", "rollout", "policy fingerprint", "trainer-step", "stateful", "reinforcement learning", " rl "]
    )
    return {
        "planning_mode": mode,
        "detected_phases": detected_phases,
        "active_phases": active_phases,
        "deferred_phases": deferred_phases,
        "parent_acceptance_signals": parent_signals,
        "max_detailed_subplans": max_detailed_subplans,
        "max_output_words": 12000,
        "session_token_risk": risk,
        "review_checkpoint": "after_active_wave",
        "estimated_subplans": estimated_subplans,
        "estimated_output_words": estimated_words,
        "confirmation_threshold": ">15_files_or_very_high_token_risk",
        "user_confirmation_required": estimated_subplans > 15 or risk == "very_high" or mode == "full",
        "framework_ownership_required": framework_required,
        "algorithmic_invariants_required": invariant_required,
        "source_sections": [
            "Planner-docs/Main-Planing.md::## 6. Phase-Based Master Roadmap",
            "Planner-docs/Main-Planing.md::## 8. Prioritized Next Steps",
            "Planner-docs/Main-Planing.md::## 9. Step 2 Preparation Notes",
        ],
    }


def collect_stage_scope(root: Path, stage: str, mode: str) -> dict[str, object]:
    docs = root / "Planner-docs"
    subplans = [
        repo_relative(root, path)
        for path in sorted(docs.glob("Faz-*-Plans/Faz*.md"))
        if path.is_file()
    ] if docs.is_dir() else []
    scope: dict[str, object] = {"stage": stage, "project_root": "."}
    if stage in {"step2", "step3"}:
        scope["detailed_subplans"] = subplans
        scope["subplan_contracts"] = collect_subplan_scope(root, subplans)
        scope["subplan_count"] = len(subplans)
        scope["index_path"] = "Planner-docs/Sub-Planing-Index.md" if (docs / "Sub-Planing-Index.md").is_file() else None
    if stage == "step2":
        scope["planning_horizon"] = collect_step2_planning_horizon(root, mode, len(subplans))
    if stage == "step4":
        ready_queue = extract_ready_queue(root)
        enriched_queue: list[dict[str, object]] = []
        for item in ready_queue:
            enriched = dict(item)
            enriched.update(subplan_scope_item(root, item["subplan_path"]))
            enriched_queue.append(enriched)
        scope["ready_queue"] = enriched_queue
        scope["ready_count"] = len(ready_queue)
        scope["no_action_required"] = bool((docs / "Sub-Planing-Audit.md").is_file() and "NO_ACTION_REQUIRED" in (docs / "Sub-Planing-Audit.md").read_text(encoding="utf-8", errors="replace"))
    return scope


def join_contract_values(value: object) -> str:
    if isinstance(value, list):
        normalized: list[str] = []
        for item in value:
            if isinstance(item, dict) and isinstance(item.get("path"), str):
                normalized.append(item["path"])
            elif str(item).strip():
                normalized.append(str(item))
        return ",".join(normalized) or "none"
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "none"


def command_id_summary(commands: object) -> str:
    if not isinstance(commands, list):
        return "none"
    ids = [
        str(command.get("id")).strip()
        for command in commands
        if isinstance(command, dict) and isinstance(command.get("id"), str) and str(command.get("id")).strip()
    ]
    return ",".join(ids) if ids else "none"


def contract_driven_work_steps(item: dict[str, object]) -> list[str]:
    path = str(item.get("subplan_path") or item.get("source_subplan_path") or "unknown")
    contract = item.get("implementation_contract")
    contract = contract if isinstance(contract, dict) else {}
    parent_signals = join_contract_values(contract.get("parent_signals"))
    implementation_paths = join_contract_values(contract.get("implementation_paths"))
    forbidden_paths = join_contract_values(contract.get("forbidden_paths"))
    validation_ids = command_id_summary(contract.get("validation_commands"))
    outputs = join_contract_values(contract.get("outputs"))
    security_required = contract.get("security_review_required")
    dependency_state = str(item.get("dependency_state") or "not_recorded")
    return [
        f"validate active snapshot for {path}",
        f"read {path} implementation contract and parent_signals={parent_signals}",
        f"permit writes only to implementation_paths={implementation_paths}; forbidden_paths={forbidden_paths}",
        f"dispatch implementer for {path} with validation_command_ids={validation_ids}, dependency_state={dependency_state}, security_review_required={json.dumps(security_required if isinstance(security_required, bool) else False)}",
        f"run task review and required security review for {path}; fix/re-review before VERIFIED",
        f"update ledger/result evidence for {path}; outputs={outputs}",
    ]


def stage_work_steps(stage: str, scope: dict[str, object]) -> list[str]:
    base = ["verify snapshot", "load canonical references"]
    if stage == "step2":
        horizon = scope.get("planning_horizon", {})
        horizon_step = (
            "derive active planning horizon from Main-Planing.md"
            if isinstance(horizon, dict)
            else "derive active planning horizon"
        )
        subplans = scope.get("detailed_subplans", [])
        return base + [horizon_step] + [f"detail active sub-plan {path}" for path in subplans] + ["run Step 2 validation checkpoints", "write final report"]
    if stage == "step3":
        subplans = scope.get("detailed_subplans", [])
        return base + [f"audit sub-plan {path}" for path in subplans] + ["run step3-preflight then step3 validation", "write final report"]
    if stage == "step4":
        queue = scope.get("ready_queue", [])
        if isinstance(queue, list) and queue:
            steps = base[:]
            for item in queue:
                if isinstance(item, dict):
                    steps.extend(contract_driven_work_steps(item))
            return steps + ["write final report"]
        return base + ["confirm NO_ACTION_REQUIRED or blocked Step 4 readiness", "write final report"]
    return base + ["perform stage-specific work", "run validation checkpoints", "write final report"]


def validation_checkpoints_for(stage: str) -> list[dict[str, object]]:
    mode = stage if stage != "step15" else "autopsy"
    modes = ["step3-preflight", "step3"] if stage == "step3" else [mode]
    return [
        {
            "id": f"VAL-{index:02d}",
            "argv": [
                "python3",
                "skills/kimiqb/scripts/validate_planner_docs.py",
                "--root",
                ".",
                "--mode",
                checkpoint_mode,
                "--strict",
            ],
            "network": "deny",
            "probe_tier": 1,
        }
        for index, checkpoint_mode in enumerate(modes, start=1)
    ]


def checkpoint_is_safe(checkpoint: object) -> bool:
    if not isinstance(checkpoint, dict):
        return False
    argv = checkpoint.get("argv")
    if not isinstance(argv, list):
        return False
    expected_prefix = [
        "python3",
        "skills/kimiqb/scripts/validate_planner_docs.py",
        "--root",
        ".",
        "--mode",
    ]
    if len(argv) != len(expected_prefix) + 2:
        return False
    if argv[: len(expected_prefix)] != expected_prefix:
        return False
    if not isinstance(argv[-2], str) or argv[-2] not in {"autopsy", "step2", "step3-preflight", "step3", "step4"}:
        return False
    if argv[-1] != "--strict":
        return False
    if checkpoint.get("network") != "deny":
        return False
    if checkpoint.get("probe_tier") != 1:
        return False
    return True


def session_role(role: str, purpose: str, required: bool = True) -> dict[str, object]:
    profile = SESSION_AGENT_PROFILES[role]
    return {
        "role": role,
        "agent_type": profile["agent_type"],
        "model_profile": profile["model_profile"],
        "sandbox": profile["sandbox"],
        "fresh_context": True,
        "fork_context": False,
        "required": required,
        "purpose": purpose,
    }


def build_subagent_plan(stage: str, mode: str, active_scope: dict[str, object]) -> dict[str, object]:
    plan: dict[str, object] = {
        "max_depth": 1,
        "roles": [],
        "one_writer": True,
        "fresh_context_required": True,
        "dispatch_order": [],
    }
    if stage == "step2":
        plan["roles"] = [
            session_role("explorer", "optional read-only repository evidence collection", required=False),
            session_role("task_reviewer", "optional read-only planning consistency review", required=False),
        ]
        plan["dispatch_order"] = ["explorer", "task_reviewer"]
    if stage == "step3":
        plan["roles"] = [session_role("task_reviewer", "read-only Step 3 audit review", required=False)]
        plan["dispatch_order"] = ["task_reviewer"]
    if stage == "step4" and mode in {"kimi_session_serial", "external_adapter"}:
        queue = active_scope.get("ready_queue", [])
        security_required = any(
            isinstance(item, dict) and item.get("security_review_required") is True
            for item in queue
        )
        roles = [
            session_role("implementer", "fresh-slice implementation writer"),
            session_role("task_reviewer", "independent spec and quality review"),
        ]
        if security_required:
            roles.append(session_role("security_reviewer", "independent security review for security-required slices"))
        roles.extend(
            [
                session_role("fixer", "same-slice fixes when review requires changes", required=False),
                session_role("final_reviewer", "batch-level final review before completion"),
            ]
        )
        plan["roles"] = roles
        plan["dispatch_order"] = [role["role"] for role in roles]
    return plan


def subagent_plan_is_valid(plan: object) -> bool:
    if not isinstance(plan, dict) or plan.get("max_depth") != 1:
        return False
    roles = plan.get("roles")
    if not isinstance(roles, list):
        return False
    for role in roles:
        if not isinstance(role, dict):
            return False
        name = role.get("role")
        if name not in SESSION_AGENT_PROFILES:
            return False
        profile = SESSION_AGENT_PROFILES[str(name)]
        for key in ("agent_type", "model_profile", "sandbox"):
            if role.get(key) != profile[key]:
                return False
        if role.get("fresh_context") is not True or role.get("fork_context") is not False:
            return False
    return True


def _scope_source_path(item: dict[str, object]) -> str:
    value = item.get("source_subplan_path") or item.get("subplan_path")
    return str(value) if isinstance(value, str) else ""


def _validate_session_scope_source_items(root: Path, label: str, items: object, errors: list[str]) -> None:
    if items is None:
        return
    if not isinstance(items, list):
        errors.append(f"invalid_{label}")
        return
    seen: dict[str, str | None] = {}
    for item in items:
        if not isinstance(item, dict):
            errors.append(f"invalid_{label}_item")
            continue
        source_path = _scope_source_path(item)
        if not source_path:
            errors.append(f"missing_source_subplan_mapping={label}")
            continue
        subplan_path = item.get("subplan_path")
        if isinstance(subplan_path, str) and subplan_path != source_path:
            errors.append(f"subplan_source_path_mismatch={source_path}")
        binding = implementation_contract_source_binding(root, source_path)
        for error in binding.get("errors", []):
            errors.append(str(error))
        source_digest = binding.get("implementation_contract_digest")
        if source_path in seen:
            if seen[source_path] != source_digest:
                errors.append(f"duplicate_source_subplan_mapping={source_path}")
            else:
                errors.append(f"duplicate_source_subplan_mapping={source_path}")
        seen[source_path] = source_digest if isinstance(source_digest, str) else None

        if item.get("source_subplan_path", source_path) != source_path:
            errors.append(f"source_subplan_path_mismatch={source_path}")
        for key in ("source_subplan_sha256", "subplan_sha256"):
            if key in item and item.get(key) != binding.get("source_subplan_sha256"):
                errors.append(f"{key}_mismatch={source_path}")
        if item.get("implementation_contract") != binding.get("implementation_contract"):
            errors.append(f"implementation_contract_source_mismatch={source_path}")
        if item.get("implementation_contract_digest") != binding.get("implementation_contract_digest"):
            errors.append(f"implementation_contract_digest_source_mismatch={source_path}")
        if item.get("validation_command_ids", []) != binding.get("validation_command_ids", []):
            errors.append(f"validation_command_ids_source_mismatch={source_path}")
        if item.get("security_review_required") != binding.get("security_review_required"):
            errors.append(f"security_review_required_source_mismatch={source_path}")
        if item.get("parent_acceptance_signal_ids", []) != binding.get("parent_acceptance_signal_ids", []):
            errors.append(f"parent_acceptance_signal_ids_source_mismatch={source_path}")
        if item.get("risk_class", "") != binding.get("risk_class", ""):
            errors.append(f"risk_class_source_mismatch={source_path}")
        if item.get("risk_domains", []) != binding.get("risk_domains", []):
            errors.append(f"risk_domains_source_mismatch={source_path}")


def validate_session_scope_source_bindings(root: Path, run: dict[str, object], errors: list[str]) -> None:
    active_scope = run.get("active_scope")
    if not isinstance(active_scope, dict):
        errors.append("invalid_active_scope")
        return
    _validate_session_scope_source_items(root, "subplan_contracts", active_scope.get("subplan_contracts"), errors)
    _validate_session_scope_source_items(root, "ready_queue", active_scope.get("ready_queue"), errors)


def validate_stage_snapshot(root: Path, run: dict[str, object], errors: list[str]) -> None:
    stage = str(run.get("stage", ""))
    snapshot = run.get("stage_snapshot")
    active_scope = run.get("active_scope") if isinstance(run.get("active_scope"), dict) else {}
    mutable_patterns = session_mutable_output_patterns(stage, active_scope)
    if not isinstance(snapshot, dict):
        errors.append("stage_snapshot_missing")
        return
    if snapshot.get("stage") != stage:
        errors.append("stage_snapshot_stage_mismatch")
    immutable = snapshot.get("immutable_inputs")
    if not isinstance(immutable, list):
        errors.append("stage_snapshot_immutable_inputs_invalid")
        immutable = []
    elif snapshot.get("immutable_input_digest") != snapshot_digest(stage, immutable):
        errors.append("stage_snapshot_immutable_digest_mismatch")
    if snapshot.get("immutable_input_digest") != run.get("source_snapshot_digest"):
        errors.append("stage_snapshot_source_digest_mismatch")
    if snapshot.get("template_bundle_digest") != run.get("template_bundle_digest"):
        errors.append("stage_snapshot_template_digest_mismatch")
    if snapshot.get("compiler_version") != SESSION_COMPILER_VERSION:
        errors.append("stage_snapshot_compiler_version_mismatch")
    if snapshot.get("session_spec_digest") != run.get("session_spec_digest"):
        errors.append("stage_snapshot_session_spec_digest_mismatch")

    mutable = snapshot.get("mutable_outputs")
    if not isinstance(mutable, dict):
        errors.append("stage_snapshot_mutable_outputs_invalid")
    else:
        declared = mutable.get("declared")
        if declared != mutable_patterns:
            errors.append("stage_snapshot_mutable_outputs_mismatch")
        duplicates = mutable.get("duplicates")
        if duplicates:
            errors.append("duplicate_mutable_output_declarations")
        for item in mutable.get("files", []) if isinstance(mutable.get("files"), list) else []:
            if not isinstance(item, dict):
                continue
            path = item.get("path")
            if item.get("exists") is True and isinstance(path, str) and not (root / path).is_file():
                errors.append(f"mutable_output_removed={path}")

    baseline = snapshot.get("workspace_baseline")
    if not isinstance(baseline, dict):
        errors.append("stage_snapshot_workspace_baseline_missing")
        return
    current = workspace_baseline(
        root,
        mutable_patterns,
        step4_unselected_subplan_paths(root, active_scope) if stage == "step4" else set(),
    )
    for key in ("branch", "base_commit", "workspace_inventory_sha256"):
        if baseline.get(key) != current.get(key):
            errors.append(f"workspace_baseline_mismatch={key}")


def validate_session_budget(run: dict[str, object], errors: list[str]) -> None:
    budget = run.get("budget_contract")
    errors.extend(validate_budget_contract(budget))
    errors.extend(validate_token_usage(run.get("token_usage")))
    if not isinstance(budget, dict):
        return
    if run.get("stage") == "step4":
        active_scope = run.get("active_scope")
        ready_queue = active_scope.get("ready_queue") if isinstance(active_scope, dict) else []
        if isinstance(ready_queue, list) and len(ready_queue) > budget_limit(budget, "max_selected_tasks"):
            errors.append("budget_selected_tasks_exceeded")
    subagent_plan = run.get("subagent_plan")
    if isinstance(subagent_plan, dict):
        roles = subagent_plan.get("roles")
        if isinstance(roles, list) and len(roles) > len(SESSION_AGENT_PROFILES):
            errors.append("budget_subagent_role_count_exceeded")


def validate_session_policy(run: dict[str, object], errors: list[str]) -> None:
    stage = str(run.get("stage", ""))
    mode = str(run.get("mode", ""))
    sources = run.get("source_snapshot")
    active_scope = run.get("active_scope")
    if stage not in STAGE_REFERENCES or mode not in STAGE_MODES.get(stage, set()):
        return
    if not isinstance(sources, list) or not isinstance(active_scope, dict):
        return
    expected = session_policy_envelope(stage, sources, mode, active_scope)
    expected_digest = canonical_json_digest(expected)
    if run.get("session_policy_digest") != expected_digest:
        errors.append("session_policy_digest_mismatch")
    for key, expected_value in expected.items():
        if run.get(key) != expected_value:
            errors.append(f"session_policy_mismatch={key}")


def default_session_run(
    root: Path,
    stage: str,
    mode: str | None = None,
    objective: str | None = None,
    run_id_suffix: str | None = None,
) -> dict[str, object]:
    selected_mode = mode or ("kimi_session_serial" if stage == "step4" else "wave")
    selected_objective = objective or f"Run KimiQB {stage} using current repository planning evidence."
    active_scope = collect_stage_scope(root, stage, selected_mode)
    mutable_patterns = session_mutable_output_patterns(stage, active_scope)
    sources = collect_sources(root, stage, active_scope)
    digest = snapshot_digest(stage, sources)
    subagent_plan = build_subagent_plan(stage, selected_mode, active_scope)
    spec_digest = session_spec_digest(stage, sources, selected_mode, selected_objective, active_scope)
    policy = session_policy_envelope(stage, sources, selected_mode, active_scope)
    policy_digest = canonical_json_digest(policy)
    bundle = template_bundle(stage)
    token_usage = token_usage_not_observed()
    snapshot = stage_snapshot(
        root,
        stage,
        sources,
        mutable_patterns,
        template_bundle_digest=str(bundle["digest"]),
        session_spec_digest_value=spec_digest,
        baseline_excluded_paths=step4_unselected_subplan_paths(root, active_scope) if stage == "step4" else set(),
    )
    suffix = invocation_suffix(run_id_suffix)
    run_id = session_run_id_for(stage, spec_digest, suffix)
    allowed_writes = mutable_patterns
    return {
        "session_run_schema_version": SESSION_RUN_SCHEMA_VERSION,
        "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
        "handoff_contract_version": HANDOFF_CONTRACT_VERSION,
        "session_spec_id": f"spec-{stage}-{spec_digest[:16]}",
        "session_spec_digest": spec_digest,
        "session_policy_digest": policy_digest,
        "session_run_id": run_id,
        "session_run_invocation_id": suffix,
        "stage": stage,
        "stage_contract_version": HANDOFF_CONTRACT_VERSION,
        "plugin_version": PLUGIN_VERSION,
        "template_bundle": bundle["templates"],
        "template_bundle_digest": bundle["digest"],
        "compiler": bundle["compiler"],
        "project_name": project_name(root),
        "mode": selected_mode,
        "objective": selected_objective,
        "source_snapshot": sources,
        "source_snapshot_digest": digest,
        "stage_snapshot": snapshot,
        "required_inputs": policy["required_inputs"],
        "allowed_writes": allowed_writes,
        "forbidden_writes": policy["forbidden_writes"],
        "active_scope": active_scope,
        "work_steps": stage_work_steps(stage, active_scope),
        "validation_checkpoints": policy["validation_checkpoints"],
        "stop_gates": policy["stop_gates"],
        "subagent_plan": subagent_plan,
        "context_token_budget": policy["context_token_budget"],
        "budget_contract": policy["budget_contract"],
        "token_usage": token_usage,
        "final_report_contract": policy["final_report_contract"],
        "user_confirmation_required": policy["user_confirmation_required"],
        "generated_at": f"invocation:{suffix}",
        "safety": policy["safety"],
    }


def validate_session_run(root: Path, run: dict[str, object]) -> list[str]:
    errors: list[str] = []
    stage = str(run.get("stage", ""))
    if stage not in STAGE_REFERENCES:
        errors.append(f"invalid_stage={stage or 'missing'}")
        return errors
    if run.get("session_run_schema_version") != SESSION_RUN_SCHEMA_VERSION:
        errors.append("invalid_session_run_schema_version")
    if run.get("plugin_version") != PLUGIN_VERSION:
        errors.append("invalid_plugin_version")
    mode = str(run.get("mode", ""))
    if mode not in STAGE_MODES[stage]:
        errors.append(f"invalid_session_mode={mode or 'missing'}")
    objective = run.get("objective")
    if not isinstance(objective, str) or not objective.strip():
        errors.append("objective_required")
    work_steps = run.get("work_steps")
    if (
        not isinstance(work_steps, list)
        or not work_steps
        or any(not isinstance(item, str) or not item.strip() for item in work_steps)
    ):
        errors.append("work_steps_required")
    elif isinstance(run.get("active_scope"), dict) and work_steps != stage_work_steps(stage, run["active_scope"]):
        errors.append("work_steps_mismatch")
    checkpoints = run.get("validation_checkpoints")
    if (
        not isinstance(checkpoints, list)
        or not checkpoints
        or any(not checkpoint_is_safe(item) for item in checkpoints)
    ):
        errors.append("invalid_validation_checkpoints")
    subagent_plan = run.get("subagent_plan")
    if not subagent_plan_is_valid(subagent_plan):
        errors.append("invalid_subagent_plan")
    token_budget = run.get("context_token_budget")
    if not isinstance(token_budget, dict) or token_budget.get("risk") not in {"low", "medium", "high"}:
        errors.append("invalid_context_token_budget")
    validate_session_budget(run, errors)
    validate_session_policy(run, errors)
    bundle = template_bundle(stage)
    if run.get("template_bundle") != bundle["templates"]:
        errors.append("template_bundle_mismatch")
    if run.get("template_bundle_digest") != bundle["digest"]:
        errors.append("template_bundle_digest_mismatch")
    if run.get("compiler") != bundle["compiler"]:
        errors.append("compiler_digest_mismatch")
    spec_digest = session_spec_digest(
        stage,
        run.get("source_snapshot", []) if isinstance(run.get("source_snapshot"), list) else [],
        str(run.get("mode", "")),
        str(run.get("objective", "")),
        run.get("active_scope", {}) if isinstance(run.get("active_scope"), dict) else {},
    )
    if run.get("session_spec_digest") != spec_digest:
        errors.append("stored_session_spec_digest_mismatch")
    if run.get("session_spec_id") != f"spec-{stage}-{spec_digest[:16]}":
        errors.append("stored_session_spec_id_mismatch")
    invocation = str(run.get("session_run_invocation_id", ""))
    if not invocation or invocation_suffix(invocation) != invocation:
        errors.append("invalid_session_run_invocation_id")
    expected_run_id = f"session-{stage}-{spec_digest[:12]}-{invocation}" if invocation else ""
    if run.get("session_run_id") != expected_run_id:
        errors.append("stored_session_run_id_mismatch")
    validate_session_scope_source_bindings(root, run, errors)
    validate_stage_snapshot(root, run, errors)
    text = json.dumps(run, sort_keys=True)
    if has_secret_like(text):
        errors.append("secret_like_content")

    allowed = set(str(item) for item in run.get("allowed_writes", []) if isinstance(item, str))
    forbidden = set(str(item) for item in run.get("forbidden_writes", []) if isinstance(item, str))
    if allowed & forbidden or any(glob_patterns_overlap(left, right) for left in allowed for right in forbidden):
        errors.append("overlapping_allowed_forbidden_writes")
    for path in allowed:
        if not is_safe_repo_path(path, allow_glob=True):
            errors.append(f"unsafe_path={path}")
    for path in forbidden:
        if not is_safe_repo_path(path, allow_glob=True, allow_home=True):
            errors.append(f"unsafe_path={path}")

    stored_sources = run.get("source_snapshot")
    if not isinstance(stored_sources, list):
        errors.append("invalid_source_snapshot")
        stored_sources = []
    elif run.get("source_snapshot_digest") != snapshot_digest(stage, stored_sources):
        errors.append("stored_source_snapshot_digest_mismatch")

    current_sources = collect_sources(
        root,
        stage,
        run.get("active_scope", {}) if isinstance(run.get("active_scope"), dict) else {},
    )
    current_digest = snapshot_digest(stage, current_sources)
    if run.get("source_snapshot_digest") != current_digest:
        errors.append("source_snapshot_mismatch")
    return errors


def render_prompt_from_run(run: dict[str, object]) -> str:
    stage = str(run["stage"])
    spec = read_text(SKILL_ROOT / f"references/session-specs/{stage}.md")
    handoff = ""
    for rel in STAGE_REFERENCES[stage]:
        if "/handoffs/" in rel:
            handoff = read_text(SKILL_ROOT / rel)
            break

    preview = [
        f"Stage: {stage}",
        f"Mode: {run['mode']}",
        f"Objective: {run['objective']}",
        f"Active phases/tasks: {json.dumps(run['active_scope'], sort_keys=True, separators=(',', ':'))}",
        "Deferred phases: see Planner-docs/Sub-Planing-Index.md when present",
        f"Expected writes: {', '.join(run['allowed_writes'])}",
        f"Validation: {len(run['validation_checkpoints'])} checkpoint(s)",
        f"Risk: context/token {run['context_token_budget']['risk']}",
        f"Budget contract: max_selected_tasks={run['budget_contract']['max_selected_tasks']} max_agent_attempts_per_role={run['budget_contract']['max_agent_attempts_per_role']} max_fix_cycles={run['budget_contract']['max_fix_cycles']} hard_total_token_limit={run['budget_contract']['hard_total_token_limit']} token_usage={run['token_usage']['status']}",
        f"Subagents: {json.dumps(run['subagent_plan'], sort_keys=True, separators=(',', ':'))}",
        f"User confirmation required: {run['user_confirmation_required']}",
        f"Stop gates: {', '.join(run['stop_gates'])}",
    ]

    lines = [
        f"# KimiQB Session Prompt: {stage}",
        "",
        "Use /skill:kimiqb.",
        "",
        "## Session Preview",
        "",
        *preview,
        "",
        "## Session Compiler Safety",
        "",
        "- Treat this as a prompt preview, not an executor.",
        "- Do not install dependencies, commit, push, create pull requests, deploy, edit global Kimi Code config, or sync plugin caches unless explicitly asked in the active run.",
        "- Recompute source snapshot hashes before starting or resuming; stop on mismatch.",
        "",
        "## Stage Spec",
        "",
        spec.strip(),
        "",
        "## Source Snapshot",
        "",
    ]
    for source in run["source_snapshot"]:
        visible = f" value={source['value']}" if source.get("scope") == "git" and "value" in source else ""
        lines.append(f"- {source['scope']}:{source['path']} sha256={source['sha256']}{visible}")
    if handoff:
        lines += ["", "## Canonical Handoff", "", handoff.strip()]
    return "\n".join(lines) + "\n"


def compile_session(
    root: Path,
    stage: str,
    output_dir: Path | None = None,
    mode: str | None = None,
    objective: str | None = None,
    *,
    replace: bool = False,
    resume: bool = False,
    run_id_suffix: str | None = None,
) -> dict[str, object]:
    root = root.resolve()
    if stage not in STAGE_REFERENCES:
        raise ValueError(f"unsupported stage: {stage}")
    if resume and output_dir is None:
        raise ValueError("resume_requires_output_dir")
    run = default_session_run(root, stage, mode, objective, run_id_suffix)
    errors = validate_session_run(root, run)
    if errors:
        raise ValueError(";".join(errors))
    out_dir = (output_dir or root / "Planner-docs" / "Session-Runs" / str(run["session_run_id"])).resolve()
    if not is_inside(root, out_dir):
        raise ValueError("output_dir must be inside the target repository")
    if resume:
        run_path = out_dir / "Session-Run.json"
        if not run_path.is_file():
            raise ValueError(f"session_run_resume_missing={out_dir.relative_to(root).as_posix()}")
        existing = load_session_run(run_path)
        existing_errors = validate_session_run(root, existing)
        if existing_errors:
            raise ValueError(";".join(existing_errors))
        result_path = out_dir / "Session-Result.json"
        result = load_session_run(result_path) if result_path.is_file() else {
            "session_run_id": existing.get("session_run_id"),
            "stage": existing.get("stage"),
            "status": "resumed",
        }
        return {"run": existing, "result": result, "output_dir": out_dir.as_posix()}
    if out_dir.exists() and not replace and not resume:
        raise ValueError(f"session_run_already_exists={out_dir.relative_to(root).as_posix()}")
    out_dir.mkdir(parents=True, exist_ok=True)

    blockers = stage_prerequisite_blockers(root, stage)
    run_json = json.dumps(run, indent=2, sort_keys=True) + "\n"
    if blockers:
        result = {
            "session_run_id": run["session_run_id"],
            "stage": stage,
            "status": "blocked",
            "blockers": blockers,
            "session_run_sha256": sha256_bytes(run_json.encode("utf-8")),
            "budget_contract": run["budget_contract"],
            "token_usage": run["token_usage"],
            "source_count": len(run["source_snapshot"]),
            "next_action": "Repair missing prerequisites, then prepare this Session run again.",
        }
        (out_dir / "Session-Run.json").write_text(run_json, encoding="utf-8")
        prompt_path = out_dir / "Session-Prompt.md"
        if prompt_path.exists():
            prompt_path.unlink()
        (out_dir / "Session-Result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return {"run": run, "result": result, "output_dir": out_dir.as_posix()}

    prompt = render_prompt_from_run(run)
    result = {
        "session_run_id": run["session_run_id"],
        "stage": stage,
        "status": "ready",
        "session_run_sha256": sha256_bytes(run_json.encode("utf-8")),
        "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
        "budget_contract": run["budget_contract"],
        "token_usage": run["token_usage"],
        "source_count": len(run["source_snapshot"]),
        "next_action": "Review Session-Prompt.md, then paste it into a new Kimi Code session only if the stage and safety policy match the intended run.",
    }
    (out_dir / "Session-Run.json").write_text(run_json, encoding="utf-8")
    (out_dir / "Session-Prompt.md").write_text(prompt, encoding="utf-8")
    (out_dir / "Session-Result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"run": run, "result": result, "output_dir": out_dir.as_posix()}


def render_session_file(root: Path, session_run_path: Path, output: Path | None = None) -> str:
    run = load_session_run(session_run_path)
    errors = validate_session_run(root.resolve(), run)
    if errors:
        raise ValueError(";".join(errors))
    prompt = render_prompt_from_run(run)
    if output:
        output.write_text(prompt, encoding="utf-8")
    return prompt


def load_session_run(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Session-Run.json must contain an object")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile deterministic KimiQB Session previews.")
    sub = parser.add_subparsers(dest="command")

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--root", default=".", help="Target repository root.")
        p.add_argument("--stage", required=True, choices=sorted(STAGE_REFERENCES), help="Session stage.")

    collect = sub.add_parser("collect", help="Print source snapshot JSON.")
    add_common(collect)
    prepare = sub.add_parser("prepare", help="Write Session-Run.json, Session-Prompt.md, and Session-Result.json.")
    add_common(prepare)
    prepare.add_argument("--mode")
    prepare.add_argument("--objective")
    prepare.add_argument("--output-dir")
    prepare.add_argument("--replace", action="store_true")
    prepare.add_argument("--resume", action="store_true")
    prepare.add_argument("--run-id-suffix")
    validate = sub.add_parser("validate", help="Validate Session-Run.json against current snapshot.")
    validate.add_argument("--root", default=".")
    validate.add_argument("--session-run", required=True)
    render = sub.add_parser("render", help="Render Session-Prompt.md from Session-Run.json.")
    render.add_argument("--root", default=".")
    render.add_argument("--session-run", required=True)
    render.add_argument("--output")

    parser.add_argument("--root", default=".", help=argparse.SUPPRESS)
    parser.add_argument("--stage", choices=sorted(STAGE_REFERENCES), help=argparse.SUPPRESS)
    parser.add_argument("--output-dir", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    try:
        if args.command is None:
            if not args.stage:
                parser.error("--stage is required")
            compiled = compile_session(Path(args.root), args.stage, Path(args.output_dir) if args.output_dir else None)
            print(f"session_run_status={compiled['result']['status']}")
            print(f"session_run_id={compiled['result']['session_run_id']}")
            print(f"output_dir={compiled['output_dir']}")
            return 0 if compiled["result"]["status"] == "ready" else 1
        if args.command == "collect":
            root = Path(args.root).resolve()
            sources = collect_sources(root, args.stage)
            print(json.dumps({"stage": args.stage, "source_snapshot": sources}, indent=2, sort_keys=True))
            return 0
        if args.command == "prepare":
            compiled = compile_session(
                Path(args.root),
                args.stage,
                Path(args.output_dir) if args.output_dir else None,
                args.mode,
                args.objective,
                replace=args.replace,
                resume=args.resume,
                run_id_suffix=args.run_id_suffix,
            )
            print(f"session_run_status={compiled['result']['status']}")
            print(f"session_run_id={compiled['result']['session_run_id']}")
            print(f"output_dir={compiled['output_dir']}")
            return 0 if compiled["result"]["status"] == "ready" else 1
        if args.command == "validate":
            errors = validate_session_run(Path(args.root).resolve(), load_session_run(Path(args.session_run)))
            if errors:
                print("session_run_status=failed")
                for error in errors:
                    print(f"error={error}")
                return 1
            print("session_run_status=passed")
            return 0
        if args.command == "render":
            prompt = render_session_file(Path(args.root), Path(args.session_run), Path(args.output) if args.output else None)
            if not args.output:
                print(prompt, end="")
            return 0
    except Exception as exc:
        print("session_run_status=failed", file=sys.stderr)
        print(f"error={exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
