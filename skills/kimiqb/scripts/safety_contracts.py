#!/usr/bin/env python3
"""Shared safety checks for KimiQB local helper scripts.

The helpers in this directory are artifact validators and preview compilers,
not executors. This module keeps command, path, and secret checks consistent
across planner validation, session previews, apply-run artifacts, and sanitized
exports.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import re
import shlex
from pathlib import Path


SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("openrouter_api_key", re.compile(r"\bsk-or-v1-[A-Za-z0-9_-]{20,}\b", re.IGNORECASE)),
    ("openai_api_key", re.compile(r"\bsk-(?!or-v1-)[A-Za-z0-9_-]{20,}\b")),
    ("github_pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("github_legacy_pat", re.compile(r"\bghp_[A-Za-z0-9]{20,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private_key", re.compile(r"BEGIN (?:RSA|OPENSSH|DSA|EC|PRIVATE) KEY", re.IGNORECASE)),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
)

SHELL_METACHAR_RE = re.compile(r"(?:&&|\|\||[;&|<>`]|[$]\(|\n|\r)")
MUTATING_COMMAND_INTENT_RE = re.compile(
    r"\b(?:deploy|release|publish|push|merge|destroy|delete|remove|prune|reset|checkout|apply|install|upgrade|"
    r"migrate|seed|prod|production|live|remote|clean)\b",
    re.IGNORECASE,
)
MUTATING_EXECUTABLES = {
    "rm",
    "rmdir",
    "mv",
    "cp",
    "chmod",
    "chown",
    "sudo",
    "su",
    "ssh",
    "scp",
    "rsync",
    "curl",
    "wget",
    "kubectl",
    "terraform",
    "docker",
    "gh",
    "git",
    "bash",
    "sh",
    "zsh",
}

SAFE_PYTHON_MODULES = {"pytest", "unittest", "compileall"}
SAFE_MAKE_TARGETS = {"check", "test", "lint", "typecheck", "smoke", "ci-local", "build"}
SAFE_JS_SCRIPTS = {"test", "lint", "typecheck", "build", "check"}
SAFE_RUFF_COMMANDS = {"check"}
BUDGET_SCHEMA_VERSION = 1
BUDGET_INT_LIMITS = {
    "soft_input_token_limit": (1, 10_000_000),
    "hard_total_token_limit": (1, 10_000_000),
    "max_subagent_total_tokens": (0, 10_000_000),
    "max_agent_attempts_per_role": (1, 10),
    "max_fix_cycles": (0, 10),
    "max_selected_tasks": (0, 50),
    "checkpoint_after_tasks": (1, 50),
}
DEFAULT_BUDGET_CONTRACT = {
    "budget_schema_version": BUDGET_SCHEMA_VERSION,
    "soft_input_token_limit": 300_000,
    "hard_total_token_limit": 600_000,
    "max_subagent_total_tokens": 250_000,
    "max_agent_attempts_per_role": 2,
    "max_fix_cycles": 2,
    "max_selected_tasks": 4,
    "checkpoint_after_tasks": 1,
    "pause_on_soft_limit": True,
    "enforcement_mode": "advisory_or_runtime_supported",
}
TOKEN_USAGE_NOT_OBSERVED = {
    "status": "not_observed",
    "input_tokens": "not_observed",
    "output_tokens": "not_observed",
    "total_tokens": "not_observed",
    "source": "runtime_not_available",
}
IMPLEMENTATION_CONTRACT_SECTION_RE = re.compile(
    r"^### Implementation Contract[ \t]*\n+(?P<body>.*?)(?=^### |^## |\Z)",
    re.DOTALL | re.IGNORECASE | re.MULTILINE,
)
IMPLEMENTATION_CONTRACT_JSON_RE = re.compile(r"```json\s*(?P<json>.*?)\s*```", re.DOTALL | re.IGNORECASE)


def secret_findings(text: str) -> list[str]:
    return [name for name, pattern in SECRET_PATTERNS if pattern.search(text)]


def has_secret_like(text: str) -> bool:
    return bool(secret_findings(text))


def path_is_inside(parent: Path, child: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json(value: object) -> object:
    return json.loads(json.dumps(value, sort_keys=True, separators=(",", ":")))


def canonical_json_digest(value: object) -> str:
    return sha256_bytes(json.dumps(canonical_json(value), sort_keys=True, separators=(",", ":")).encode("utf-8"))


def default_budget_contract() -> dict[str, object]:
    return canonical_json(DEFAULT_BUDGET_CONTRACT)


def token_usage_not_observed() -> dict[str, object]:
    return canonical_json(TOKEN_USAGE_NOT_OBSERVED)


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def budget_limit(contract: object, key: str, fallback: int | None = None) -> int:
    if isinstance(contract, dict) and _is_int(contract.get(key)):
        return int(contract[key])
    default = DEFAULT_BUDGET_CONTRACT.get(key)
    if _is_int(default):
        return int(default)
    if fallback is None:
        raise KeyError(key)
    return fallback


def validate_budget_contract(value: object, prefix: str = "budget_contract") -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return [f"{prefix}_missing"]
    if value.get("budget_schema_version") != BUDGET_SCHEMA_VERSION:
        errors.append(f"invalid_{prefix}_schema_version")
    for key, (minimum, maximum) in BUDGET_INT_LIMITS.items():
        current = value.get(key)
        if not _is_int(current) or not minimum <= int(current) <= maximum:
            errors.append(f"invalid_{prefix}={key}")
    if (
        _is_int(value.get("hard_total_token_limit"))
        and _is_int(value.get("soft_input_token_limit"))
        and int(value["hard_total_token_limit"]) < int(value["soft_input_token_limit"])
    ):
        errors.append(f"{prefix}_hard_below_soft")
    if (
        _is_int(value.get("hard_total_token_limit"))
        and _is_int(value.get("max_subagent_total_tokens"))
        and int(value["max_subagent_total_tokens"]) > int(value["hard_total_token_limit"])
    ):
        errors.append(f"{prefix}_subagent_tokens_exceed_hard_limit")
    if (
        _is_int(value.get("checkpoint_after_tasks"))
        and _is_int(value.get("max_selected_tasks"))
        and int(value["max_selected_tasks"]) > 0
        and int(value["checkpoint_after_tasks"]) > int(value["max_selected_tasks"])
    ):
        errors.append(f"{prefix}_checkpoint_exceeds_selected_task_cap")
    if value.get("pause_on_soft_limit") is not True:
        errors.append(f"{prefix}_must_pause_on_soft_limit")
    if value.get("enforcement_mode") != "advisory_or_runtime_supported":
        errors.append(f"invalid_{prefix}_enforcement_mode")
    return errors


def validate_token_usage(value: object, prefix: str = "token_usage") -> list[str]:
    if value == TOKEN_USAGE_NOT_OBSERVED:
        return []
    errors: list[str] = []
    if not isinstance(value, dict):
        return [f"{prefix}_missing"]
    if value.get("status") not in {"observed", "not_observed"}:
        errors.append(f"invalid_{prefix}_status")
    if value.get("status") == "not_observed" and value != TOKEN_USAGE_NOT_OBSERVED:
        errors.append(f"{prefix}_not_observed_must_be_explicit")
    if value.get("status") == "observed":
        for key in ("input_tokens", "output_tokens", "total_tokens"):
            current = value.get(key)
            if not _is_int(current) or int(current) < 0:
                errors.append(f"invalid_{prefix}={key}")
        if (
            _is_int(value.get("input_tokens"))
            and _is_int(value.get("output_tokens"))
            and _is_int(value.get("total_tokens"))
            and int(value["input_tokens"]) + int(value["output_tokens"]) != int(value["total_tokens"])
        ):
            errors.append(f"{prefix}_total_mismatch")
    return errors


def _list_of_strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def implementation_contract_validation_command_ids(contract: dict[str, object]) -> list[str]:
    commands = contract.get("validation_commands")
    if not isinstance(commands, list):
        return []
    ids: list[str] = []
    for command in commands:
        if not isinstance(command, dict):
            continue
        command_id = command.get("id")
        if isinstance(command_id, str) and command_id.strip():
            ids.append(command_id.strip())
    return ids


def implementation_contract_paths(contract: dict[str, object]) -> list[str]:
    paths = contract.get("implementation_paths")
    if not isinstance(paths, list):
        return []
    normalized: list[str] = []
    for item in paths:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        if isinstance(path, str) and path.strip():
            normalized.append(path.strip())
    return normalized


def implementation_contract_source_binding(root: Path, source_subplan_path: str) -> dict[str, object]:
    errors: list[str] = []
    if not is_safe_repo_path(source_subplan_path):
        return {"errors": [f"unsafe_source_subplan_path={source_subplan_path or 'missing'}"]}
    path = (root / source_subplan_path).resolve()
    if not path_is_inside(root, path):
        return {"errors": [f"unsafe_source_subplan_path={source_subplan_path}"]}
    if not path.is_file():
        return {"errors": [f"missing_source_subplan={source_subplan_path}"]}

    text = path.read_text(encoding="utf-8", errors="replace")
    section_matches = list(IMPLEMENTATION_CONTRACT_SECTION_RE.finditer(text))
    if len(section_matches) != 1:
        errors.append(f"implementation_contract_section_count={source_subplan_path}:{len(section_matches)}")
        contract: dict[str, object] = {}
    else:
        json_matches = list(IMPLEMENTATION_CONTRACT_JSON_RE.finditer(section_matches[0].group("body")))
        if len(json_matches) != 1:
            errors.append(f"implementation_contract_json_block_count={source_subplan_path}:{len(json_matches)}")
            contract = {}
        else:
            try:
                parsed = json.loads(json_matches[0].group("json"))
            except json.JSONDecodeError:
                errors.append(f"implementation_contract_json_invalid={source_subplan_path}")
                parsed = {}
            contract = canonical_json(parsed) if isinstance(parsed, dict) else {}
            if not isinstance(parsed, dict):
                errors.append(f"implementation_contract_must_be_object={source_subplan_path}")

    digest = canonical_json_digest(contract) if contract else None
    return {
        "errors": errors,
        "source_subplan_path": source_subplan_path,
        "source_subplan_sha256": sha256_bytes(path.read_bytes()),
        "implementation_contract": contract,
        "implementation_contract_digest": digest,
        "validation_command_ids": implementation_contract_validation_command_ids(contract),
        "parent_acceptance_signal_ids": _list_of_strings(contract.get("parent_signals")),
        "security_review_required": contract.get("security_review_required") if isinstance(contract.get("security_review_required"), bool) else False,
        "risk_class": contract.get("risk_class") if isinstance(contract.get("risk_class"), str) else "",
        "risk_domains": _list_of_strings(contract.get("risk_domains")),
        "dependencies": canonical_json(contract.get("dependencies", {})),
        "outputs": _list_of_strings(contract.get("outputs")),
        "implementation_paths": implementation_contract_paths(contract),
    }


def _strip_value(value: str) -> str:
    return value.strip().strip("`").strip("'\"")


def _path_parts(value: str) -> tuple[str, ...]:
    return Path(value).parts


def is_safe_repo_path(value: str, *, allow_glob: bool = False, allow_home: bool = False) -> bool:
    target = _strip_value(value)
    if not target:
        return False
    if target.startswith("~"):
        return allow_home and not any(part == ".." for part in _path_parts(target))
    path = Path(target)
    if path.is_absolute():
        return False
    if any(part == ".." for part in path.parts):
        return False
    if not allow_glob and any(char in target for char in "*?[]"):
        return False
    return True


def unsafe_path_in_arg(value: str) -> bool:
    raw = _strip_value(value)
    candidates = [raw]
    if "=" in raw:
        candidates.append(raw.split("=", 1)[1])
    for candidate in candidates:
        if not candidate or candidate in {".", "./", "./..."}:
            continue
        if candidate.startswith(("http://", "https://")):
            return True
        if candidate.startswith("~"):
            return True
        path = Path(candidate)
        if path.is_absolute():
            return True
        if any(part == ".." for part in path.parts):
            return True
    return False


def glob_patterns_overlap(left: str, right: str) -> bool:
    left = _strip_value(left)
    right = _strip_value(right)
    if left == right:
        return True
    if fnmatch.fnmatch(left, right) or fnmatch.fnmatch(right, left):
        return True
    left_prefix = re.split(r"[*?\[]", left, maxsplit=1)[0].rstrip("/")
    right_prefix = re.split(r"[*?\[]", right, maxsplit=1)[0].rstrip("/")
    if left_prefix and right.startswith(left_prefix + "/"):
        return True
    if right_prefix and left.startswith(right_prefix + "/"):
        return True
    return False


def parse_legacy_command(command: str) -> list[str] | None:
    command = command.strip().strip("`")
    if len(command.split()) < 2:
        return None
    if SHELL_METACHAR_RE.search(command):
        return None
    try:
        return shlex.split(command)
    except ValueError:
        return None


def safe_validation_argv(argv: object, *, allow_uv: bool = True) -> bool:
    if not isinstance(argv, list) or len(argv) < 2:
        return False
    normalized: list[str] = []
    for item in argv:
        if not isinstance(item, str):
            return False
        value = item.strip()
        if not value or SHELL_METACHAR_RE.search(value):
            return False
        if any(pattern.search(value) for _, pattern in SECRET_PATTERNS):
            return False
        if unsafe_path_in_arg(value):
            return False
        normalized.append(value)

    executable = Path(normalized[0]).name
    if executable in MUTATING_EXECUTABLES:
        return False
    if MUTATING_COMMAND_INTENT_RE.search(" ".join(normalized)):
        return False

    if executable in {"python", "python3"}:
        return len(normalized) >= 3 and normalized[1] == "-m" and normalized[2] in SAFE_PYTHON_MODULES
    if executable == "pytest":
        return True
    if executable == "uv":
        return allow_uv and len(normalized) >= 4 and normalized[1] == "run" and safe_validation_argv(
            normalized[2:], allow_uv=False
        )
    if executable == "make":
        return len(normalized) >= 2 and all(arg in SAFE_MAKE_TARGETS for arg in normalized[1:])
    if executable == "npm":
        return len(normalized) >= 3 and normalized[1] == "run" and normalized[2] in SAFE_JS_SCRIPTS
    if executable in {"pnpm", "yarn"}:
        if len(normalized) >= 3 and normalized[1] == "run":
            return normalized[2] in SAFE_JS_SCRIPTS
        return len(normalized) >= 2 and normalized[1] in SAFE_JS_SCRIPTS
    if executable == "cargo":
        return len(normalized) >= 2 and normalized[1] == "test"
    if executable == "go":
        return len(normalized) >= 2 and normalized[1] == "test"
    if executable == "ruff":
        return len(normalized) >= 2 and normalized[1] in SAFE_RUFF_COMMANDS
    if executable == "mypy":
        return True
    return False


def exact_validation_command(command: str) -> bool:
    argv = parse_legacy_command(command)
    return bool(argv and safe_validation_argv(argv))


def safe_validation_command_item(item: object) -> bool:
    if not isinstance(item, dict):
        return False
    argv = item.get("argv")
    if argv is not None:
        return safe_validation_argv(argv)
    command = item.get("command")
    return isinstance(command, str) and exact_validation_command(command)
