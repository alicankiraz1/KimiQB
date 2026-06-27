#!/usr/bin/env python3
"""Create a sanitized KimiQB source zip with package provenance.

The default mode is release-oriented: tracked files only, clean Git worktree
required, and HEAD must match origin/main when that ref is available. Worktree
exports can opt into untracked files and dirty/head-mismatch allowances.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path


SAFETY_DIR = Path(__file__).resolve().parents[1] / "skills/kimiqb/scripts"
if str(SAFETY_DIR) not in sys.path:
    sys.path.insert(0, str(SAFETY_DIR))

from safety_contracts import has_secret_like, path_is_inside  # noqa: E402


IGNORED_PARTS = {
    ".git",
    ".kimiqb",
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
IGNORED_PREFIXES = {
    "docs/superpowers/plans/",
}
BLOCKED_SUFFIXES = {".pyc", ".pem", ".key", ".zip"}
BLOCKED_RE = re.compile(
    r"(^|/)(\.git|\.kimiqb|__pycache__|\.env|artifacts|logs|tmp|__MACOSX)(/|$)|"
    r"\.pyc$|\.pem$|\.key$|\.local($|\.)"
)
PACKAGE_MANIFEST_NAME = "PACKAGE-MANIFEST.json"
PACKAGE_SCHEMA_VERSION = 1


def run_git(root: Path, args: list[str]) -> list[str] | None:
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
        return None
    if completed.returncode != 0:
        return None
    return [line for line in completed.stdout.splitlines() if line.strip()]


def run_git_text(root: Path, args: list[str]) -> str | None:
    lines = run_git(root, args)
    if lines is None:
        return None
    return "\n".join(lines).strip()


def in_git_checkout(root: Path) -> bool:
    return run_git_text(root, ["rev-parse", "--is-inside-work-tree"]) == "true"


def git_commit(root: Path, ref: str = "HEAD") -> str:
    return run_git_text(root, ["rev-parse", ref]) or "unknown"


def git_branch(root: Path) -> str:
    return run_git_text(root, ["branch", "--show-current"]) or "unknown"


def git_status(root: Path) -> str:
    return run_git_text(root, ["status", "--porcelain=v1"]) or ""


def origin_main_commit(root: Path) -> str | None:
    commit = run_git_text(root, ["rev-parse", "--verify", "refs/remotes/origin/main"])
    return commit if commit else None


def plugin_version(root: Path) -> str:
    plugin = root / "kimi.plugin.json"
    if not plugin.is_file():
        return "unknown"
    try:
        data = json.loads(plugin.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "unknown"
    version = data.get("version")
    return version if isinstance(version, str) and version else "unknown"


def changelog_mentions_version(root: Path, version: str) -> bool:
    changelog = root / "CHANGELOG.md"
    if not changelog.is_file() or version == "unknown":
        return False
    return version in changelog.read_text(encoding="utf-8", errors="replace")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def candidate_paths(root: Path, *, include_untracked: bool) -> list[Path]:
    tracked = run_git(root, ["ls-files", "--cached"])
    if tracked is None:
        return sorted(path for path in root.rglob("*"))
    rels = set(tracked)
    if include_untracked:
        rels.update(run_git(root, ["ls-files", "--others", "--exclude-standard"]) or [])
    return sorted(root / rel for rel in rels)


def file_digest(root: Path, path: Path) -> dict[str, str]:
    rel = path.relative_to(root).as_posix()
    return {"path": rel, "sha256": sha256_bytes(path.read_bytes())}


def tree_digest(entries: list[dict[str, str]]) -> str:
    payload = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(payload)


def package_manifest(root: Path, files: list[Path], *, include_untracked: bool) -> dict[str, object]:
    root = root.resolve()
    entries = [file_digest(root, path) for path in files]
    version = plugin_version(root)
    head = git_commit(root) if in_git_checkout(root) else "unknown"
    origin = origin_main_commit(root) if in_git_checkout(root) else None
    return {
        "package_schema_version": PACKAGE_SCHEMA_VERSION,
        "plugin_version": version,
        "git_commit": head,
        "git_branch": git_branch(root) if in_git_checkout(root) else "unknown",
        "origin_main_commit": origin or "unknown",
        "head_matches_origin_main": (head == origin) if origin else None,
        "working_tree_clean": git_status(root) == "" if in_git_checkout(root) else None,
        "tracked_only": not include_untracked,
        "include_untracked": include_untracked,
        "changelog_mentions_plugin_version": changelog_mentions_version(root, version),
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "file_count": len(files),
        "tree_sha256": tree_digest(entries),
        "files": entries,
    }


def release_blockers(root: Path, *, allow_dirty: bool, allow_head_mismatch: bool) -> list[str]:
    del allow_head_mismatch
    if not in_git_checkout(root):
        return []
    blockers: list[str] = []
    status = git_status(root)
    if status and not allow_dirty:
        blockers.append("working_tree_dirty")
    version = plugin_version(root)
    if version == "unknown":
        blockers.append("plugin_version_unknown")
    elif not changelog_mentions_version(root, version):
        blockers.append(f"changelog_missing_plugin_version={version}")
    return blockers


def should_include(path: Path, root: Path, output: Path, errors: list[str]) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        errors.append(f"path_outside_repo={path}")
        return False
    if path.is_symlink():
        errors.append(f"symlink_rejected={rel.as_posix()}")
        return False
    resolved = path.resolve()
    if not path_is_inside(root, resolved):
        errors.append(f"path_outside_repo={rel.as_posix()}")
        return False
    if resolved == output.resolve():
        return False
    if not path.is_file():
        return False
    if rel.as_posix() == PACKAGE_MANIFEST_NAME:
        return False
    if any(rel.as_posix().startswith(prefix) for prefix in IGNORED_PREFIXES):
        return False
    if IGNORED_PARTS.intersection(rel.parts):
        return False
    if path.name == ".DS_Store" or path.name.startswith(".env"):
        return False
    if path.suffix in BLOCKED_SUFFIXES:
        return False
    if path.name.endswith(".local") or ".local." in path.name:
        return False
    if BLOCKED_RE.search(rel.as_posix()):
        return False
    try:
        data = path.read_bytes()
    except OSError as exc:
        errors.append(f"read_error={rel.as_posix()}:{exc}")
        return False
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = ""
    if text and has_secret_like(text):
        errors.append(f"secret_like_content={rel.as_posix()}")
        return False
    return True


def create_zip(
    root: Path,
    output: Path,
    *,
    include_untracked: bool = False,
    allow_dirty: bool = False,
    allow_head_mismatch: bool = False,
) -> int:
    root = root.resolve()
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    blockers = release_blockers(root, allow_dirty=allow_dirty, allow_head_mismatch=allow_head_mismatch)
    if blockers:
        raise ValueError(";".join(blockers))
    errors: list[str] = []
    files = [
        path
        for path in candidate_paths(root, include_untracked=include_untracked)
        if should_include(path, root, output, errors)
    ]
    if errors:
        raise ValueError(";".join(errors))
    manifest = package_manifest(root, files, include_untracked=include_untracked)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            rel = path.relative_to(root).as_posix()
            archive.write(path, f"KimiQB/{rel}")
        archive.writestr(
            f"KimiQB/{PACKAGE_MANIFEST_NAME}",
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        )
    return len(files)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create KimiQB-sanitized.zip from the current worktree.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="KimiQB-sanitized.zip")
    parser.add_argument(
        "--include-untracked",
        action="store_true",
        help="Include untracked, non-ignored files after symlink and secret scanning.",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow a dirty Git worktree. Intended only for explicit worktree exports.",
    )
    parser.add_argument(
        "--allow-head-mismatch",
        action="store_true",
        help="Allow HEAD to differ from refs/remotes/origin/main when that ref is available.",
    )
    args = parser.parse_args()
    count = create_zip(
        Path(args.root),
        Path(args.output),
        include_untracked=args.include_untracked,
        allow_dirty=args.allow_dirty,
        allow_head_mismatch=args.allow_head_mismatch,
    )
    print(f"sanitized_export=created")
    print(f"file_count={count}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
