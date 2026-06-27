#!/usr/bin/env python3
"""Collect deterministic Session/Apply prompt-size metrics.

These checks estimate prompt size from local artifacts only. They do not call
Kimi Code, spawn subagents, or claim exact model token billing.
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SESSION_RUN = REPO_ROOT / "skills/kimiqb/scripts/session_run.py"
APPLY_RUN = REPO_ROOT / "skills/kimiqb/scripts/apply_run.py"
STEP4_HANDOFF = REPO_ROOT / "skills/kimiqb/references/handoffs/run-step4.md"

if REPO_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, REPO_ROOT.as_posix())

from tests.test_validate_planner_docs import write_audit, write_valid_step2_fixture  # noqa: E402


def fail(message: str) -> None:
    print(f"session_apply_metric_checks_failed={message}")
    raise SystemExit(1)


def approx_tokens(text: str) -> int:
    # Deterministic dependency-free estimate. This is not model billing.
    return max(1, math.ceil(len(text) / 4))


def metric(name: str, text: str) -> dict[str, int | str]:
    return {
        "name": name,
        "bytes": len(text.encode("utf-8")),
        "chars": len(text),
        "words": len(text.split()),
        "estimated_tokens": approx_tokens(text),
    }


def run_command(args: list[str], *, cwd: Path) -> str:
    completed = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    if completed.returncode != 0:
        fail(f"command_failed={' '.join(args)} stdout={completed.stdout.strip()} stderr={completed.stderr.strip()}")
    return completed.stdout


def parse_key(output: str, key: str) -> str:
    prefix = f"{key}="
    for line in output.splitlines():
        if line.startswith(prefix):
            return line.split("=", 1)[1]
    fail(f"missing_output_key={key}")
    raise AssertionError("unreachable")


def write_fixture(root: Path) -> None:
    docs = write_valid_step2_fixture(root)
    write_audit(docs, "PASS")


def compile_session_prompt(root: Path, mode: str, suffix: str) -> str:
    output = run_command(
        [
            sys.executable,
            SESSION_RUN.as_posix(),
            "prepare",
            "--root",
            root.as_posix(),
            "--stage",
            "step4",
            "--mode",
            mode,
            "--run-id-suffix",
            suffix,
        ],
        cwd=root,
    )
    out_dir = Path(parse_key(output, "output_dir"))
    prompt_path = out_dir / "Session-Prompt.md"
    if not prompt_path.is_file():
        fail(f"missing_session_prompt={mode}")
    prompt = prompt_path.read_text(encoding="utf-8")
    if "Planner-docs/Faz-1-Plans/Faz1.1-local-contract.md" not in prompt:
        fail(f"dynamic_prompt_missing_ready_subplan={mode}")
    if mode not in prompt:
        fail(f"dynamic_prompt_missing_mode={mode}")
    return prompt


def prepare_apply_run(root: Path, mode: str, suffix: str) -> Path:
    output = run_command(
        [
            sys.executable,
            APPLY_RUN.as_posix(),
            "prepare",
            "--root",
            root.as_posix(),
            "--mode",
            mode,
            "--run-id-suffix",
            suffix,
            "--allow-non-git-unsafe",
        ],
        cwd=root,
    )
    return Path(parse_key(output, "run_dir"))


def first_task(run_dir: Path) -> tuple[str, Path]:
    progress = json.loads((run_dir / "Progress.json").read_text(encoding="utf-8"))
    tasks = progress.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        fail(f"missing_apply_task={run_dir}")
    task = tasks[0]
    if not isinstance(task, dict) or not isinstance(task.get("task_id"), str):
        fail(f"invalid_apply_task={run_dir}")
    task_id = str(task["task_id"])
    return task_id, run_dir / task_id


def subagent_dispatch_message(root: Path, run_dir: Path, task_id: str) -> str:
    output = run_command(
        [
            sys.executable,
            APPLY_RUN.as_posix(),
            "dispatch",
            "--run-dir",
            run_dir.as_posix(),
            "--task-id",
            task_id,
            "--role",
            "implementer",
            "--actor",
            "metric-controller",
            "--evidence",
            "metric collection generated dispatch packet",
        ],
        cwd=root,
    )
    packet_path = Path(parse_key(output, "packet_path"))
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    message = packet.get("spawn_request", {}).get("message")
    if not isinstance(message, str):
        fail("dispatch_packet_missing_message")
    if "Use only this fresh task context" not in message:
        fail("dispatch_message_not_fresh_context")
    if "Structured Implementation Contract" not in message:
        fail("dispatch_message_missing_structured_contract")
    return message


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        write_fixture(root)

        static_handoff = STEP4_HANDOFF.read_text(encoding="utf-8")
        direct_prompt = compile_session_prompt(root, "direct", "metrics-direct")
        subagent_prompt = compile_session_prompt(root, "kimi_session_serial", "metrics-subagent")

        direct_run_dir = prepare_apply_run(root, "direct", "metrics-direct")
        direct_task_id, direct_task_dir = first_task(direct_run_dir)
        direct_brief = (direct_task_dir / "Brief.md").read_text(encoding="utf-8")
        if direct_task_id not in direct_brief:
            fail("direct_brief_missing_task_id")

        subagent_run_dir = prepare_apply_run(root, "kimi_session_serial", "metrics-subagent")
        subagent_task_id, _subagent_task_dir = first_task(subagent_run_dir)
        dispatch_message = subagent_dispatch_message(root, subagent_run_dir, subagent_task_id)

        metrics = [
            metric("static_step4_handoff", static_handoff),
            metric("dynamic_step4_session_direct", direct_prompt),
            metric("dynamic_step4_session_kimi_session_serial", subagent_prompt),
            metric("apply_direct_brief", direct_brief),
            metric("apply_subagent_dispatch_message", dispatch_message),
        ]

    for item in metrics:
        if int(item["estimated_tokens"]) <= 0:
            fail(f"invalid_estimated_tokens={item['name']}")
        print(
            "metric="
            f"{item['name']} bytes={item['bytes']} words={item['words']} estimated_tokens={item['estimated_tokens']}"
        )
    print("session_apply_metric_checks=passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
