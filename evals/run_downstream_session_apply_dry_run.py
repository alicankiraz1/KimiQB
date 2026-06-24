#!/usr/bin/env python3
"""Run a representative downstream Step 2 -> Step 4 Session/Apply dry run.

This gate uses a disposable git repository with small product code and tests.
It validates the planner docs, compiles Session previews, prepares a subagent
Apply run, records artifact-level agent evidence, and finalizes the run. It
does not call Kimi Code, spawn real subagents, commit the source repo, push, open a
PR, deploy, or mutate external systems.
"""

from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / "skills/kimiqb/scripts/validate_planner_docs.py"
SESSION_RUN = REPO_ROOT / "skills/kimiqb/scripts/session_run.py"
APPLY_RUN = REPO_ROOT / "skills/kimiqb/scripts/apply_run.py"

if REPO_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, REPO_ROOT.as_posix())

from tests.test_validate_planner_docs import write_audit, write_valid_step2_fixture  # noqa: E402


def fail(message: str) -> None:
    print(f"downstream_session_apply_dry_run_failed={message}")
    raise SystemExit(1)


def run_command(args: list[str], *, cwd: Path, timeout: int = 30) -> str:
    completed = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
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


def write_downstream_code(root: Path) -> None:
    (root / "src").mkdir()
    (root / "tests").mkdir()
    (root / "src/__init__.py").write_text("", encoding="utf-8")
    (root / "src/feature_1_1.py").write_text(
        "\n".join(
            [
                "def normalize_signal(value: str) -> str:",
                "    return value.strip().lower().replace(' ', '-')",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (root / "src/feature_2_1.py").write_text(
        "\n".join(
            [
                "def gateway_status(enabled: bool) -> str:",
                "    return 'ready' if enabled else 'blocked'",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (root / "tests/test_feature_1_1.py").write_text(
        "\n".join(
            [
                "import unittest",
                "",
                "from src.feature_1_1 import normalize_signal",
                "",
                "",
                "class Feature11Tests(unittest.TestCase):",
                "    def test_normalize_signal(self) -> None:",
                "        self.assertEqual(normalize_signal(' Local Contract '), 'local-contract')",
                "",
                "",
                "if __name__ == '__main__':",
                "    unittest.main()",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (root / "tests/test_feature_2_1.py").write_text(
        "\n".join(
            [
                "import unittest",
                "",
                "from src.feature_2_1 import gateway_status",
                "",
                "",
                "class Feature21Tests(unittest.TestCase):",
                "    def test_gateway_status(self) -> None:",
                "        self.assertEqual(gateway_status(True), 'ready')",
                "        self.assertEqual(gateway_status(False), 'blocked')",
                "",
                "",
                "if __name__ == '__main__':",
                "    unittest.main()",
                "",
            ]
        ),
        encoding="utf-8",
    )


def adapt_validation_commands(docs: Path) -> None:
    replacements = {
        "python3 -m pytest tests/test_feature_1_1.py -q": "python3 -m unittest tests/test_feature_1_1.py",
        "python3 -m pytest tests/test_feature_2_1.py -q": "python3 -m unittest tests/test_feature_2_1.py",
        '"argv": ["python3", "-m", "pytest", "tests/test_feature_1_1.py", "-q"]': (
            '"argv": ["python3", "-m", "unittest", "tests/test_feature_1_1.py"]'
        ),
        '"argv": ["python3", "-m", "pytest", "tests/test_feature_2_1.py", "-q"]': (
            '"argv": ["python3", "-m", "unittest", "tests/test_feature_2_1.py"]'
        ),
    }
    for path in [docs / "Sub-Planing-Index.md", *sorted(docs.glob("Faz-*-Plans/*.md"))]:
        text = path.read_text(encoding="utf-8")
        for old, new in replacements.items():
            text = text.replace(old, new)
        path.write_text(text, encoding="utf-8")


def run_validator(root: Path, mode: str) -> str:
    return run_command(
        [sys.executable, VALIDATOR.as_posix(), "--root", root.as_posix(), "--mode", mode, "--strict"],
        cwd=root,
    )


def prepare_session(root: Path, stage: str, mode: str, suffix: str) -> Path:
    output = run_command(
        [
            sys.executable,
            SESSION_RUN.as_posix(),
            "prepare",
            "--root",
            root.as_posix(),
            "--stage",
            stage,
            "--mode",
            mode,
            "--run-id-suffix",
            suffix,
        ],
        cwd=root,
    )
    if "session_run_status=ready" not in output:
        fail(f"session_not_ready={stage}:{mode}")
    out_dir = Path(parse_key(output, "output_dir"))
    session_run = out_dir / "Session-Run.json"
    prompt = out_dir / "Session-Prompt.md"
    if not session_run.is_file() or not prompt.is_file():
        fail(f"session_outputs_missing={stage}:{mode}")
    run_command(
        [
            sys.executable,
            SESSION_RUN.as_posix(),
            "validate",
            "--root",
            root.as_posix(),
            "--session-run",
            session_run.as_posix(),
        ],
        cwd=root,
    )
    return out_dir


def git_checkpoint(root: Path) -> None:
    run_command(["git", "init"], cwd=root)
    run_command(["git", "checkout", "-b", "kimi/downstream-dry-run"], cwd=root)
    run_command(["git", "add", "."], cwd=root)
    run_command(
        [
            "git",
            "-c",
            "user.name=KimiQB Dry Run",
            "-c",
            "user.email=kimiqb-dry-run@example.invalid",
            "commit",
            "-m",
            "Initial downstream dry run fixture",
        ],
        cwd=root,
    )
    status = run_command(["git", "status", "--porcelain=v1"], cwd=root)
    if status.strip():
        fail(f"git_fixture_dirty={status.strip()}")


def prepare_apply(root: Path) -> Path:
    output = run_command(
        [
            sys.executable,
            APPLY_RUN.as_posix(),
            "prepare",
            "--root",
            root.as_posix(),
            "--mode",
            "kimi_session_serial",
            "--run-id-suffix",
            "downstream-dry-run",
        ],
        cwd=root,
    )
    run_dir = Path(parse_key(output, "run_dir"))
    run = json.loads((run_dir / "Apply-Run.json").read_text(encoding="utf-8"))
    if run.get("workspace_detected") != "git":
        fail("apply_run_not_git_backed")
    if run.get("dirty_state") != "clean":
        fail(f"apply_run_dirty_state={run.get('dirty_state')}")
    if run.get("user_approval") is not False:
        fail("apply_run_unexpected_user_approval")
    return run_dir


def first_task(run_dir: Path) -> tuple[str, str, str, str, bool, list[object]]:
    progress = json.loads((run_dir / "Progress.json").read_text(encoding="utf-8"))
    tasks = progress.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != 1:
        fail("expected_one_downstream_task")
    task = tasks[0]
    if not isinstance(task, dict):
        fail("invalid_downstream_task")
    task_id = str(task.get("task_id", ""))
    brief_sha = str(task.get("brief_sha256", ""))
    security_required = task.get("security_review_required") is True
    implementation_contract_digest = str(task.get("implementation_contract_digest", ""))
    task_contract_digest = str(task.get("task_contract_digest", ""))
    validation_commands = task.get("validation_commands", [])
    if not isinstance(validation_commands, list):
        validation_commands = []
    if not task_id or not brief_sha:
        fail("task_missing_id_or_brief_hash")
    if "Planner-docs/Faz-1-Plans/Faz1.1-local-contract.md" != task.get("source_subplan_path"):
        fail(f"unexpected_task_subplan={task.get('source_subplan_path')}")
    return task_id, brief_sha, implementation_contract_digest, task_contract_digest, security_required, validation_commands


def run_apply(root: Path, args: list[str]) -> str:
    return run_command([sys.executable, APPLY_RUN.as_posix(), *args], cwd=root)


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
            "@@ -1,2 +1,2 @@",
            " def normalize_signal(value: str) -> str:",
            "-    return value.strip().lower().replace(' ', '-')",
            "+    return value.strip().lower().replace(' ', '-')",
            "",
        ]
    )
    patch_sha = hashlib.sha256(patch.encode("utf-8")).hexdigest()
    validation_evidence = [
        {**command, "exit_code": 0, "output_sha256": hashlib.sha256(b"downstream validation passed\n").hexdigest()}
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
                "implementer_agent_id": "downstream-impl-agent",
                "files_changed": ["src/feature_1_1.py"],
                "validation_evidence": validation_evidence,
                "diff_sha256": patch_sha,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    review: dict[str, object] = {
        "task_id": task_id,
        "brief_sha256": brief_sha256,
        "implementation_contract_digest": implementation_contract_digest,
        "task_contract_digest": task_contract_digest,
        "reviewer_agent_id": "downstream-review-agent",
        "spec_compliance": "pass",
        "task_quality": "approved",
        "security_review": "pass" if security_required else "not_required",
        "evidence": ["Downstream dry-run artifacts preserve fresh context and validator evidence."],
    }
    if security_required:
        review["security_reviewer_agent_id"] = "downstream-security-agent"
    (task_dir / "Task-Review.json").write_text(json.dumps(review, sort_keys=True) + "\n", encoding="utf-8")
    (run_dir / "Final-Review.json").write_text(
        json.dumps(
            {
                "status": "pass",
                "reviewed_task_ids": [task_id],
                "global_validations": [
                    {
                        "id": "VAL-DOWNSTREAM-DISCOVER",
                        "argv": ["python3", "-m", "unittest", "discover", "-s", "tests", "-v"],
                        "exit_code": 0,
                    }
                ],
                "evidence": ["Downstream Step 2, Step 3, Step 4, Session, and Apply dry-run gates passed."],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def drive_subagent_apply(root: Path, run_dir: Path) -> None:
    (
        task_id,
        brief_sha,
        implementation_contract_digest,
        task_contract_digest,
        security_required,
        validation_commands,
    ) = first_task(run_dir)
    run_apply(root, ["validate", "--run-dir", run_dir.as_posix(), "--root", root.as_posix()])
    packet_output = run_apply(
        root,
        [
            "dispatch",
            "--run-dir",
            run_dir.as_posix(),
            "--task-id",
            task_id,
            "--role",
            "implementer",
            "--actor",
            "downstream-controller",
            "--evidence",
            "downstream dry run prepared fresh implementer packet",
        ],
    )
    packet_path = Path(parse_key(packet_output, "packet_path"))
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    message = packet.get("spawn_request", {}).get("message")
    if not isinstance(message, str) or "Use only this fresh task context" not in message:
        fail("downstream_dispatch_not_fresh_context")
    if "Structured Implementation Contract" not in message:
        fail("downstream_dispatch_missing_contract")

    run_apply(
        root,
        [
            "record-agent",
            "--run-dir",
            run_dir.as_posix(),
            "--task-id",
            task_id,
            "--role",
            "implementer",
            "--agent-id",
            "downstream-impl-agent",
            "--status",
            "spawned",
            "--actor",
            "downstream-controller",
            "--evidence",
            "downstream dry run recorded spawned implementer",
        ],
    )
    run_apply(
        root,
        [
            "transition",
            "--run-dir",
            run_dir.as_posix(),
            "--task-id",
            task_id,
            "--to",
            "IMPLEMENTING",
            "--actor",
            "downstream-impl-agent",
            "--evidence",
            "downstream implementer accepted fresh brief",
        ],
    )
    run_apply(
        root,
        [
            "record-agent",
            "--run-dir",
            run_dir.as_posix(),
            "--task-id",
            task_id,
            "--role",
            "implementer",
            "--agent-id",
            "downstream-impl-agent",
            "--status",
            "completed",
            "--actor",
            "downstream-controller",
            "--summary",
            "downstream dry run artifact implementation completed",
            "--evidence",
            "downstream dry run recorded completed implementer",
        ],
    )
    for state, actor in [
        ("IMPLEMENTED", "downstream-impl-agent"),
        ("TASK_REVIEW", "downstream-review-agent"),
        ("SECURITY_REVIEW", "downstream-security-agent"),
        ("VERIFIED", "downstream-review-agent"),
    ]:
        if state == "SECURITY_REVIEW" and not security_required:
            continue
        run_apply(
            root,
            [
                "transition",
                "--run-dir",
                run_dir.as_posix(),
                "--task-id",
                task_id,
                "--to",
                state,
                "--actor",
                actor,
                "--evidence",
                f"downstream dry run reached {state}",
            ],
        )
    write_verified_reports(
        run_dir,
        task_id,
        brief_sha,
        implementation_contract_digest=implementation_contract_digest,
        task_contract_digest=task_contract_digest,
        security_required=security_required,
        validation_commands=validation_commands,
    )
    run_apply(root, ["validate", "--run-dir", run_dir.as_posix(), "--root", root.as_posix()])
    run_apply(
        root,
        [
            "finalize",
            "--run-dir",
            run_dir.as_posix(),
            "--actor",
            "downstream-controller",
            "--evidence",
            "downstream dry run final review passed",
        ],
    )
    run_apply(root, ["validate", "--run-dir", run_dir.as_posix(), "--root", root.as_posix()])
    result = json.loads((run_dir / "Result.json").read_text(encoding="utf-8"))
    if result.get("status") != "complete":
        fail(f"downstream_apply_not_complete={result.get('status')}")


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        write_downstream_code(root)
        docs = write_valid_step2_fixture(root)
        adapt_validation_commands(docs)

        unit_output = run_command([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=root)
        if "FAILED" in unit_output:
            fail("downstream_unit_tests_failed")

        step2_output = run_validator(root, "step2")
        if "validation_mode=step2" not in step2_output:
            fail("step2_validator_missing_mode")
        preflight_output = run_validator(root, "step3-preflight")
        if "validation_mode=step3-preflight" not in preflight_output:
            fail("step3_preflight_missing_mode")

        write_audit(docs, "PASS")
        step3_output = run_validator(root, "step3")
        if "validation_mode=step3" not in step3_output:
            fail("step3_validator_missing_mode")
        step4_output = run_validator(root, "step4")
        if "validation_mode=step4" not in step4_output:
            fail("step4_validator_missing_mode")

        prepare_session(root, "step2", "wave", "downstream-step2")
        prepare_session(root, "step3", "audit", "downstream-step3")
        step4_session_dir = prepare_session(root, "step4", "kimi_session_serial", "downstream-step4")
        step4_prompt = (step4_session_dir / "Session-Prompt.md").read_text(encoding="utf-8")
        if "Planner-docs/Faz-1-Plans/Faz1.1-local-contract.md" not in step4_prompt:
            fail("step4_session_missing_ready_subplan")
        if "kimi_session_serial" not in step4_prompt:
            fail("step4_session_missing_subagent_mode")

        git_checkpoint(root)
        apply_run_dir = prepare_apply(root)
        drive_subagent_apply(root, apply_run_dir)

        print("downstream_session_apply_dry_run=passed")
        print("downstream_stage_validations=step2,step3-preflight,step3,step4")
        print(f"downstream_apply_run_dir={apply_run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
