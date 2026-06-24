#!/usr/bin/env python3
"""Exercise the apply-run controller through its public CLI.

This is a behavioral smoke for the artifact controller, not a product-code
executor and not a direct Kimi Code runtime caller. It uses a disposable repository,
drives the public prepare/dispatch/record-agent/transition/validate/finalize
commands, writes the minimum evidence reports a real implementation run must
produce, and verifies that the final artifact state is complete.
"""

from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
APPLY_RUN = REPO_ROOT / "skills/kimiqb/scripts/apply_run.py"
if REPO_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, REPO_ROOT.as_posix())

from tests.test_validate_planner_docs import write_audit, write_valid_step2_fixture  # noqa: E402


def fail(message: str) -> None:
    print(f"apply_behavior_smoke_failed={message}")
    raise SystemExit(1)


def run_apply(args: list[str], *, cwd: Path) -> str:
    completed = subprocess.run(
        [sys.executable, APPLY_RUN.as_posix(), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )
    if completed.returncode != 0:
        fail(f"command_failed={' '.join(args)} stdout={completed.stdout.strip()} stderr={completed.stderr.strip()}")
    return completed.stdout


def run_apply_expect_failure(args: list[str], *, cwd: Path, expected: str) -> str:
    completed = subprocess.run(
        [sys.executable, APPLY_RUN.as_posix(), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )
    combined = f"{completed.stdout}\n{completed.stderr}"
    if completed.returncode == 0:
        fail(f"command_unexpected_success={' '.join(args)} stdout={completed.stdout.strip()}")
    if expected not in combined:
        fail(f"expected_failure_missing={expected} stdout={completed.stdout.strip()} stderr={completed.stderr.strip()}")
    return combined


def parse_key(output: str, key: str) -> str:
    prefix = f"{key}="
    for line in output.splitlines():
        if line.startswith(prefix):
            return line.split("=", 1)[1]
    fail(f"missing_output_key={key}")
    raise AssertionError("unreachable")


def write_fixture(root: Path) -> None:
    docs = write_valid_step2_fixture(root)
    subplan = docs / "Faz-1-Plans" / "Faz1.1-local-contract.md"
    subplan.write_text(
        subplan.read_text(encoding="utf-8")
        + "\n".join(
            [
                "",
                "Additional Apply smoke signals:",
                "- behavioral acceptance: smoke artifact reaches complete state.",
                "- allowed write paths: src/smoke.py",
                "- forbidden paths: .env",
                "- parent acceptance signal: PAS-SMOKE-1",
                "- depends_on: none",
                "- validation command argv: python3 -m unittest",
                "- security review: not required",
                "- algorithmic invariant: task transition order remains monotonic.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    write_audit(docs, "PASS")


def write_verified_reports(
    run_dir: Path,
    task_id: str,
    brief_sha256: str,
    *,
    implementation_contract_digest: str,
    task_contract_digest: str,
    security_required: bool,
    validation_commands: list[object],
) -> None:
    task_dir = run_dir / task_id
    patch = "\n".join(
        [
            "diff --git a/src/feature_1_1.py b/src/feature_1_1.py",
            "--- a/src/feature_1_1.py",
            "+++ b/src/feature_1_1.py",
            "@@ -0,0 +1 @@",
            "+VALUE = 1",
            "",
        ]
    )
    patch_sha = hashlib.sha256(patch.encode("utf-8")).hexdigest()
    validation_evidence = [
        {**command, "exit_code": 0, "output_sha256": hashlib.sha256(b"validation passed\n").hexdigest()}
        for command in validation_commands
        if isinstance(command, dict)
    ]
    (task_dir / "Review-Package.patch").write_text(patch, encoding="utf-8")
    (task_dir / "Implementer-Report.json").write_text(
        json.dumps(
            {
                "status": "DONE",
                "task_id": task_id,
                "brief_sha256": brief_sha256,
                "implementation_contract_digest": implementation_contract_digest,
                "task_contract_digest": task_contract_digest,
                "implementer_agent_id": "smoke-impl",
                "files_changed": ["src/feature_1_1.py"],
                "validation_evidence": validation_evidence,
                "diff_sha256": patch_sha,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    task_review = {
        "task_id": task_id,
        "brief_sha256": brief_sha256,
        "implementation_contract_digest": implementation_contract_digest,
        "task_contract_digest": task_contract_digest,
        "reviewer_agent_id": "smoke-reviewer",
        "spec_compliance": "pass",
        "task_quality": "approved",
        "security_review": "pass" if security_required else "not_required",
        "evidence": ["CLI behavior smoke reviewed transition trace and validation evidence."],
    }
    if security_required:
        task_review["security_reviewer_agent_id"] = "smoke-security"
    (task_dir / "Task-Review.json").write_text(
        json.dumps(task_review, sort_keys=True),
        encoding="utf-8",
    )
    (run_dir / "Final-Review.json").write_text(
        json.dumps(
            {
                "status": "pass",
                "reviewed_task_ids": [task_id],
                "global_validations": [{"id": "VAL-REPO", "argv": ["make", "check"], "exit_code": 0}],
                "evidence": ["CLI behavior smoke validated and finalized the apply run."],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        write_fixture(root)

        output = run_apply(
            [
                "prepare",
                "--root",
                root.as_posix(),
                "--mode",
                "direct",
                "--run-id-suffix",
                "behavior-smoke",
                "--allow-non-git-unsafe",
            ],
            cwd=root,
        )
        run_dir = Path(parse_key(output, "run_dir"))
        progress = json.loads((run_dir / "Progress.json").read_text(encoding="utf-8"))
        tasks = progress.get("tasks")
        if not isinstance(tasks, list) or len(tasks) != 1:
            fail("expected_one_task")
        task = tasks[0]
        task_id = task["task_id"]
        brief_sha256 = task["brief_sha256"]
        security_required = task.get("security_review_required") is True

        run_apply(["validate", "--run-dir", run_dir.as_posix(), "--root", root.as_posix()], cwd=root)
        actors = {
            "IMPLEMENTING": "smoke-impl",
            "IMPLEMENTED": "smoke-impl",
            "TASK_REVIEW": "smoke-reviewer",
            "SECURITY_REVIEW": "smoke-security",
            "VERIFIED": "smoke-reviewer",
        }
        states = ["IMPLEMENTING", "IMPLEMENTED", "TASK_REVIEW"]
        if security_required:
            states.append("SECURITY_REVIEW")
        states.append("VERIFIED")
        for state in states:
            run_apply(
                [
                    "transition",
                    "--run-dir",
                    run_dir.as_posix(),
                    "--task-id",
                    task_id,
                    "--to",
                    state,
                    "--actor",
                    actors[state],
                    "--evidence",
                    f"behavior smoke reached {state}",
                ],
                cwd=root,
            )

        write_verified_reports(
            run_dir,
            task_id,
            brief_sha256,
            implementation_contract_digest=str(task.get("implementation_contract_digest", "")),
            task_contract_digest=str(task.get("task_contract_digest", "")),
            security_required=security_required,
            validation_commands=task.get("validation_commands", []),
        )
        run_apply(["validate", "--run-dir", run_dir.as_posix(), "--root", root.as_posix()], cwd=root)
        run_apply(
            [
                "finalize",
                "--run-dir",
                run_dir.as_posix(),
                "--actor",
                "smoke-controller",
                "--evidence",
                "behavior smoke final review passed",
            ],
            cwd=root,
        )
        run_apply(["validate", "--run-dir", run_dir.as_posix(), "--root", root.as_posix()], cwd=root)

        result = json.loads((run_dir / "Result.json").read_text(encoding="utf-8"))
        events = [json.loads(line) for line in (run_dir / "Events.jsonl").read_text(encoding="utf-8").splitlines()]
        if result.get("status") != "complete":
            fail(f"unexpected_result_status={result.get('status')}")
        if events[-1].get("event_type") != "apply_run_finalized":
            fail("missing_finalize_event")
        if [event.get("sequence") for event in events] != list(range(1, len(events) + 1)):
            fail("non_contiguous_event_sequence")

        dispatch_output = run_apply(
            [
                "prepare",
                "--root",
                root.as_posix(),
                "--mode",
                "kimi_session_serial",
                "--run-id-suffix",
                "dispatch-smoke",
                "--allow-non-git-unsafe",
            ],
            cwd=root,
        )
        dispatch_run_dir = Path(parse_key(dispatch_output, "run_dir"))
        dispatch_progress = json.loads((dispatch_run_dir / "Progress.json").read_text(encoding="utf-8"))
        dispatch_task = dispatch_progress["tasks"][0]
        dispatch_task_id = dispatch_task["task_id"]
        run_apply_expect_failure(
            [
                "transition",
                "--run-dir",
                dispatch_run_dir.as_posix(),
                "--task-id",
                dispatch_task_id,
                "--to",
                "IMPLEMENTING",
                "--actor",
                "dispatch-impl",
                "--evidence",
                "packet missing should block",
            ],
            cwd=root,
            expected=f"subagent_dispatch_packet_missing={dispatch_task_id}",
        )
        packet_output = run_apply(
            [
                "dispatch",
                "--run-dir",
                dispatch_run_dir.as_posix(),
                "--task-id",
                dispatch_task_id,
                "--role",
                "implementer",
                "--actor",
                "smoke-controller",
                "--evidence",
                "behavior smoke prepared dispatch packet",
            ],
            cwd=root,
        )
        packet_path = Path(parse_key(packet_output, "packet_path"))
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        if packet.get("spawn_tool") != "kimi_session_dispatch_artifact":
            fail("dispatch_packet_missing_spawn_tool")
        if packet.get("spawn_request", {}).get("fork_context") is not False:
            fail("dispatch_packet_not_fresh_context")
        run_apply_expect_failure(
            [
                "transition",
                "--run-dir",
                dispatch_run_dir.as_posix(),
                "--task-id",
                dispatch_task_id,
                "--to",
                "IMPLEMENTING",
                "--actor",
                "dispatch-impl",
                "--evidence",
                "spawn record missing should block",
            ],
            cwd=root,
            expected=f"subagent_dispatch_spawn_required={dispatch_task_id}",
        )
        run_apply(
            [
                "record-agent",
                "--run-dir",
                dispatch_run_dir.as_posix(),
                "--task-id",
                dispatch_task_id,
                "--role",
                "implementer",
                "--agent-id",
                "dispatch-agent-1",
                "--status",
                "spawned",
                "--actor",
                "smoke-controller",
                "--evidence",
                "behavior smoke recorded spawned agent",
            ],
            cwd=root,
        )
        run_apply(
            [
                "transition",
                "--run-dir",
                dispatch_run_dir.as_posix(),
                "--task-id",
                dispatch_task_id,
                "--to",
                "IMPLEMENTING",
                "--actor",
                "dispatch-impl",
                "--evidence",
                "dispatch packet accepted",
            ],
            cwd=root,
        )
        run_apply_expect_failure(
            [
                "transition",
                "--run-dir",
                dispatch_run_dir.as_posix(),
                "--task-id",
                dispatch_task_id,
                "--to",
                "IMPLEMENTED",
                "--actor",
                "dispatch-impl",
                "--evidence",
                "completion record missing should block",
            ],
            cwd=root,
            expected=f"subagent_dispatch_completion_required={dispatch_task_id}",
        )
        run_apply(
            [
                "record-agent",
                "--run-dir",
                dispatch_run_dir.as_posix(),
                "--task-id",
                dispatch_task_id,
                "--role",
                "implementer",
                "--agent-id",
                "dispatch-agent-1",
                "--status",
                "completed",
                "--actor",
                "smoke-controller",
                "--summary",
                "behavior smoke implementation agent completed",
                "--evidence",
                "behavior smoke recorded completed agent",
            ],
            cwd=root,
        )
        run_apply(
            [
                "transition",
                "--run-dir",
                dispatch_run_dir.as_posix(),
                "--task-id",
                dispatch_task_id,
                "--to",
                "IMPLEMENTED",
                "--actor",
                "dispatch-impl",
                "--evidence",
                "completion packet accepted",
            ],
            cwd=root,
        )
        run_apply(["validate", "--run-dir", dispatch_run_dir.as_posix(), "--root", root.as_posix()], cwd=root)

        recovery_output = run_apply(
            [
                "prepare",
                "--root",
                root.as_posix(),
                "--mode",
                "direct",
                "--run-id-suffix",
                "recovery-smoke",
                "--allow-non-git-unsafe",
            ],
            cwd=root,
        )
        recovery_run_dir = Path(parse_key(recovery_output, "run_dir"))
        recovery_progress = json.loads((recovery_run_dir / "Progress.json").read_text(encoding="utf-8"))
        recovery_task = recovery_progress["tasks"][0]
        recovery_task_id = recovery_task["task_id"]
        run_apply(
            [
                "transition",
                "--run-dir",
                recovery_run_dir.as_posix(),
                "--task-id",
                recovery_task_id,
                "--to",
                "IMPLEMENTING",
                "--actor",
                "stale-impl",
                "--evidence",
                "behavior smoke starts stale lock scenario",
            ],
            cwd=root,
        )
        lock_path = recovery_run_dir / "Writer-Lock.json"
        stale_lock = json.loads(lock_path.read_text(encoding="utf-8"))
        stale_lock["acquired_at"] = "2000-01-01T00:00:00Z"
        lock_path.write_text(json.dumps(stale_lock, sort_keys=True), encoding="utf-8")
        recovery_progress = json.loads((recovery_run_dir / "Progress.json").read_text(encoding="utf-8"))
        recovery_progress["active_writer_locks"] = [stale_lock]
        recovery_progress["tasks"][0]["writer_lock"] = stale_lock
        (recovery_run_dir / "Progress.json").write_text(json.dumps(recovery_progress, sort_keys=True), encoding="utf-8")
        run_apply_expect_failure(
            ["validate", "--run-dir", recovery_run_dir.as_posix(), "--root", root.as_posix()],
            cwd=root,
            expected=f"writer_lock_expired={recovery_task_id}",
        )
        run_apply(
            [
                "recover-lock",
                "--run-dir",
                recovery_run_dir.as_posix(),
                "--task-id",
                recovery_task_id,
                "--to",
                "NEEDS_CONTEXT",
                "--actor",
                "smoke-controller",
                "--evidence",
                "behavior smoke recovered expired writer lock",
            ],
            cwd=root,
        )
        run_apply(["validate", "--run-dir", recovery_run_dir.as_posix(), "--root", root.as_posix()], cwd=root)
        recovery_progress = json.loads((recovery_run_dir / "Progress.json").read_text(encoding="utf-8"))
        if recovery_progress["tasks"][0]["state"] != "NEEDS_CONTEXT":
            fail("recovery_state_not_needs_context")
        if lock_path.exists():
            fail("recovery_left_writer_lock_file")

    print("apply_behavior_smoke=passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
