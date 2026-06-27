from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_validate_planner_docs import write_audit, write_ledger, write_valid_step2_fixture


REPO_ROOT = Path(__file__).resolve().parents[1]
APPLY_RUN = REPO_ROOT / "skills/kimiqb/scripts/apply_run.py"


def load_apply_module():
    spec = importlib.util.spec_from_file_location("kimiqb_apply_run", APPLY_RUN)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load apply_run from {APPLY_RUN}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


APPLY_MODULE = load_apply_module()
VALIDATION_OUTPUT_SHA256 = APPLY_MODULE.sha256_bytes(b"validation passed\n")


class ApplyRunTests(unittest.TestCase):
    def write_apply_fixture(self, root: Path) -> None:
        docs = write_valid_step2_fixture(root)
        subplan = docs / "Faz-1-Plans" / "Faz1.1-local-contract.md"
        subplan.write_text(
            subplan.read_text(encoding="utf-8")
            + "\n".join(
                [
                    "",
                    "Additional Apply fresh-context signals:",
                    "- behavioral acceptance: API returns durable state.",
                    "- allowed write paths: src/example.py",
                    "- forbidden paths: .env",
                    "- parent acceptance signal: PAS-1",
                    "- depends_on: none",
                    "- validation command argv: python3 -m unittest",
                    "- security review: not required",
                    "- algorithmic invariant: state transition order remains monotonic.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        write_audit(docs, "PASS")

    def write_no_action_fixture(self, root: Path) -> None:
        docs = write_valid_step2_fixture(root)
        write_audit(
            docs,
            "PASS",
            readiness_rows=[
                "| Sub-Plan Path | Status | Finding IDs | Dependency State | Reason | Required Repair |",
                "|---|---|---|---|---|---|",
                "| Planner-docs/Faz-1-Plans/Faz1.1-local-contract.md | COMPLETE | none | satisfied | Already verified. | none |",
                "| Planner-docs/Faz-2-Plans/Faz2.1-live-gateway.md | SUPERSEDED | none | satisfied | Replaced by later plan. | none |",
            ],
        )

    def init_git_repo(self, root: Path) -> None:
        subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)

    def create_apply_run(self, root: Path, mode: str, *args, **kwargs) -> dict[str, object]:
        kwargs.setdefault("allow_non_git_unsafe", True)
        kwargs.setdefault("allow_unverified_git_worktree", True)
        return APPLY_MODULE.create_apply_run(root, mode, *args, **kwargs)

    def first_task_id(self, run_dir: Path) -> str:
        progress = json.loads((run_dir / "Progress.json").read_text(encoding="utf-8"))
        return progress["tasks"][0]["task_id"]

    def mark_task_verified(self, run_dir: Path, security: str = "not_required") -> None:
        progress = json.loads((run_dir / "Progress.json").read_text(encoding="utf-8"))
        task = progress["tasks"][0]
        task_id = task["task_id"]
        security_verdict = "pass" if security == "pass" or task.get("security_review_required") is True else security
        task["state"] = "BRIEFED"
        task["security_review_required"] = security_verdict == "pass"
        task["writer_lock"] = None
        progress["active_writer_locks"] = []
        (run_dir / "Progress.json").write_text(json.dumps(progress), encoding="utf-8")
        run = json.loads((run_dir / "Apply-Run.json").read_text(encoding="utf-8"))
        if run.get("mode") == "kimi_session_serial":
            APPLY_MODULE.prepare_dispatch_packet(
                run_dir,
                task_id,
                "implementer",
                "controller",
                ["prepared fresh implementer dispatch packet"],
            )
            APPLY_MODULE.record_agent_status(
                run_dir,
                task_id,
                "implementer",
                "impl-1",
                "spawned",
                "controller",
                ["implementer subagent spawned"],
            )
        APPLY_MODULE.transition_task_state(run_dir, task_id, "IMPLEMENTING", "impl-1", ["started implementation"])
        if run.get("mode") == "kimi_session_serial":
            APPLY_MODULE.record_agent_status(
                run_dir,
                task_id,
                "implementer",
                "impl-1",
                "completed",
                "controller",
                ["implementer subagent completed"],
                "implementation report ready",
            )
        APPLY_MODULE.transition_task_state(run_dir, task_id, "IMPLEMENTED", "impl-1", ["implementation report ready"])
        APPLY_MODULE.transition_task_state(run_dir, task_id, "TASK_REVIEW", "review-1", ["review package ready"])
        if security_verdict == "pass":
            APPLY_MODULE.transition_task_state(run_dir, task_id, "SECURITY_REVIEW", "review-1", ["security review required"])
            APPLY_MODULE.transition_task_state(run_dir, task_id, "VERIFIED", "review-1", ["security review passed"])
        else:
            APPLY_MODULE.transition_task_state(run_dir, task_id, "VERIFIED", "review-1", ["task review passed"])

        progress = json.loads((run_dir / "Progress.json").read_text(encoding="utf-8"))
        task = progress["tasks"][0]
        progress["verified_task_ids"] = [task_id]
        (run_dir / "Progress.json").write_text(json.dumps(progress), encoding="utf-8")
        brief_hash = task["brief_sha256"]
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
        patch_sha = APPLY_MODULE.sha256_bytes(patch.encode("utf-8"))
        (run_dir / task_id / "Review-Package.patch").write_text(patch, encoding="utf-8")
        validation_evidence = [
            {**command, "exit_code": 0, "output_sha256": VALIDATION_OUTPUT_SHA256}
            for command in task.get("validation_commands", [])
            if isinstance(command, dict)
        ]
        (run_dir / task_id / "Implementer-Report.json").write_text(
            json.dumps(
                {
                    "status": "DONE",
                    "task_id": task_id,
                    "brief_sha256": brief_hash,
                    "implementation_contract_digest": task.get("implementation_contract_digest"),
                    "task_contract_digest": task.get("task_contract_digest"),
                    "implementer_agent_id": "impl-1",
                    "files_changed": ["src/feature_1_1.py"],
                    "validation_evidence": validation_evidence,
                    "diff_sha256": patch_sha,
                }
            ),
            encoding="utf-8",
        )
        task_review = {
            "task_id": task_id,
            "brief_sha256": brief_hash,
            "implementation_contract_digest": task.get("implementation_contract_digest"),
            "task_contract_digest": task.get("task_contract_digest"),
            "reviewer_agent_id": "review-1",
            "spec_compliance": "pass",
            "task_quality": "approved",
            "security_review": security_verdict,
            "evidence": ["reviewed diff and validation evidence"],
        }
        if security_verdict == "pass":
            task_review["security_reviewer_agent_id"] = "security-review-1"
        (run_dir / task_id / "Task-Review.json").write_text(json.dumps(task_review), encoding="utf-8")
        (run_dir / "Final-Review.json").write_text(
            json.dumps(
                {
                    "status": "pass",
                    "reviewed_task_ids": [task_id],
                    "global_validations": [{"id": "VAL-REPO", "argv": ["make", "check"], "exit_code": 0}],
                    "evidence": ["repo gate passed"],
                }
            ),
            encoding="utf-8",
        )

    def test_init_kimi_session_serial_creates_safe_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)

            result = self.create_apply_run(root, "kimi_session_serial")
            run_dir = Path(result["run_dir"])

            self.assertTrue((run_dir / "Apply-Run.json").is_file())
            self.assertTrue((run_dir / "Progress.json").is_file())
            self.assertTrue((run_dir / "Final-Review.json").is_file())
            self.assertTrue((run_dir / "Result.json").is_file())
            task_id = self.first_task_id(run_dir)
            self.assertRegex(task_id, r"^AR-apply-kimi_session_serial-[A-Za-z0-9_.-]+-T001$")
            self.assertTrue((run_dir / task_id / "Brief.md").is_file())
            self.assertTrue((run_dir / task_id / "Implementer-Report.json").is_file())
            self.assertTrue((run_dir / task_id / "Review-Package.patch").is_file())
            self.assertTrue((run_dir / task_id / "Task-Review.json").is_file())
            self.assertTrue((run_dir / task_id / "Fix-Report.json").is_file())
            run = json.loads((run_dir / "Apply-Run.json").read_text(encoding="utf-8"))
            self.assertEqual(run["apply_run_schema_version"], 1)
            self.assertEqual(run["mode"], "kimi_session_serial")
            self.assertIn("apply_policy_digest", run)
            self.assertEqual(run["commit_policy"], "none")
            self.assertFalse(run["push_allowed"])
            self.assertFalse(run["pr_allowed"])
            self.assertEqual(run["max_writer_agents"], 1)
            self.assertEqual(run["max_subagent_depth"], 1)
            self.assertEqual(run["budget_contract"]["max_selected_tasks"], 4)
            self.assertEqual(run["budget_contract"]["max_agent_attempts_per_role"], 2)
            self.assertEqual(run["budget_contract"]["max_fix_cycles"], 2)
            self.assertEqual(run["token_usage"]["status"], "not_observed")
            self.assertEqual(run["workspace_mode"], "non_git_unsafe")
            self.assertTrue(run["user_approval"])
            self.assertEqual(run["worktree_path"], ".")
            self.assertEqual(run["working_branch"], "unknown")
            self.assertEqual(run["dirty_state"], "non_git")
            self.assertEqual(run["workspace_baseline"]["vcs"], "non_git")
            self.assertIn("git_status_porcelain_sha256", run["workspace_baseline"])
            self.assertIn("untracked_inventory_sha256", run["workspace_baseline"])
            self.assertIn("workspace_file_inventory_sha256", run["workspace_baseline"])
            self.assertEqual(run["agent_profiles"]["implementer"]["model_profile"], "balanced")
            self.assertEqual(run["agent_profiles"]["task_reviewer"]["sandbox"], "read-only")
            self.assertEqual(run["agent_profiles"]["security_reviewer"]["model_profile"], "security_strong")
            self.assertFalse(run["safety"]["executes_implementation"])
            self.assertFalse(run["safety"]["allows_commit_push_pr_deploy"])
            progress = json.loads((run_dir / "Progress.json").read_text(encoding="utf-8"))
            self.assertEqual(
                progress["tasks"][0]["source_subplan_path"],
                "Planner-docs/Faz-1-Plans/Faz1.1-local-contract.md",
            )
            contract = progress["tasks"][0]["fresh_context_contract"]
            self.assertTrue(any("behavioral acceptance" in item for item in contract["acceptance_criteria"]))
            self.assertTrue(any("allowed write paths" in item for item in contract["allowed_paths"]))
            self.assertTrue(any("validation command argv" in item for item in contract["structured_validation_commands"]))
            self.assertTrue(progress["tasks"][0]["security_review_required"])
            self.assertEqual(progress["tasks"][0]["finding_ids"], [])
            self.assertEqual(progress["tasks"][0]["dependency_state"], "independent")
            implementation_contract = progress["tasks"][0]["implementation_contract"]
            self.assertEqual(implementation_contract["contract_version"], 1)
            self.assertEqual(implementation_contract["parent_signals"], ["MP-PH1-AS-01"])
            self.assertEqual(implementation_contract["outputs"], ["reports/faz1-1-readiness.md"])
            self.assertEqual(
                implementation_contract["dependencies"]["activation_conditions"],
                ["local fixture files exist"],
            )
            self.assertEqual(implementation_contract["implementation_paths"][0]["path"], "src/feature_1_1.py")
            self.assertEqual(progress["tasks"][0]["validation_commands"][0]["id"], "VAL-01")
            self.assertEqual(
                progress["tasks"][0]["validation_commands"][0]["argv"],
                ["python3", "-m", "pytest", "tests/test_feature_1_1.py", "-q"],
            )
            self.assertEqual(progress["tasks"][0]["validation_command_ids"], ["VAL-01"])
            brief = (run_dir / task_id / "Brief.md").read_text(encoding="utf-8")
            self.assertIn("Planner-docs/Faz-1-Plans/Faz1.1-local-contract.md", brief)
            self.assertIn("fresh_context_contract", brief)
            self.assertIn("implementation_contract", brief)
            self.assertIn('"outputs":["reports/faz1-1-readiness.md"]', brief)
            self.assertIn("security_review_required: true", brief)
            self.assertIn("validation_command_ids: VAL-01", brief)
            self.assertIn('"id":"VAL-01"', brief)
            self.assertEqual(APPLY_MODULE.validate_apply_run(run_dir), [])

    def test_apply_rejects_policy_envelope_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            result = self.create_apply_run(root, "direct")
            run_dir = Path(result["run_dir"])
            run_path = run_dir / "Apply-Run.json"
            run = json.loads(run_path.read_text(encoding="utf-8"))
            run["workspace_verified"] = True
            run["worktree_path"] = "../../outside"
            run["step4_readiness"]["validator_status"] = "failed"
            run["step4_readiness"]["validator_output_sha256"] = "0" * 64
            run["safety"]["allows_commit_push_pr_deploy"] = True
            run["budget_contract"]["max_selected_tasks"] = 3
            run["apply_policy_digest"] = APPLY_MODULE.canonical_json_digest(
                {
                    "workspace_verified": run["workspace_verified"],
                    "worktree_path": run["worktree_path"],
                    "step4_readiness": run["step4_readiness"],
                    "safety": run["safety"],
                    "budget_contract": run["budget_contract"],
                }
            )
            run_path.write_text(json.dumps(run), encoding="utf-8")

            errors = APPLY_MODULE.validate_apply_run(run_dir, root)

            self.assertIn("apply_policy_digest_mismatch", errors)
            self.assertIn("apply_policy_mismatch=workspace_verified", errors)
            self.assertIn("apply_policy_mismatch=worktree_path", errors)
            self.assertIn("apply_policy_mismatch=step4_readiness", errors)
            self.assertIn("apply_policy_mismatch=safety", errors)
            self.assertIn("apply_policy_mismatch=budget_contract", errors)

    def test_apply_budget_rejects_invalid_limits_and_selected_task_overflow(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            result = self.create_apply_run(root, "direct")
            run_dir = Path(result["run_dir"])
            run_path = run_dir / "Apply-Run.json"
            run = json.loads(run_path.read_text(encoding="utf-8"))
            run["budget_contract"]["max_agent_attempts_per_role"] = -1
            run["budget_contract"]["hard_total_token_limit"] = 1
            run["budget_contract"]["soft_input_token_limit"] = 2
            run_path.write_text(json.dumps(run), encoding="utf-8")
            progress_path = run_dir / "Progress.json"
            progress = json.loads(progress_path.read_text(encoding="utf-8"))
            template = progress["tasks"][0]
            progress["tasks"] = [json.loads(json.dumps(template)) for _ in range(5)]
            for index, task in enumerate(progress["tasks"], start=1):
                task["task_id"] = f"{template['task_id'][:-3]}{index:03d}"
            progress_path.write_text(json.dumps(progress), encoding="utf-8")

            errors = APPLY_MODULE.validate_apply_run(run_dir, root)

            self.assertIn("invalid_budget_contract=max_agent_attempts_per_role", errors)
            self.assertIn("budget_contract_hard_below_soft", errors)
            self.assertIn("budget_selected_tasks_exceeded", errors)

    def test_subagent_attempt_budget_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            result = self.create_apply_run(root, "kimi_session_serial")
            run_dir = Path(result["run_dir"])
            task_id = self.first_task_id(run_dir)

            for attempt in range(1, 3):
                APPLY_MODULE.prepare_dispatch_packet(run_dir, task_id, "implementer", "controller", [f"packet {attempt}"])
                APPLY_MODULE.record_agent_status(
                    run_dir,
                    task_id,
                    "implementer",
                    f"agent-impl-{attempt}",
                    "spawned",
                    "controller",
                    [f"spawn {attempt}"],
                )
                APPLY_MODULE.record_agent_status(
                    run_dir,
                    task_id,
                    "implementer",
                    f"agent-impl-{attempt}",
                    "failed",
                    "controller",
                    [f"failure {attempt}"],
                    "recoverable setup failure",
                )

            with self.assertRaisesRegex(ValueError, f"budget_max_agent_attempts_exceeded={task_id}:implementer"):
                APPLY_MODULE.prepare_dispatch_packet(run_dir, task_id, "implementer", "controller", ["third packet"])

    def test_apply_validator_rejects_attempt_and_fix_cycle_over_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            result = self.create_apply_run(root, "direct")
            run_dir = Path(result["run_dir"])
            progress_path = run_dir / "Progress.json"
            progress = json.loads(progress_path.read_text(encoding="utf-8"))
            task = progress["tasks"][0]
            task_id = task["task_id"]
            task["fix_cycle_count"] = 3
            task["agent_runs"] = [
                {
                    "task_id": task_id,
                    "role": "implementer",
                    "attempt": 3,
                    "agent_id": "agent-impl-3",
                    "status": "failed",
                    "packet_sha256": "a" * 64,
                    "prompt_sha256": "b" * 64,
                    "spawn_tool": "kimi_session_dispatch_artifact",
                    "summary": "attempt exceeds budget",
                    "failed_at": "2026-01-01T00:00:00Z",
                }
            ]
            progress_path.write_text(json.dumps(progress), encoding="utf-8")
            (run_dir / task_id / "Fix-Report.json").write_text(
                json.dumps({"fixes": [{"finding": "a"}, {"finding": "b"}, {"finding": "c"}]}),
                encoding="utf-8",
            )

            errors = APPLY_MODULE.validate_apply_run(run_dir, root)

            self.assertIn(f"budget_max_fix_cycles_exceeded={task_id}", errors)
            self.assertIn(f"budget_max_agent_attempts_exceeded={task_id}:implementer", errors)

    def test_apply_unknown_runtime_token_usage_is_reported_honestly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            result = self.create_apply_run(root, "direct")
            run_dir = Path(result["run_dir"])
            run = json.loads((run_dir / "Apply-Run.json").read_text(encoding="utf-8"))
            result_payload = json.loads((run_dir / "Result.json").read_text(encoding="utf-8"))

            self.assertEqual(run["token_usage"]["total_tokens"], "not_observed")
            self.assertEqual(result_payload["token_usage"]["source"], "runtime_not_available")
            run["token_usage"] = {"status": "observed", "input_tokens": 10, "output_tokens": 5, "total_tokens": 99, "source": "test"}
            (run_dir / "Apply-Run.json").write_text(json.dumps(run), encoding="utf-8")
            errors = APPLY_MODULE.validate_apply_run(run_dir, root)

            self.assertIn("token_usage_total_mismatch", errors)

    def test_apply_task_contract_is_bound_to_source_subplan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            result = self.create_apply_run(root, "direct")
            run_dir = Path(result["run_dir"])
            progress = json.loads((run_dir / "Progress.json").read_text(encoding="utf-8"))
            task = progress["tasks"][0]

            self.assertEqual(task["source_subplan_path"], "Planner-docs/Faz-1-Plans/Faz1.1-local-contract.md")
            self.assertTrue(task["source_subplan_sha256"])
            self.assertTrue(task["implementation_contract_digest"])
            self.assertTrue(task["task_contract_digest"])
            self.assertEqual(task["parent_acceptance_signal_ids"], ["MP-PH1-AS-01"])
            self.assertEqual(task["risk_class"], "low")
            self.assertEqual(task["risk_domains"], ["none"])
            self.assertEqual(APPLY_MODULE.validate_apply_run(run_dir, root), [])

    def test_apply_rejects_task_contract_divergent_from_source_subplan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            result = self.create_apply_run(root, "direct")
            run_dir = Path(result["run_dir"])
            progress_path = run_dir / "Progress.json"
            progress = json.loads(progress_path.read_text(encoding="utf-8"))
            task = progress["tasks"][0]
            task["implementation_contract"]["outputs"] = ["reports/tampered.md"]
            task["implementation_contract_digest"] = APPLY_MODULE.canonical_json_digest(task["implementation_contract"])
            task["task_contract_digest"] = APPLY_MODULE.task_contract_digest(task)
            progress_path.write_text(json.dumps(progress), encoding="utf-8")

            errors = APPLY_MODULE.validate_apply_run(run_dir, root)

            self.assertIn(f"implementation_contract_source_mismatch={task['task_id']}", errors)
            self.assertIn(f"implementation_contract_digest_source_mismatch={task['task_id']}", errors)

    def test_apply_rejects_source_subplan_hash_and_path_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            result = self.create_apply_run(root, "direct")
            run_dir = Path(result["run_dir"])
            progress_path = run_dir / "Progress.json"
            progress = json.loads(progress_path.read_text(encoding="utf-8"))
            task = progress["tasks"][0]
            task["source_subplan_sha256"] = "0" * 64
            task["source_subplan_path"] = "Planner-docs/Missing.md"
            task["task_contract_digest"] = APPLY_MODULE.task_contract_digest(task)
            progress_path.write_text(json.dumps(progress), encoding="utf-8")

            errors = APPLY_MODULE.validate_apply_run(run_dir, root)

            self.assertIn("missing_source_subplan=Planner-docs/Missing.md", errors)
            self.assertIn(f"source_subplan_sha256_mismatch={task['task_id']}", errors)

    def test_apply_rejects_validation_ids_divergent_from_source_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            result = self.create_apply_run(root, "direct")
            run_dir = Path(result["run_dir"])
            progress_path = run_dir / "Progress.json"
            progress = json.loads(progress_path.read_text(encoding="utf-8"))
            task = progress["tasks"][0]
            task["validation_command_ids"] = ["VAL-99"]
            task["task_contract_digest"] = APPLY_MODULE.task_contract_digest(task)
            progress_path.write_text(json.dumps(progress), encoding="utf-8")

            errors = APPLY_MODULE.validate_apply_run(run_dir, root)

            self.assertIn(f"validation_command_ids_source_mismatch={task['task_id']}", errors)
            self.assertIn(f"implementation_contract_validation_command_ids_mismatch={task['task_id']}", errors)

    def test_apply_brief_contract_hash_matches_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            result = self.create_apply_run(root, "direct")
            run_dir = Path(result["run_dir"])
            progress = json.loads((run_dir / "Progress.json").read_text(encoding="utf-8"))
            task = progress["tasks"][0]
            brief_path = run_dir / task["task_id"] / "Brief.md"
            brief_path.write_text(
                brief_path.read_text(encoding="utf-8").replace("reports/faz1-1-readiness.md", "reports/tampered.md"),
                encoding="utf-8",
            )

            errors = APPLY_MODULE.validate_apply_run(run_dir, root)

            self.assertIn(f"task_brief_hash_mismatch={task['task_id']}", errors)
            self.assertIn(f"task_brief_contract_mismatch={task['task_id']}", errors)

    def test_apply_dispatch_contract_hash_matches_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            result = self.create_apply_run(root, "kimi_session_serial")
            run_dir = Path(result["run_dir"])
            task_id = self.first_task_id(run_dir)
            APPLY_MODULE.prepare_dispatch_packet(run_dir, task_id, "implementer", "controller", ["packet ready"])
            packet_path = run_dir / task_id / "Dispatch-Packet.json"
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            packet["spawn_request"]["message"] = packet["spawn_request"]["message"].replace(
                "reports/faz1-1-readiness.md",
                "reports/tampered.md",
            )
            packet["prompt_sha256"] = APPLY_MODULE.sha256_bytes(packet["spawn_request"]["message"].encode("utf-8"))
            packet_path.write_text(json.dumps(packet, sort_keys=True), encoding="utf-8")
            progress_path = run_dir / "Progress.json"
            progress = json.loads(progress_path.read_text(encoding="utf-8"))
            progress["tasks"][0]["dispatch"]["packet_sha256"] = APPLY_MODULE.sha256_bytes(packet_path.read_bytes())
            progress_path.write_text(json.dumps(progress), encoding="utf-8")

            errors = APPLY_MODULE.validate_apply_run(run_dir, root)

            self.assertIn(f"dispatch_prompt_contract_mismatch={task_id}", errors)

    def test_apply_report_and_review_reference_expected_contract_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            result = self.create_apply_run(root, "direct")
            run_dir = Path(result["run_dir"])
            self.mark_task_verified(run_dir, "pass")
            task_id = self.first_task_id(run_dir)
            report_path = run_dir / task_id / "Implementer-Report.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            report["task_contract_digest"] = "0" * 64
            report_path.write_text(json.dumps(report), encoding="utf-8")
            review_path = run_dir / task_id / "Task-Review.json"
            review = json.loads(review_path.read_text(encoding="utf-8"))
            review["implementation_contract_digest"] = "1" * 64
            review_path.write_text(json.dumps(review), encoding="utf-8")

            errors = APPLY_MODULE.validate_apply_run(run_dir, root)

            self.assertIn(f"implementer_task_contract_digest_mismatch={task_id}", errors)
            self.assertIn(f"task_review_contract_digest_mismatch={task_id}", errors)

    def test_kimi_session_serial_requires_dispatch_packet_before_implementation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            result = self.create_apply_run(root, "kimi_session_serial")
            run_dir = Path(result["run_dir"])
            task_id = self.first_task_id(run_dir)

            with self.assertRaisesRegex(ValueError, "subagent_dispatch_packet_missing"):
                APPLY_MODULE.transition_task_state(run_dir, task_id, "IMPLEMENTING", "impl-1", ["started"])

            prepared = APPLY_MODULE.prepare_dispatch_packet(
                run_dir,
                task_id,
                "implementer",
                "controller",
                ["controller prepared fresh implementer dispatch"],
            )
            packet_path = Path(prepared["packet_path"])
            packet = json.loads(packet_path.read_text(encoding="utf-8"))

            self.assertEqual(packet["spawn_tool"], "kimi_session_dispatch_artifact")
            self.assertEqual(packet["spawn_request"]["agent_type"], "worker")
            self.assertFalse(packet["spawn_request"]["fork_context"])
            self.assertIn("Use only this fresh task context", packet["spawn_request"]["message"])
            self.assertIn("## Structured Implementation Contract", packet["spawn_request"]["message"])
            self.assertIn('"outputs": [', packet["spawn_request"]["message"])
            self.assertIsNone(packet["model_override"])
            with self.assertRaisesRegex(ValueError, "subagent_dispatch_spawn_required"):
                APPLY_MODULE.transition_task_state(run_dir, task_id, "IMPLEMENTING", "impl-1", ["started"])
            APPLY_MODULE.record_agent_status(
                run_dir,
                task_id,
                "implementer",
                "agent-impl-1",
                "spawned",
                "controller",
                ["spawned implementer"],
            )
            APPLY_MODULE.transition_task_state(run_dir, task_id, "IMPLEMENTING", "impl-1", ["started"])
            with self.assertRaisesRegex(ValueError, "subagent_dispatch_completion_required"):
                APPLY_MODULE.transition_task_state(run_dir, task_id, "IMPLEMENTED", "impl-1", ["done"])
            APPLY_MODULE.record_agent_status(
                run_dir,
                task_id,
                "implementer",
                "agent-impl-1",
                "completed",
                "controller",
                ["implementer completed"],
                "implementation finished",
            )
            APPLY_MODULE.transition_task_state(run_dir, task_id, "IMPLEMENTED", "impl-1", ["done"])
            self.assertEqual(APPLY_MODULE.validate_apply_run(run_dir), [])

    def test_failed_subagent_dispatch_can_be_redispatched_before_implementation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            result = self.create_apply_run(root, "kimi_session_serial")
            run_dir = Path(result["run_dir"])
            task_id = self.first_task_id(run_dir)

            APPLY_MODULE.prepare_dispatch_packet(run_dir, task_id, "implementer", "controller", ["first packet"])
            APPLY_MODULE.record_agent_status(
                run_dir,
                task_id,
                "implementer",
                "agent-impl-1",
                "spawned",
                "controller",
                ["first spawn"],
            )
            APPLY_MODULE.record_agent_status(
                run_dir,
                task_id,
                "implementer",
                "agent-impl-1",
                "failed",
                "controller",
                ["agent failed before code changes"],
                "spawn failed before implementation",
            )
            second = APPLY_MODULE.prepare_dispatch_packet(run_dir, task_id, "implementer", "controller", ["second packet"])
            packet = json.loads(Path(second["packet_path"]).read_text(encoding="utf-8"))
            APPLY_MODULE.record_agent_status(
                run_dir,
                task_id,
                "implementer",
                "agent-impl-2",
                "spawned",
                "controller",
                ["second spawn"],
            )

            progress = json.loads((run_dir / "Progress.json").read_text(encoding="utf-8"))
            task = progress["tasks"][0]

            self.assertEqual(packet["attempt"], 2)
            self.assertEqual([run["status"] for run in task["agent_runs"]], ["failed", "spawned"])
            self.assertEqual(task["dispatch"]["agent_id"], "agent-impl-2")
            self.assertEqual(APPLY_MODULE.validate_apply_run(run_dir), [])

    def test_no_action_mode_has_no_queue(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_no_action_fixture(root)
            result = self.create_apply_run(root, "no_action")
            run_dir = Path(result["run_dir"])
            progress = json.loads((run_dir / "Progress.json").read_text(encoding="utf-8"))
            run = json.loads((run_dir / "Apply-Run.json").read_text(encoding="utf-8"))
            self.assertEqual(progress["tasks"], [])
            self.assertEqual(run["mode"], "no_action")
            self.assertEqual(run["step4_readiness"]["execution_queue_state"], "NO_ACTION_REQUIRED")

    def test_apply_run_rejects_output_dir_outside_repo(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, tempfile.TemporaryDirectory() as outside:
            with self.assertRaises(ValueError):
                self.create_apply_run(Path(temp_dir), "direct", Path(outside))

    def test_apply_run_requires_step4_audit_for_action_modes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "missing_step4_audit"):
                self.create_apply_run(Path(temp_dir), "direct")

    def test_apply_run_blocks_non_git_action_without_explicit_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)

            with self.assertRaisesRegex(ValueError, "non_git_workspace_requires_explicit_approval"):
                APPLY_MODULE.create_apply_run(root, "direct")

            result = self.create_apply_run(root, "direct")
            run_dir = Path(result["run_dir"])
            run = json.loads((run_dir / "Apply-Run.json").read_text(encoding="utf-8"))
            self.assertEqual(run["workspace_mode"], "non_git_unsafe")
            self.assertTrue(run["user_approval"])
            run["user_approval"] = False
            (run_dir / "Apply-Run.json").write_text(json.dumps(run), encoding="utf-8")

            errors = APPLY_MODULE.validate_apply_run(run_dir, root)

            self.assertIn("non_git_workspace_requires_user_approval", errors)

    def test_apply_run_blocks_dirty_or_protected_git_without_explicit_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            self.init_git_repo(root)

            with self.assertRaisesRegex(ValueError, "git_workspace_requires_explicit_current_worktree_approval"):
                APPLY_MODULE.create_apply_run(root, "direct")

            result = self.create_apply_run(root, "direct")
            run_dir = Path(result["run_dir"])
            run = json.loads((run_dir / "Apply-Run.json").read_text(encoding="utf-8"))
            self.assertEqual(run["workspace_mode"], "unverified_current_worktree")
            self.assertTrue(run["user_approval"])
            self.assertEqual(run["worktree_path"], ".")
            self.assertIn(run["dirty_state"], {"clean", "dirty"})
            self.assertEqual(run["working_branch"], run["workspace_baseline"]["branch"])
            run["user_approval"] = False
            (run_dir / "Apply-Run.json").write_text(json.dumps(run), encoding="utf-8")

            errors = APPLY_MODULE.validate_apply_run(run_dir, root)

            self.assertIn("git_workspace_requires_user_approval", errors)

    def test_apply_run_rejects_unsafe_queue_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            result = self.create_apply_run(root, "direct")
            run_dir = Path(result["run_dir"])
            progress = json.loads((run_dir / "Progress.json").read_text(encoding="utf-8"))
            task_id = progress["tasks"][0]["task_id"]
            progress["tasks"][0]["validation_commands"] = [
                {"argv": ["sh", "-c", "touch /tmp/kimiqb-owned"]}
            ]
            (run_dir / "Progress.json").write_text(json.dumps(progress), encoding="utf-8")
            errors = APPLY_MODULE.validate_apply_run(run_dir)
            self.assertIn(f"unsafe_validation_command={task_id}", errors)

    def test_apply_run_rejects_agent_profile_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            result = self.create_apply_run(root, "direct")
            run_dir = Path(result["run_dir"])
            run = json.loads((run_dir / "Apply-Run.json").read_text(encoding="utf-8"))
            run["agent_profiles"]["task_reviewer"]["sandbox"] = "workspace-write"
            (run_dir / "Apply-Run.json").write_text(json.dumps(run), encoding="utf-8")

            errors = APPLY_MODULE.validate_apply_run(run_dir)

            self.assertIn("agent_profile_mismatch=task_reviewer:sandbox", errors)

    def test_transition_cli_appends_events_and_manages_writer_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            result = self.create_apply_run(root, "direct")
            run_dir = Path(result["run_dir"])

            code = APPLY_MODULE.main(
                [
                    "transition",
                    "--run-dir",
                    str(run_dir),
                    "--task-id",
                    self.first_task_id(run_dir),
                    "--to",
                    "IMPLEMENTING",
                    "--actor",
                    "impl-1",
                    "--evidence",
                    "brief accepted",
                ]
            )
            self.assertEqual(code, 0)
            self.assertTrue((run_dir / "Writer-Lock.json").is_file())
            progress = json.loads((run_dir / "Progress.json").read_text(encoding="utf-8"))
            task_id = progress["tasks"][0]["task_id"]
            self.assertEqual(progress["tasks"][0]["state"], "IMPLEMENTING")
            self.assertEqual(progress["active_writer_locks"][0]["task_id"], task_id)

            with self.assertRaisesRegex(ValueError, "invalid_transition=IMPLEMENTING->VERIFIED"):
                APPLY_MODULE.transition_task_state(run_dir, task_id, "VERIFIED", "impl-1", [])

            APPLY_MODULE.transition_task_state(run_dir, task_id, "IMPLEMENTED", "impl-1", ["implementation complete"])
            self.assertFalse((run_dir / "Writer-Lock.json").exists())
            events = [
                json.loads(line)
                for line in (run_dir / "Events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual([event["sequence"] for event in events], [1, 2, 3])
            self.assertEqual(events[-1]["from"], "IMPLEMENTING")
            self.assertEqual(events[-1]["to"], "IMPLEMENTED")
            self.assertEqual(APPLY_MODULE.validate_apply_run(run_dir), [])

    def test_validate_rejects_state_without_transition_event(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            result = self.create_apply_run(root, "direct")
            run_dir = Path(result["run_dir"])
            progress = json.loads((run_dir / "Progress.json").read_text(encoding="utf-8"))
            task_id = progress["tasks"][0]["task_id"]
            progress["tasks"][0]["state"] = "IMPLEMENTED"
            (run_dir / "Progress.json").write_text(json.dumps(progress), encoding="utf-8")

            errors = APPLY_MODULE.validate_apply_run(run_dir)

            self.assertIn(f"task_state_missing_transition_event={task_id}", errors)

    def test_validate_rejects_missing_writer_lock_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            result = self.create_apply_run(root, "direct")
            run_dir = Path(result["run_dir"])
            task_id = self.first_task_id(run_dir)
            APPLY_MODULE.transition_task_state(run_dir, task_id, "IMPLEMENTING", "impl-1", ["started"])
            (run_dir / "Writer-Lock.json").unlink()

            errors = APPLY_MODULE.validate_apply_run(run_dir)

            self.assertIn("active_writer_lock_missing_file", errors)

    def test_recover_stale_writer_lock_moves_task_to_needs_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            result = self.create_apply_run(root, "direct")
            run_dir = Path(result["run_dir"])
            task_id = self.first_task_id(run_dir)
            APPLY_MODULE.transition_task_state(run_dir, task_id, "IMPLEMENTING", "impl-1", ["started"])

            lock_path = run_dir / "Writer-Lock.json"
            stale_lock = json.loads(lock_path.read_text(encoding="utf-8"))
            stale_lock["acquired_at"] = "2000-01-01T00:00:00Z"
            lock_path.write_text(json.dumps(stale_lock), encoding="utf-8")
            progress = json.loads((run_dir / "Progress.json").read_text(encoding="utf-8"))
            progress["active_writer_locks"] = [stale_lock]
            progress["tasks"][0]["writer_lock"] = stale_lock
            (run_dir / "Progress.json").write_text(json.dumps(progress), encoding="utf-8")

            self.assertIn(f"writer_lock_expired={task_id}", APPLY_MODULE.validate_apply_run(run_dir))
            event = APPLY_MODULE.recover_stale_writer_lock(
                run_dir,
                task_id,
                "NEEDS_CONTEXT",
                "controller",
                ["implementation worker abandoned stale lock"],
            )
            progress = json.loads((run_dir / "Progress.json").read_text(encoding="utf-8"))

            self.assertEqual(event["recovery"], "stale_writer_lock")
            self.assertEqual(event["from"], "IMPLEMENTING")
            self.assertEqual(event["to"], "NEEDS_CONTEXT")
            self.assertFalse(lock_path.exists())
            self.assertEqual(progress["tasks"][0]["state"], "NEEDS_CONTEXT")
            self.assertEqual(APPLY_MODULE.validate_apply_run(run_dir), [])

    def test_apply_run_enforces_review_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            result = self.create_apply_run(root, "direct")
            run_dir = Path(result["run_dir"])
            progress = json.loads((run_dir / "Progress.json").read_text(encoding="utf-8"))
            task_id = progress["tasks"][0]["task_id"]
            progress["tasks"][0]["state"] = "TASK_REVIEW"
            (run_dir / "Progress.json").write_text(json.dumps(progress), encoding="utf-8")
            review = {
                "spec_compliance": "fail",
                "task_quality": "needs_fixes",
                "blocking_findings": ["missing acceptance behavior"],
                "re_review_required": True,
            }
            (run_dir / task_id / "Task-Review.json").write_text(json.dumps(review), encoding="utf-8")
            errors = APPLY_MODULE.validate_apply_run(run_dir)
            self.assertIn(f"re_review_requires_fix_report={task_id}", errors)

    def test_apply_run_rejects_non_ready_p0_p1_and_policy_violations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            result = self.create_apply_run(root, "kimi_session_serial")
            run_dir = Path(result["run_dir"])
            run = json.loads((run_dir / "Apply-Run.json").read_text(encoding="utf-8"))
            run["max_writer_agents"] = 2
            run["max_subagent_depth"] = 2
            (run_dir / "Apply-Run.json").write_text(json.dumps(run), encoding="utf-8")
            progress = json.loads((run_dir / "Progress.json").read_text(encoding="utf-8"))
            progress["tasks"][0]["readiness_status"] = "BLOCKED"
            progress["tasks"][0]["finding_ids"] = ["P1"]
            (run_dir / "Progress.json").write_text(json.dumps(progress), encoding="utf-8")
            task_id = progress["tasks"][0]["task_id"]

            errors = APPLY_MODULE.validate_apply_run(run_dir)

            self.assertIn("only_one_writer_permitted", errors)
            self.assertIn("recursive_subagents_rejected", errors)
            self.assertIn(f"non_ready_queue_item={task_id}:BLOCKED", errors)
            self.assertIn(f"p0_p1_queue_item_rejected={task_id}", errors)

    def test_apply_run_requires_security_review_and_final_review_for_verified_task(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            result = self.create_apply_run(root, "kimi_session_serial")
            run_dir = Path(result["run_dir"])
            progress = json.loads((run_dir / "Progress.json").read_text(encoding="utf-8"))
            progress["tasks"][0]["state"] = "VERIFIED"
            progress["tasks"][0]["security_review_required"] = True
            (run_dir / "Progress.json").write_text(json.dumps(progress), encoding="utf-8")
            task_id = progress["tasks"][0]["task_id"]
            (run_dir / task_id / "Implementer-Report.json").write_text(
                json.dumps({"status": "DONE", "implementer_agent_id": "impl-1"}),
                encoding="utf-8",
            )
            (run_dir / task_id / "Task-Review.json").write_text(
                json.dumps({"spec_compliance": "pass", "task_quality": "approved", "security_review": "not_required"}),
                encoding="utf-8",
            )

            errors = APPLY_MODULE.validate_apply_run(run_dir)

            self.assertIn(f"required_security_review_must_pass={task_id}", errors)
            self.assertIn(f"security_review_requires_security_reviewer_agent_id={task_id}", errors)
            self.assertIn("final_review_required", errors)

            review_path = run_dir / task_id / "Task-Review.json"
            review = json.loads(review_path.read_text(encoding="utf-8"))
            review["security_review"] = "pass"
            review_path.write_text(json.dumps(review), encoding="utf-8")
            errors = APPLY_MODULE.validate_apply_run(run_dir)
            self.assertIn(f"security_review_requires_security_reviewer_agent_id={task_id}", errors)

            review["security_reviewer_agent_id"] = "impl-1"
            review_path.write_text(json.dumps(review), encoding="utf-8")
            errors = APPLY_MODULE.validate_apply_run(run_dir)
            self.assertIn(f"security_reviewer_must_be_independent={task_id}", errors)

            self.mark_task_verified(run_dir, security="pass")
            self.assertEqual(APPLY_MODULE.validate_apply_run(run_dir), [])

    def test_finalize_requires_validated_complete_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            result = self.create_apply_run(root, "direct")
            run_dir = Path(result["run_dir"])

            with self.assertRaisesRegex(ValueError, "finalize_requires_all_tasks_verified"):
                APPLY_MODULE.finalize_apply_run(run_dir, "controller", ["attempted early finalize"])

            self.mark_task_verified(run_dir)
            event = APPLY_MODULE.finalize_apply_run(run_dir, "controller", ["all checks passed"])
            result_payload = json.loads((run_dir / "Result.json").read_text(encoding="utf-8"))

            self.assertEqual(event["event_type"], "apply_run_finalized")
            self.assertEqual(result_payload["status"], "complete")
            self.assertEqual(result_payload["completed_tasks"], [self.first_task_id(run_dir)])
            self.assertEqual(APPLY_MODULE.validate_apply_run(run_dir), [])

    def test_apply_run_snapshot_mismatch_blocks_resume(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            docs = root / "Planner-docs"
            result = self.create_apply_run(root, "direct")
            run_dir = Path(result["run_dir"])
            (docs / "Sub-Planing-Audit.md").write_text("changed\n", encoding="utf-8")

            errors = APPLY_MODULE.validate_apply_run(run_dir, root)

            self.assertIn("source_snapshot_mismatch", errors)

    def test_apply_validation_requires_root_for_source_binding_when_not_inferred(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, tempfile.TemporaryDirectory() as outside_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            result = self.create_apply_run(root, "direct")
            run_dir = Path(result["run_dir"])
            copied = Path(outside_dir) / "copied-apply-run"
            shutil.copytree(run_dir, copied)

            self.assertIn("source_binding_root_required", APPLY_MODULE.validate_apply_run(copied))
            self.assertEqual(APPLY_MODULE.validate_apply_run(copied, root), [])

    def test_apply_run_workspace_baseline_detects_non_git_source_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            (root / "src").mkdir()
            (root / "src" / "example.py").write_text("print('before')\n", encoding="utf-8")
            result = self.create_apply_run(root, "direct")
            run_dir = Path(result["run_dir"])
            (root / "src" / "example.py").write_text("print('after')\n", encoding="utf-8")

            errors = APPLY_MODULE.validate_apply_run(run_dir, root)

            self.assertIn("workspace_baseline_mismatch=workspace_file_inventory_sha256", errors)

    def test_step4_ledger_update_does_not_break_apply_resume(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            docs = root / "Planner-docs"
            write_ledger(docs)
            result = self.create_apply_run(root, "direct")
            run_dir = Path(result["run_dir"])
            ledger = docs / "Planing-Ledger.md"
            ledger.write_text(ledger.read_text(encoding="utf-8") + "\nStep 4 expected ledger update.\n", encoding="utf-8")

            self.assertEqual(APPLY_MODULE.validate_apply_run(run_dir, root), [])

    def test_apply_run_workspace_baseline_detects_git_untracked_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            self.init_git_repo(root)
            result = self.create_apply_run(root, "direct")
            run_dir = Path(result["run_dir"])
            self.assertEqual(APPLY_MODULE.validate_apply_run(run_dir, root), [])
            (root / "notes.txt").write_text("new local note\n", encoding="utf-8")

            errors = APPLY_MODULE.validate_apply_run(run_dir, root)

            self.assertIn("workspace_baseline_mismatch=git_status_porcelain_sha256", errors)
            self.assertIn("workspace_baseline_mismatch=untracked_inventory_sha256", errors)

    def test_apply_run_allows_contract_bound_tracked_implementation_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "feature_1_1.py").write_text("VALUE = 'before'\n", encoding="utf-8")
            (root / "src" / "outside.py").write_text("VALUE = 'outside-before'\n", encoding="utf-8")
            (root / "tests" / "test_feature_1_1.py").write_text(
                "import unittest\n\nclass FeatureTests(unittest.TestCase):\n    def test_placeholder(self):\n        self.assertTrue(True)\n",
                encoding="utf-8",
            )
            self.init_git_repo(root)
            subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True, text=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=KimiQB Test",
                    "-c",
                    "user.email=kimiqb-test@example.invalid",
                    "commit",
                    "-m",
                    "fixture",
                ],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )
            result = self.create_apply_run(root, "direct")
            run_dir = Path(result["run_dir"])
            task_id = self.first_task_id(run_dir)

            APPLY_MODULE.transition_task_state(run_dir, task_id, "IMPLEMENTING", "impl-1", ["started"])
            (root / "src" / "feature_1_1.py").write_text("VALUE = 'after'\n", encoding="utf-8")
            APPLY_MODULE.transition_task_state(run_dir, task_id, "IMPLEMENTED", "impl-1", ["implementation complete"])
            APPLY_MODULE.transition_task_state(run_dir, task_id, "TASK_REVIEW", "review-1", ["review ready"])
            APPLY_MODULE.transition_task_state(run_dir, task_id, "SECURITY_REVIEW", "security-1", ["security review"])
            APPLY_MODULE.transition_task_state(run_dir, task_id, "VERIFIED", "review-1", ["verified"])

            progress = json.loads((run_dir / "Progress.json").read_text(encoding="utf-8"))
            task = progress["tasks"][0]
            progress["verified_task_ids"] = [task_id]
            (run_dir / "Progress.json").write_text(json.dumps(progress), encoding="utf-8")
            brief_hash = task["brief_sha256"]
            patch = subprocess.run(
                ["git", "diff", "--binary", "--", "src/feature_1_1.py"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            (run_dir / task_id / "Review-Package.patch").write_text(patch, encoding="utf-8")
            (run_dir / task_id / "Implementer-Report.json").write_text(
                json.dumps(
                    {
                        "status": "DONE",
                        "task_id": task_id,
                        "brief_sha256": brief_hash,
                        "implementation_contract_digest": task.get("implementation_contract_digest"),
                        "task_contract_digest": task.get("task_contract_digest"),
                        "implementer_agent_id": "impl-1",
                        "files_changed": ["src/feature_1_1.py"],
                        "validation_evidence": [
                            {
                                "id": "VAL-01",
                                "argv": ["python3", "-m", "pytest", "tests/test_feature_1_1.py", "-q"],
                                "exit_code": 0,
                                "output_sha256": VALIDATION_OUTPUT_SHA256,
                            }
                        ],
                        "diff_sha256": APPLY_MODULE.sha256_bytes(patch.encode("utf-8")),
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / task_id / "Task-Review.json").write_text(
                json.dumps(
                    {
                        "task_id": task_id,
                        "brief_sha256": brief_hash,
                        "implementation_contract_digest": task.get("implementation_contract_digest"),
                        "task_contract_digest": task.get("task_contract_digest"),
                        "reviewer_agent_id": "review-1",
                        "security_reviewer_agent_id": "security-1",
                        "spec_compliance": "pass",
                        "task_quality": "approved",
                        "security_review": "pass",
                        "evidence": ["reviewed contract-bound implementation drift"],
                    }
                ),
                encoding="utf-8",
            )
            (root / "tests" / "test_feature_1_1.py").write_text(
                "import unittest\n\nclass FeatureTests(unittest.TestCase):\n    def test_placeholder(self):\n        self.assertTrue(True)\n\n    def test_fix_coverage(self):\n        self.assertTrue(True)\n",
                encoding="utf-8",
            )
            (run_dir / task_id / "Fix-Report.json").write_text(
                json.dumps(
                    {
                        "task_id": task_id,
                        "fixer_agent_id": "fixer-1",
                        "fixes": [
                            {
                                "finding": "missing coverage",
                                "files_changed": ["tests/test_feature_1_1.py"],
                                "validation": {
                                    "id": "VAL-01",
                                    "argv": ["python3", "-m", "pytest", "tests/test_feature_1_1.py", "-q"],
                                    "exit_code": 0,
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "Final-Review.json").write_text(
                json.dumps(
                    {
                        "status": "pass",
                        "reviewed_task_ids": [task_id],
                        "global_validations": [{"id": "VAL-REPO", "argv": ["make", "check"], "exit_code": 0}],
                        "evidence": ["final review passed"],
                    }
                ),
                encoding="utf-8",
            )

            (root / "src" / "__pycache__").mkdir()
            (root / "src" / "__pycache__" / "feature_1_1.cpython-314.pyc").write_bytes(b"cache")
            self.assertEqual(APPLY_MODULE.validate_apply_run(run_dir, root), [])

            (root / "src" / "outside.py").write_text("VALUE = 'outside-after'\n", encoding="utf-8")
            errors = APPLY_MODULE.validate_apply_run(run_dir, root)

            self.assertIn("workspace_baseline_mismatch=git_status_porcelain_sha256", errors)
            self.assertIn("source_snapshot_mismatch", errors)

    def test_apply_run_allows_contract_bound_proposed_untracked_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            self.init_git_repo(root)
            subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True, text=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=KimiQB Test",
                    "-c",
                    "user.email=kimiqb-test@example.invalid",
                    "commit",
                    "-m",
                    "fixture",
                ],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )
            result = self.create_apply_run(root, "direct")
            run_dir = Path(result["run_dir"])
            task_id = self.first_task_id(run_dir)

            APPLY_MODULE.transition_task_state(run_dir, task_id, "IMPLEMENTING", "impl-1", ["started"])
            (root / "src").mkdir()
            (root / "src" / "feature_1_1.py").write_text("VALUE = 'new'\n", encoding="utf-8")
            APPLY_MODULE.transition_task_state(run_dir, task_id, "IMPLEMENTED", "impl-1", ["implementation complete"])
            APPLY_MODULE.transition_task_state(run_dir, task_id, "TASK_REVIEW", "review-1", ["review ready"])
            APPLY_MODULE.transition_task_state(run_dir, task_id, "SECURITY_REVIEW", "security-1", ["security review"])
            APPLY_MODULE.transition_task_state(run_dir, task_id, "VERIFIED", "review-1", ["verified"])

            progress = json.loads((run_dir / "Progress.json").read_text(encoding="utf-8"))
            task = progress["tasks"][0]
            progress["verified_task_ids"] = [task_id]
            (run_dir / "Progress.json").write_text(json.dumps(progress), encoding="utf-8")
            patch = "\n".join(
                [
                    "diff --git a/src/feature_1_1.py b/src/feature_1_1.py",
                    "new file mode 100644",
                    "--- /dev/null",
                    "+++ b/src/feature_1_1.py",
                    "@@ -0,0 +1 @@",
                    "+VALUE = 'new'",
                    "",
                ]
            )
            (run_dir / task_id / "Review-Package.patch").write_text(patch, encoding="utf-8")
            brief_hash = task["brief_sha256"]
            (run_dir / task_id / "Implementer-Report.json").write_text(
                json.dumps(
                    {
                        "status": "DONE",
                        "task_id": task_id,
                        "brief_sha256": brief_hash,
                        "implementation_contract_digest": task.get("implementation_contract_digest"),
                        "task_contract_digest": task.get("task_contract_digest"),
                        "implementer_agent_id": "impl-1",
                        "files_changed": ["src/feature_1_1.py"],
                        "validation_evidence": [
                            {
                                "id": "VAL-01",
                                "argv": ["python3", "-m", "pytest", "tests/test_feature_1_1.py", "-q"],
                                "exit_code": 0,
                                "output_sha256": VALIDATION_OUTPUT_SHA256,
                            }
                        ],
                        "diff_sha256": APPLY_MODULE.sha256_bytes(patch.encode("utf-8")),
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / task_id / "Task-Review.json").write_text(
                json.dumps(
                    {
                        "task_id": task_id,
                        "brief_sha256": brief_hash,
                        "implementation_contract_digest": task.get("implementation_contract_digest"),
                        "task_contract_digest": task.get("task_contract_digest"),
                        "reviewer_agent_id": "review-1",
                        "security_reviewer_agent_id": "security-1",
                        "spec_compliance": "pass",
                        "task_quality": "approved",
                        "security_review": "pass",
                        "evidence": ["reviewed proposed new file patch"],
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "Final-Review.json").write_text(
                json.dumps(
                    {
                        "status": "pass",
                        "reviewed_task_ids": [task_id],
                        "global_validations": [{"id": "VAL-REPO", "argv": ["make", "check"], "exit_code": 0}],
                        "evidence": ["final review passed"],
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(APPLY_MODULE.validate_apply_run(run_dir, root), [])

            (root / "src" / "outside_new.py").write_text("VALUE = 'outside'\n", encoding="utf-8")
            errors = APPLY_MODULE.validate_apply_run(run_dir, root)

            self.assertIn("workspace_baseline_mismatch=untracked_inventory_sha256", errors)
            self.assertIn("source_snapshot_mismatch", errors)

    def test_apply_run_verified_task_is_not_redispatched(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            result = self.create_apply_run(root, "direct")
            run_dir = Path(result["run_dir"])
            progress = json.loads((run_dir / "Progress.json").read_text(encoding="utf-8"))
            progress["tasks"][0]["state"] = "VERIFIED"
            progress["tasks"][0]["redispatch_count"] = 1
            (run_dir / "Progress.json").write_text(json.dumps(progress), encoding="utf-8")
            task_id = progress["tasks"][0]["task_id"]

            errors = APPLY_MODULE.validate_apply_run(run_dir)

            self.assertIn(f"verified_task_not_redispatched={task_id}", errors)

    def test_external_adapter_unavailable_requires_safe_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            result = self.create_apply_run(root, "external_adapter")
            run_dir = Path(result["run_dir"])
            self.assertIn("external_adapter_readiness_not_checked", APPLY_MODULE.validate_apply_run(run_dir))
            run = json.loads((run_dir / "Apply-Run.json").read_text(encoding="utf-8"))
            run["external_adapter"]["availability"] = "unavailable"
            run["external_adapter"]["fallback_mode"] = "direct"
            (run_dir / "Apply-Run.json").write_text(json.dumps(run), encoding="utf-8")

            errors = APPLY_MODULE.validate_apply_run(run_dir)

            self.assertIn("external_adapter_unavailable_requires_kimi_session_serial_fallback", errors)
            self.assertIn("external_adapter_unavailable_must_reconcile_mode", errors)
            run["external_adapter"]["fallback_mode"] = "kimi_session_serial"
            (run_dir / "Apply-Run.json").write_text(json.dumps(run), encoding="utf-8")
            self.assertIn("external_adapter_unavailable_must_reconcile_mode", APPLY_MODULE.validate_apply_run(run_dir))
            reconciled = APPLY_MODULE.reconcile_external_adapter(run_dir)

            self.assertEqual(reconciled["state"], "reconciled")
            run = json.loads((run_dir / "Apply-Run.json").read_text(encoding="utf-8"))
            self.assertEqual(run["mode"], "kimi_session_serial")
            self.assertEqual(APPLY_MODULE.validate_apply_run(run_dir), [])

    def test_apply_run_rejects_task_id_traversal_and_no_action_queue(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_no_action_fixture(root)
            no_action = self.create_apply_run(root, "no_action")
            run_dir = Path(no_action["run_dir"])
            progress = json.loads((run_dir / "Progress.json").read_text(encoding="utf-8"))
            progress["tasks"] = [{"task_id": "../../outside-task", "state": "BRIEFED", "readiness_status": "READY"}]
            (run_dir / "Progress.json").write_text(json.dumps(progress), encoding="utf-8")

            errors = APPLY_MODULE.validate_apply_run(run_dir)

            self.assertIn("no_action_must_not_have_tasks", errors)
            self.assertIn("invalid_task_id=../../outside-task", errors)

    def test_apply_run_does_not_overwrite_existing_progress_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            first = self.create_apply_run(root, "direct", run_id_suffix="one")
            second = self.create_apply_run(root, "direct", run_id_suffix="two")
            first_run = json.loads((Path(first["run_dir"]) / "Apply-Run.json").read_text(encoding="utf-8"))
            second_run = json.loads((Path(second["run_dir"]) / "Apply-Run.json").read_text(encoding="utf-8"))

            self.assertEqual(first_run["apply_spec_inputs"]["workspace_baseline"], first_run["workspace_baseline"])
            self.assertEqual(first_run["apply_spec_id"], second_run["apply_spec_id"])
            self.assertNotEqual(first["apply_run_id"], second["apply_run_id"])

            fixed = root / ".kimiqb" / "apply-runs" / "fixed"
            fixed_result = self.create_apply_run(root, "direct", fixed)
            with self.assertRaises(ValueError):
                self.create_apply_run(root, "direct", fixed)

            resumed = self.create_apply_run(root, "direct", fixed, resume=True)
            self.assertEqual(resumed["run_dir"], fixed_result["run_dir"])

    def test_apply_spec_digest_includes_workspace_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            result = self.create_apply_run(root, "direct")
            run_dir = Path(result["run_dir"])
            run_path = run_dir / "Apply-Run.json"
            run = json.loads(run_path.read_text(encoding="utf-8"))
            run["apply_spec_inputs"]["workspace_baseline"]["untracked_count"] = 999
            run_path.write_text(json.dumps(run), encoding="utf-8")

            errors = APPLY_MODULE.validate_apply_run(run_dir)

            self.assertIn("stored_apply_spec_digest_mismatch", errors)
            self.assertIn("stored_apply_spec_id_mismatch", errors)
            self.assertIn("stored_apply_run_id_mismatch", errors)
            self.assertIn("apply_spec_workspace_baseline_mismatch=untracked_count", errors)

    def test_verified_task_requires_evidence_bearing_reports(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            result = self.create_apply_run(root, "direct")
            run_dir = Path(result["run_dir"])
            progress = json.loads((run_dir / "Progress.json").read_text(encoding="utf-8"))
            progress["tasks"][0]["state"] = "VERIFIED"
            (run_dir / "Progress.json").write_text(json.dumps(progress), encoding="utf-8")
            task_id = progress["tasks"][0]["task_id"]
            (run_dir / task_id / "Implementer-Report.json").write_text(json.dumps({"status": "DONE"}), encoding="utf-8")
            (run_dir / task_id / "Task-Review.json").write_text(
                json.dumps({"spec_compliance": "pass", "task_quality": "approved", "security_review": "not_required"}),
                encoding="utf-8",
            )
            (run_dir / "Final-Review.json").write_text(json.dumps({"status": "pass"}), encoding="utf-8")

            errors = APPLY_MODULE.validate_apply_run(run_dir)

            self.assertIn(f"verified_requires_files_changed={task_id}", errors)
            self.assertIn(f"verified_requires_validation_evidence={task_id}", errors)
            self.assertIn(f"verified_requires_review_evidence={task_id}", errors)

    def test_verified_task_rejects_inconsistent_patch_and_validation_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            result = self.create_apply_run(root, "direct")
            run_dir = Path(result["run_dir"])
            self.mark_task_verified(run_dir)
            task_id = self.first_task_id(run_dir)
            report_path = run_dir / task_id / "Implementer-Report.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            report["files_changed"] = ["src/unapproved.py"]
            report["validation_evidence"] = [{"id": "VAL-99", "argv": ["python3", "-m", "pytest", "tests/other.py"], "exit_code": 0}]
            report["diff_sha256"] = "0" * 64
            report_path.write_text(json.dumps(report), encoding="utf-8")
            (run_dir / task_id / "Review-Package.patch").write_text(
                "diff --git a/src/feature_1_1.py b/src/feature_1_1.py\n--- a/src/feature_1_1.py\n+++ b/src/feature_1_1.py\n@@ -0,0 +1 @@\n+VALUE = 1\n",
                encoding="utf-8",
            )

            errors = APPLY_MODULE.validate_apply_run(run_dir, root)

            self.assertIn(f"verified_diff_hash_mismatch={task_id}", errors)
            self.assertIn(f"verified_files_changed_not_contract_bound={task_id}:src/unapproved.py", errors)
            self.assertIn(f"verified_patch_files_mismatch={task_id}", errors)
            self.assertIn(f"verified_validation_evidence_not_planned={task_id}:VAL-99", errors)
            self.assertIn(f"verified_validation_evidence_requires_output_hash={task_id}:VAL-99", errors)

    def test_apply_prepare_requires_passing_step4_validator(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_apply_fixture(root)
            (root / "Planner-docs" / "Sub-Planing-Audit.md").write_text("# broken audit\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "step4_validator_failed="):
                self.create_apply_run(root, "direct")


if __name__ == "__main__":
    unittest.main()
