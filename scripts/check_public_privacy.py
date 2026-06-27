#!/usr/bin/env python3
"""Scan public release-facing files for local/private identifiers."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


PUBLIC_FILES = {
    "README.md",
    "CHANGELOG.md",
    "docs/USAGE.md",
    "docs/MAINTAINING.md",
    "docs/INSTALLATION.md",
}
PUBLIC_DIRS = {
    "docs/release-audits",
    "docs/release-evidence",
}
PRIVATE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("mac_user_path", re.compile(r"/Users/")),
    ("linux_home_path", re.compile(r"/home/")),
    ("private_tmp_path", re.compile(r"/private/(?:tmp|var)/")),
    ("codex_attachment_path", re.compile(r"\.codex/attachments/")),
    ("windows_user_path", re.compile(r"[A-Za-z]:\\Users\\")),
    (
        "local_uuid",
        re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"),
    ),
    ("codex_live_agent_id", re.compile(r"\b019e[a-f0-9]{28}\b")),
)


def git_tracked(root: Path) -> set[str] | None:
    try:
        completed = subprocess.run(
            ["git", "ls-files"],
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
    return {line.strip() for line in completed.stdout.splitlines() if line.strip()}


def candidate_files(root: Path) -> list[Path]:
    tracked = git_tracked(root)
    candidates: set[Path] = set()
    for rel in PUBLIC_FILES:
        path = root / rel
        if path.is_file() and (tracked is None or rel in tracked):
            candidates.add(path)
    for rel_dir in PUBLIC_DIRS:
        base = root / rel_dir
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            if tracked is None or rel in tracked:
                candidates.add(path)
    return sorted(candidates)


def scan_file(root: Path, path: Path) -> list[str]:
    findings: list[str] = []
    rel = path.relative_to(root).as_posix()
    for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        for rule, pattern in PRIVATE_PATTERNS:
            if pattern.search(line):
                findings.append(f"{rel}:{line_number}:{rule}")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check public KimiQB artifacts for private local identifiers.")
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    findings: list[str] = []
    for path in candidate_files(root):
        findings.extend(scan_file(root, path))
    if findings:
        print("public_privacy_check=failed")
        for finding in findings:
            print(finding)
        return 1
    print("public_privacy_check=passed")
    print(f"public_privacy_files_scanned={len(candidate_files(root))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
