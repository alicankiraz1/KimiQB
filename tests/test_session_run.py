from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_validate_planner_docs import write_audit, write_ledger, write_main_plan_with_phases, write_valid_step2_fixture


REPO_ROOT = Path(__file__).resolve().parents[1]
SESSION_RUN = REPO_ROOT / "skills/kimiqb/scripts/session_run.py"


def load_session_module():
    spec = importlib.util.spec_from_file_location("kimiqb_session_run", SESSION_RUN)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load session_run from {SESSION_RUN}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


SESSION_MODULE = load_session_module()


class SessionRunTests(unittest.TestCase):
    def write_session_fixture(self, root: Path) -> None:
        docs = write_valid_step2_fixture(root)
        write_audit(docs, "PASS")

    def init_git_repo(self, root: Path) -> None:
        subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)

    def rewrite_session_identity(self, run: dict[str, object]) -> None:
        stage = str(run["stage"])
        digest = SESSION_MODULE.session_spec_digest(
            stage,
            run["source_snapshot"],
            run["mode"],
            run["objective"],
            run["active_scope"],
        )
        run["session_spec_digest"] = digest
        run["session_spec_id"] = f"spec-{stage}-{digest[:16]}"
        run["session_run_id"] = f"session-{stage}-{digest[:12]}-{run['session_run_invocation_id']}"
        run["session_policy_digest"] = SESSION_MODULE.session_policy_digest(
            stage,
            run["source_snapshot"],
            run["mode"],
            run["active_scope"],
        )

    def test_compile_session_writes_stable_spec_and_unique_run_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_session_fixture(root)

            first = SESSION_MODULE.compile_session(root, "step2", run_id_suffix="one")
            second = SESSION_MODULE.compile_session(root, "step2", run_id_suffix="two")

            self.assertEqual(first["run"]["session_spec_id"], second["run"]["session_spec_id"])
            self.assertEqual(first["run"]["session_spec_digest"], second["run"]["session_spec_digest"])
            self.assertNotEqual(first["result"]["session_run_id"], second["result"]["session_run_id"])
            out_dir = Path(first["output_dir"])
            self.assertIn("Planner-docs/Session-Runs", out_dir.as_posix())
            self.assertTrue((out_dir / "Session-Run.json").is_file())
            self.assertTrue((out_dir / "Session-Prompt.md").is_file())
            self.assertTrue((out_dir / "Session-Result.json").is_file())

            run = json.loads((out_dir / "Session-Run.json").read_text(encoding="utf-8"))
            result = json.loads((out_dir / "Session-Result.json").read_text(encoding="utf-8"))
            prompt = (out_dir / "Session-Prompt.md").read_text(encoding="utf-8")
            self.assertEqual(run["session_run_schema_version"], 1)
            self.assertEqual(run["artifact_schema_version"], 3)
            self.assertEqual(run["handoff_contract_version"], 2)
            self.assertEqual(run["stage"], "step2")
            self.assertIn("source_snapshot_digest", run)
            self.assertIn("session_spec_digest", run)
            self.assertIn("session_policy_digest", run)
            self.assertIn("template_bundle_digest", run)
            self.assertIn("compiler", run)
            self.assertEqual(run["compiler"]["version"], 1)
            self.assertEqual(run["session_run_invocation_id"], "one")
            self.assertIn("required_inputs", run)
            self.assertIn("allowed_writes", run)
            self.assertIn("forbidden_writes", run)
            self.assertIn("validation_checkpoints", run)
            self.assertIn("stop_gates", run)
            self.assertEqual(run["budget_contract"]["max_selected_tasks"], 4)
            self.assertEqual(run["budget_contract"]["max_agent_attempts_per_role"], 2)
            self.assertEqual(run["token_usage"]["status"], "not_observed")
            self.assertEqual(result["budget_contract"], run["budget_contract"])
            self.assertEqual(result["token_usage"], run["token_usage"])
            self.assertEqual(run["active_scope"]["project_root"], ".")
            self.assertFalse(run["safety"]["executes_commands"])
            self.assertFalse(run["safety"]["allows_commit_push_pr_deploy"])
            self.assertEqual(result["status"], "ready")
            self.assertEqual(result["session_run_sha256"], SESSION_MODULE.sha256_bytes((out_dir / "Session-Run.json").read_bytes()))
            self.assertIn("Canonical Handoff", prompt)
            self.assertIn("Session Compiler Safety", prompt)
            self.assertEqual(prompt, SESSION_MODULE.render_prompt_from_run(run))
            self.assertEqual(SESSION_MODULE.validate_session_run(root, run), [])

    def test_session_rejects_policy_envelope_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_session_fixture(root)
            compiled = SESSION_MODULE.compile_session(root, "step4", run_id_suffix="policy")
            run = json.loads((Path(compiled["output_dir"]) / "Session-Run.json").read_text(encoding="utf-8"))
            run["allowed_writes"].append("src/unapproved.py")
            run["required_inputs"] = []
            if "--strict" in run["validation_checkpoints"][0]["argv"]:
                run["validation_checkpoints"][0]["argv"].remove("--strict")
            run["stop_gates"] = []
            run["user_confirmation_required"] = False
            run["safety"]["allows_commit_push_pr_deploy"] = True
            run["budget_contract"]["max_selected_tasks"] = 3
            run["session_policy_digest"] = SESSION_MODULE.canonical_json_digest(
                {
                    "allowed_writes": run["allowed_writes"],
                    "required_inputs": run["required_inputs"],
                    "stop_gates": run["stop_gates"],
                    "user_confirmation_required": run["user_confirmation_required"],
                    "safety": run["safety"],
                    "budget_contract": run["budget_contract"],
                }
            )

            errors = SESSION_MODULE.validate_session_run(root, run)

            self.assertIn("session_policy_digest_mismatch", errors)
            self.assertIn("session_policy_mismatch=allowed_writes", errors)
            self.assertIn("session_policy_mismatch=required_inputs", errors)
            self.assertIn("session_policy_mismatch=validation_checkpoints", errors)
            self.assertIn("session_policy_mismatch=stop_gates", errors)
            self.assertIn("session_policy_mismatch=user_confirmation_required", errors)
            self.assertIn("session_policy_mismatch=safety", errors)
            self.assertIn("session_policy_mismatch=budget_contract", errors)

    def test_compile_session_rejects_output_dir_outside_repo(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, tempfile.TemporaryDirectory() as outside:
            with self.assertRaises(ValueError):
                SESSION_MODULE.compile_session(Path(temp_dir), "step3", Path(outside))

    def test_compile_session_supports_all_declared_stages(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_session_fixture(root)
            for stage in ["step15", "step2", "step3", "step4"]:
                compiled = SESSION_MODULE.compile_session(root, stage)
                prompt = Path(compiled["output_dir"]) / "Session-Prompt.md"
                self.assertIn(f"KimiQB Session Prompt: {stage}", prompt.read_text(encoding="utf-8"))

    def test_default_cli_reports_blocked_status_for_missing_prerequisites(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [sys.executable, str(SESSION_RUN), "--root", temp_dir, "--stage", "step4"],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("session_run_status=blocked", result.stdout)
            self.assertNotIn("session_run_status=ready", result.stdout)

    def test_session_run_snapshot_mismatch_blocks_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            docs = write_valid_step2_fixture(root)
            main = docs / "Main-Planing.md"
            compiled = SESSION_MODULE.compile_session(root, "step2")
            run = json.loads((Path(compiled["output_dir"]) / "Session-Run.json").read_text(encoding="utf-8"))

            main.write_text("# Main Planing\n\nchanged\n", encoding="utf-8")
            errors = SESSION_MODULE.validate_session_run(root, run)

            self.assertIn("source_snapshot_mismatch", errors)

    def test_session_run_rejects_secret_like_content_and_overlapping_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            compiled = SESSION_MODULE.compile_session(root, "step3")
            run = json.loads((Path(compiled["output_dir"]) / "Session-Run.json").read_text(encoding="utf-8"))
            run["objective"] = "do not leak sk-" + "A" * 40
            run["allowed_writes"] = ["Planner-docs/Sub-Planing-Audit.md"]
            run["forbidden_writes"] = ["Planner-docs/Sub-Planing-Audit.md"]

            errors = SESSION_MODULE.validate_session_run(root, run)

            self.assertIn("secret_like_content", errors)
            self.assertIn("overlapping_allowed_forbidden_writes", errors)

    def test_session_run_rejects_template_bundle_or_compiler_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_session_fixture(root)
            compiled = SESSION_MODULE.compile_session(root, "step2")
            run = json.loads((Path(compiled["output_dir"]) / "Session-Run.json").read_text(encoding="utf-8"))
            run["template_bundle_digest"] = "0" * 64
            run["compiler"]["sha256"] = "1" * 64

            errors = SESSION_MODULE.validate_session_run(root, run)

            self.assertIn("template_bundle_digest_mismatch", errors)
            self.assertIn("compiler_digest_mismatch", errors)

    def test_session_run_rejects_unsafe_wildcards_and_glob_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_session_fixture(root)
            compiled = SESSION_MODULE.compile_session(root, "step3")
            run = json.loads((Path(compiled["output_dir"]) / "Session-Run.json").read_text(encoding="utf-8"))
            run["allowed_writes"] = ["/tmp/**", "../outside/**", "Planner-docs/**"]
            run["forbidden_writes"] = ["Planner-docs/Main-Planing.md"]

            errors = SESSION_MODULE.validate_session_run(root, run)

            self.assertIn("unsafe_path=/tmp/**", errors)
            self.assertIn("unsafe_path=../outside/**", errors)
            self.assertIn("overlapping_allowed_forbidden_writes", errors)

    def test_session_run_rejects_invalid_semantic_controls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_session_fixture(root)
            compiled = SESSION_MODULE.compile_session(root, "step2")
            run = json.loads((Path(compiled["output_dir"]) / "Session-Run.json").read_text(encoding="utf-8"))
            run["mode"] = "invalid"
            run["objective"] = " "
            run["work_steps"] = []
            run["validation_checkpoints"] = [{"argv": ["python3", "-c", "print('unsafe')"], "network": "allow"}]
            run["subagent_plan"] = {"max_depth": 99, "roles": []}
            run["context_token_budget"] = {"risk": "unbounded"}

            errors = SESSION_MODULE.validate_session_run(root, run)

            self.assertIn("invalid_session_mode=invalid", errors)
            self.assertIn("objective_required", errors)
            self.assertIn("work_steps_required", errors)
            self.assertIn("invalid_validation_checkpoints", errors)
            self.assertIn("invalid_subagent_plan", errors)
            self.assertIn("invalid_context_token_budget", errors)

    def test_session_budget_rejects_invalid_limits(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_session_fixture(root)
            compiled = SESSION_MODULE.compile_session(root, "step2")
            run = json.loads((Path(compiled["output_dir"]) / "Session-Run.json").read_text(encoding="utf-8"))
            run["budget_contract"]["soft_input_token_limit"] = -1
            run["budget_contract"]["hard_total_token_limit"] = 1
            run["budget_contract"]["pause_on_soft_limit"] = False

            errors = SESSION_MODULE.validate_session_run(root, run)

            self.assertIn("invalid_budget_contract=soft_input_token_limit", errors)
            self.assertIn("budget_contract_must_pause_on_soft_limit", errors)

    def test_session_budget_limits_step4_selected_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_session_fixture(root)
            compiled = SESSION_MODULE.compile_session(root, "step4")
            run = json.loads((Path(compiled["output_dir"]) / "Session-Run.json").read_text(encoding="utf-8"))
            run["budget_contract"]["max_selected_tasks"] = 0

            errors = SESSION_MODULE.validate_session_run(root, run)

            self.assertIn("budget_selected_tasks_exceeded", errors)

    def test_session_unknown_runtime_token_usage_is_reported_honestly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_session_fixture(root)
            compiled = SESSION_MODULE.compile_session(root, "step2")
            run = json.loads((Path(compiled["output_dir"]) / "Session-Run.json").read_text(encoding="utf-8"))
            result = json.loads((Path(compiled["output_dir"]) / "Session-Result.json").read_text(encoding="utf-8"))

            self.assertEqual(run["token_usage"]["input_tokens"], "not_observed")
            self.assertEqual(result["token_usage"]["total_tokens"], "not_observed")
            run["token_usage"] = {"status": "not_observed"}
            errors = SESSION_MODULE.validate_session_run(root, run)

            self.assertIn("token_usage_not_observed_must_be_explicit", errors)

    def test_session_render_validates_before_writing_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_session_fixture(root)
            compiled = SESSION_MODULE.compile_session(root, "step2")
            run_path = Path(compiled["output_dir"]) / "Session-Run.json"
            run = json.loads(run_path.read_text(encoding="utf-8"))
            run["objective"] = "leak sk-" + "A" * 40
            run_path.write_text(json.dumps(run), encoding="utf-8")

            code = SESSION_MODULE.main(["render", "--root", str(root), "--session-run", str(run_path)])

            self.assertEqual(code, 1)

    def test_session_prepare_blocks_missing_stage_prerequisites(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            compiled = SESSION_MODULE.compile_session(root, "step4")
            out_dir = Path(compiled["output_dir"])

            self.assertEqual(compiled["result"]["status"], "blocked")
            self.assertFalse((out_dir / "Session-Prompt.md").exists())
            self.assertIn("missing_prerequisite=Planner-docs/Sub-Planing-Audit.md", compiled["result"]["blockers"])

    def test_session_prepare_blocks_when_stage_validator_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            docs = write_valid_step2_fixture(root)
            (docs / "Sub-Planing-Index.md").write_text("# broken index\n", encoding="utf-8")

            compiled = SESSION_MODULE.compile_session(root, "step3")

            self.assertEqual(compiled["result"]["status"], "blocked")
            self.assertIn("validator_failed=step3-preflight", compiled["result"]["blockers"])
            self.assertFalse((Path(compiled["output_dir"]) / "Session-Prompt.md").exists())

    def test_session_run_id_includes_mode_and_objective_and_does_not_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_session_fixture(root)
            first = SESSION_MODULE.compile_session(root, "step2", mode="wave", objective="A")
            second = SESSION_MODULE.compile_session(root, "step2", mode="full", objective="B")

            self.assertNotEqual(first["run"]["session_spec_id"], second["run"]["session_spec_id"])
            self.assertNotEqual(first["result"]["session_run_id"], second["result"]["session_run_id"])
            fixed = root / "Planner-docs" / "Session-Runs" / "fixed"
            SESSION_MODULE.compile_session(root, "step2", mode="wave", objective="A", output_dir=fixed)
            with self.assertRaises(ValueError):
                SESSION_MODULE.compile_session(root, "step2", mode="wave", objective="A", output_dir=fixed)

    def test_session_run_detects_tampered_stored_snapshot_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_session_fixture(root)
            compiled = SESSION_MODULE.compile_session(root, "step2")
            run = json.loads((Path(compiled["output_dir"]) / "Session-Run.json").read_text(encoding="utf-8"))
            run["source_snapshot"][0]["sha256"] = "0" * 64

            errors = SESSION_MODULE.validate_session_run(root, run)

            self.assertIn("stored_source_snapshot_digest_mismatch", errors)

    def test_session_scope_collectors_include_project_specific_subplans_and_ready_queue(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_session_fixture(root)

            step2 = SESSION_MODULE.compile_session(root, "step2")
            step4 = SESSION_MODULE.compile_session(root, "step4")

            self.assertIn(
                "Planner-docs/Faz-1-Plans/Faz1.1-local-contract.md",
                step2["run"]["active_scope"]["detailed_subplans"],
            )
            step2_contract = step2["run"]["active_scope"]["subplan_contracts"][0]
            self.assertEqual(step2_contract["subplan_path"], "Planner-docs/Faz-1-Plans/Faz1.1-local-contract.md")
            self.assertTrue(step2_contract["subplan_sha256"])
            self.assertTrue(any("MP-PH1-AS-01" in item for item in step2_contract["contract_signals"]["acceptance_criteria"]))
            self.assertTrue(any("implementation_paths" in item for item in step2_contract["contract_signals"]["allowed_paths"]))
            self.assertTrue(any("parent_signals" in item for item in step2_contract["contract_signals"]["parent_signals"]))
            self.assertTrue(any("validation_commands" in item for item in step2_contract["contract_signals"]["structured_validation_commands"]))
            self.assertTrue(step2_contract["security_review_required"])
            implementation_contract = step2_contract["implementation_contract"]
            implementation_digest = SESSION_MODULE.sha256_bytes(
                json.dumps(implementation_contract, sort_keys=True, separators=(",", ":")).encode("utf-8")
            )
            self.assertEqual(step2_contract["implementation_contract_digest"], implementation_digest)
            self.assertEqual(implementation_contract["contract_version"], 1)
            self.assertEqual(implementation_contract["parent_signals"], ["MP-PH1-AS-01"])
            self.assertEqual(implementation_contract["outputs"], ["reports/faz1-1-readiness.md"])
            self.assertEqual(implementation_contract["validation_commands"][0]["id"], "VAL-01")
            self.assertEqual(
                implementation_contract["validation_commands"][0]["argv"],
                ["python3", "-m", "pytest", "tests/test_feature_1_1.py", "-q"],
            )
            self.assertEqual(step2_contract["structured_validation_command_count"], 1)
            self.assertEqual(step2_contract["validation_command_ids"], ["VAL-01"])
            self.assertEqual(
                step4["run"]["active_scope"]["ready_queue"][0]["subplan_path"],
                "Planner-docs/Faz-1-Plans/Faz1.1-local-contract.md",
            )
            self.assertIn("contract_signals", step4["run"]["active_scope"]["ready_queue"][0])
            self.assertEqual(
                step4["run"]["active_scope"]["ready_queue"][0]["implementation_contract"]["outputs"],
                ["reports/faz1-1-readiness.md"],
            )
            self.assertEqual(
                step4["run"]["active_scope"]["ready_queue"][0]["implementation_contract_digest"],
                implementation_digest,
            )
            self.assertGreaterEqual(step4["run"]["active_scope"]["ready_queue"][0]["validation_command_count"], 1)
            self.assertEqual(step4["run"]["active_scope"]["ready_queue"][0]["structured_validation_command_count"], 1)
            self.assertEqual(step4["run"]["active_scope"]["ready_queue"][0]["validation_command_ids"], ["VAL-01"])
            roles = {role["role"]: role for role in step4["run"]["subagent_plan"]["roles"]}
            self.assertEqual(roles["implementer"]["model_profile"], "balanced")
            self.assertEqual(roles["implementer"]["sandbox"], "workspace-write")
            self.assertEqual(roles["task_reviewer"]["sandbox"], "read-only")
            self.assertEqual(roles["security_reviewer"]["model_profile"], "security_strong")
            self.assertFalse(roles["security_reviewer"]["fork_context"])
            self.assertIn("final_reviewer", roles)
            work_steps = "\n".join(step4["run"]["work_steps"])
            self.assertIn("Planner-docs/Faz-1-Plans/Faz1.1-local-contract.md", work_steps)
            self.assertIn("parent_signals=MP-PH1-AS-01", work_steps)
            self.assertIn("implementation_paths=src/feature_1_1.py,tests/test_feature_1_1.py", work_steps)
            self.assertIn("validation_command_ids=VAL-01", work_steps)
            self.assertIn("outputs=reports/faz1-1-readiness.md", work_steps)

    def test_session_contract_is_bound_to_source_subplan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_session_fixture(root)
            compiled = SESSION_MODULE.compile_session(root, "step2")
            item = compiled["run"]["active_scope"]["subplan_contracts"][0]

            self.assertEqual(item["source_subplan_path"], "Planner-docs/Faz-1-Plans/Faz1.1-local-contract.md")
            self.assertEqual(item["source_subplan_sha256"], item["subplan_sha256"])
            self.assertTrue(item["implementation_contract_digest"])
            self.assertEqual(item["parent_acceptance_signal_ids"], ["MP-PH1-AS-01"])
            self.assertEqual(item["risk_class"], "low")
            self.assertEqual(item["risk_domains"], ["none"])
            self.assertEqual(SESSION_MODULE.validate_session_run(root, compiled["run"]), [])

    def test_session_rejects_self_consistent_but_source_divergent_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_session_fixture(root)
            compiled = SESSION_MODULE.compile_session(root, "step2", run_id_suffix="tamper")
            run = json.loads((Path(compiled["output_dir"]) / "Session-Run.json").read_text(encoding="utf-8"))
            item = run["active_scope"]["subplan_contracts"][0]
            item["implementation_contract"]["outputs"] = ["reports/tampered.md"]
            item["implementation_contract_digest"] = SESSION_MODULE.implementation_contract_digest(item["implementation_contract"])
            self.rewrite_session_identity(run)

            errors = SESSION_MODULE.validate_session_run(root, run)

            self.assertIn("implementation_contract_source_mismatch=Planner-docs/Faz-1-Plans/Faz1.1-local-contract.md", errors)
            self.assertIn("implementation_contract_digest_source_mismatch=Planner-docs/Faz-1-Plans/Faz1.1-local-contract.md", errors)

    def test_session_rejects_validation_ids_divergent_from_source_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_session_fixture(root)
            compiled = SESSION_MODULE.compile_session(root, "step2", run_id_suffix="tamper")
            run = json.loads((Path(compiled["output_dir"]) / "Session-Run.json").read_text(encoding="utf-8"))
            item = run["active_scope"]["subplan_contracts"][0]
            item["implementation_contract"]["validation_commands"][0]["id"] = "VAL-99"
            item["validation_command_ids"] = ["VAL-99"]
            item["implementation_contract_digest"] = SESSION_MODULE.implementation_contract_digest(item["implementation_contract"])
            self.rewrite_session_identity(run)

            errors = SESSION_MODULE.validate_session_run(root, run)

            self.assertIn("validation_command_ids_source_mismatch=Planner-docs/Faz-1-Plans/Faz1.1-local-contract.md", errors)

    def test_session_rejects_security_flags_divergent_from_source_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_session_fixture(root)
            compiled = SESSION_MODULE.compile_session(root, "step2", run_id_suffix="tamper")
            run = json.loads((Path(compiled["output_dir"]) / "Session-Run.json").read_text(encoding="utf-8"))
            item = run["active_scope"]["subplan_contracts"][0]
            item["implementation_contract"]["security_review_required"] = False
            item["security_review_required"] = False
            item["implementation_contract_digest"] = SESSION_MODULE.implementation_contract_digest(item["implementation_contract"])
            self.rewrite_session_identity(run)

            errors = SESSION_MODULE.validate_session_run(root, run)

            self.assertIn("security_review_required_source_mismatch=Planner-docs/Faz-1-Plans/Faz1.1-local-contract.md", errors)

    def test_session_rejects_missing_or_duplicate_source_subplan_mappings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_session_fixture(root)
            compiled = SESSION_MODULE.compile_session(root, "step2", run_id_suffix="tamper")
            run = json.loads((Path(compiled["output_dir"]) / "Session-Run.json").read_text(encoding="utf-8"))
            items = run["active_scope"]["subplan_contracts"]
            missing = json.loads(json.dumps(items[0]))
            missing["source_subplan_path"] = "Planner-docs/Missing.md"
            items.append(missing)
            items.append(json.loads(json.dumps(items[0])))
            self.rewrite_session_identity(run)

            errors = SESSION_MODULE.validate_session_run(root, run)

            self.assertIn("missing_source_subplan=Planner-docs/Missing.md", errors)
            self.assertIn("duplicate_source_subplan_mapping=Planner-docs/Faz-1-Plans/Faz1.1-local-contract.md", errors)

    def test_step2_session_collects_main_plan_horizon_before_subplans_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            docs = root / "Planner-docs"
            docs.mkdir()
            write_main_plan_with_phases(docs, list(range(7)))
            main = docs / "Main-Planing.md"
            text = main.read_text(encoding="utf-8")
            text = text.replace(
                "Detail phases 0-4 first; keep later phases deferred until the first wave is audited.",
                (
                    "Detail phases 0-2 first; keep later phases deferred until the first wave is audited. "
                    "The plan uses TRL, vLLM, PEFT, GRPO rollout groups, and stateful policy fingerprints."
                ),
            )
            main.write_text(text, encoding="utf-8")

            compiled = SESSION_MODULE.compile_session(root, "step2", mode="wave", run_id_suffix="horizon")
            scope = compiled["run"]["active_scope"]
            horizon = scope["planning_horizon"]

            self.assertEqual(scope["detailed_subplans"], [])
            self.assertEqual(scope["subplan_contracts"], [])
            self.assertEqual(horizon["planning_mode"], "wave")
            self.assertEqual(horizon["detected_phases"], [0, 1, 2, 3, 4, 5, 6])
            self.assertEqual(horizon["active_phases"], [0, 1, 2])
            self.assertEqual(horizon["deferred_phases"], [3, 4, 5, 6])
            self.assertEqual(horizon["parent_acceptance_signals"][0], "MP-PH0-AS-01")
            self.assertEqual(horizon["max_detailed_subplans"], 10)
            self.assertEqual(horizon["max_output_words"], 12000)
            self.assertTrue(horizon["framework_ownership_required"])
            self.assertTrue(horizon["algorithmic_invariants_required"])
            self.assertIn("confirmation_threshold", horizon)

    def test_step3_session_includes_preflight_and_post_audit_checkpoints(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_session_fixture(root)

            compiled = SESSION_MODULE.compile_session(root, "step3")
            checkpoints = compiled["run"]["validation_checkpoints"]
            modes = [checkpoint["argv"][checkpoint["argv"].index("--mode") + 1] for checkpoint in checkpoints]

            self.assertIn("step3-preflight", modes)
            self.assertIn("step3", modes)
            self.assertTrue(all(checkpoint["argv"][-1] == "--strict" for checkpoint in checkpoints))

    def test_step3_expected_audit_output_does_not_break_resume(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            docs = write_valid_step2_fixture(root)
            compiled = SESSION_MODULE.compile_session(root, "step3")
            run = json.loads((Path(compiled["output_dir"]) / "Session-Run.json").read_text(encoding="utf-8"))
            write_audit(docs, "PASS")

            self.assertEqual(SESSION_MODULE.validate_session_run(root, run), [])

    def test_step3_source_plan_change_breaks_resume(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            docs = write_valid_step2_fixture(root)
            compiled = SESSION_MODULE.compile_session(root, "step3")
            run = json.loads((Path(compiled["output_dir"]) / "Session-Run.json").read_text(encoding="utf-8"))
            subplan = docs / "Faz-1-Plans" / "Faz1.1-local-contract.md"
            subplan.write_text(subplan.read_text(encoding="utf-8") + "\nsource drift\n", encoding="utf-8")

            errors = SESSION_MODULE.validate_session_run(root, run)

            self.assertIn("source_snapshot_mismatch", errors)

    def test_step4_ledger_update_does_not_break_resume(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            docs = write_valid_step2_fixture(root)
            write_audit(docs, "PASS")
            write_ledger(docs)
            compiled = SESSION_MODULE.compile_session(root, "step4")
            run = json.loads((Path(compiled["output_dir"]) / "Session-Run.json").read_text(encoding="utf-8"))
            ledger = docs / "Planing-Ledger.md"
            ledger.write_text(ledger.read_text(encoding="utf-8") + "\nStep 4 expected ledger update.\n", encoding="utf-8")

            self.assertEqual(SESSION_MODULE.validate_session_run(root, run), [])

    def test_step4_selected_subplan_change_breaks_resume(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            docs = write_valid_step2_fixture(root)
            write_audit(docs, "PASS")
            compiled = SESSION_MODULE.compile_session(root, "step4")
            run = json.loads((Path(compiled["output_dir"]) / "Session-Run.json").read_text(encoding="utf-8"))
            subplan = docs / "Faz-1-Plans" / "Faz1.1-local-contract.md"
            subplan.write_text(subplan.read_text(encoding="utf-8") + "\nsource drift\n", encoding="utf-8")

            errors = SESSION_MODULE.validate_session_run(root, run)

            self.assertIn("source_snapshot_mismatch", errors)

    def test_step4_unselected_subplan_change_does_not_break_resume(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            docs = write_valid_step2_fixture(root)
            write_audit(docs, "PASS")
            compiled = SESSION_MODULE.compile_session(root, "step4")
            run = json.loads((Path(compiled["output_dir"]) / "Session-Run.json").read_text(encoding="utf-8"))
            unselected = docs / "Faz-2-Plans" / "Faz2.1-live-gateway.md"
            unselected.write_text(unselected.read_text(encoding="utf-8") + "\ndeferred source note\n", encoding="utf-8")

            self.assertEqual(SESSION_MODULE.validate_session_run(root, run), [])

    def test_step4_expected_implementation_paths_can_change_without_snapshot_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            docs = write_valid_step2_fixture(root)
            write_audit(docs, "PASS")
            compiled = SESSION_MODULE.compile_session(root, "step4")
            run = json.loads((Path(compiled["output_dir"]) / "Session-Run.json").read_text(encoding="utf-8"))
            (root / "src").mkdir()
            (root / "src" / "feature_1_1.py").write_text("VALUE = 1\n", encoding="utf-8")

            self.assertEqual(SESSION_MODULE.validate_session_run(root, run), [])

    def test_step4_allowed_writes_include_apply_and_contract_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_session_fixture(root)
            compiled = SESSION_MODULE.compile_session(root, "step4")
            run = json.loads((Path(compiled["output_dir"]) / "Session-Run.json").read_text(encoding="utf-8"))
            prompt = (Path(compiled["output_dir"]) / "Session-Prompt.md").read_text(encoding="utf-8")

            self.assertIn("Planner-docs/Planing-Ledger.md", run["allowed_writes"])
            self.assertIn(".kimiqb/apply-runs/**", run["allowed_writes"])
            self.assertIn("src/feature_1_1.py", run["allowed_writes"])
            self.assertIn("tests/test_feature_1_1.py", run["allowed_writes"])
            self.assertIn(".kimiqb/apply-runs/**", prompt)
            self.assertIn("src/feature_1_1.py", prompt)

    def test_session_rejects_work_steps_divergent_from_source_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_session_fixture(root)
            compiled = SESSION_MODULE.compile_session(root, "step4", run_id_suffix="tamper")
            run = json.loads((Path(compiled["output_dir"]) / "Session-Run.json").read_text(encoding="utf-8"))

            run["work_steps"] = ["Execute a stale validation-command ID from an old sub-plan."]

            self.assertIn("work_steps_mismatch", SESSION_MODULE.validate_session_run(root, run))

    def test_session_rejects_subplan_path_alias_for_source_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_session_fixture(root)
            compiled = SESSION_MODULE.compile_session(root, "step4", run_id_suffix="alias")
            run = json.loads((Path(compiled["output_dir"]) / "Session-Run.json").read_text(encoding="utf-8"))
            ready_item = run["active_scope"]["ready_queue"][0]
            ready_item["subplan_path"] = "Planner-docs/Faz-1-Plans/Other.md"
            self.rewrite_session_identity(run)

            errors = SESSION_MODULE.validate_session_run(root, run)
            self.assertIn(f"subplan_source_path_mismatch={ready_item['source_subplan_path']}", errors)

    def test_unexpected_workspace_change_breaks_resume(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            docs = write_valid_step2_fixture(root)
            write_audit(docs, "PASS")
            compiled = SESSION_MODULE.compile_session(root, "step4")
            run = json.loads((Path(compiled["output_dir"]) / "Session-Run.json").read_text(encoding="utf-8"))
            (root / "src").mkdir()
            (root / "src" / "unrelated.py").write_text("VALUE = 1\n", encoding="utf-8")

            errors = SESSION_MODULE.validate_session_run(root, run)

            self.assertIn("workspace_baseline_mismatch=workspace_inventory_sha256", errors)

    def test_session_workspace_inventory_uses_git_tracked_files_and_ignores_gitignored_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_session_fixture(root)
            (root / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
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
            compiled = SESSION_MODULE.compile_session(root, "step4")
            run = json.loads((Path(compiled["output_dir"]) / "Session-Run.json").read_text(encoding="utf-8"))
            (root / "node_modules" / "pkg").mkdir(parents=True)
            (root / "node_modules" / "pkg" / "cache.js").write_text("ignored cache\n", encoding="utf-8")

            self.assertEqual(SESSION_MODULE.validate_session_run(root, run), [])

    def test_missing_mutable_output_is_distinguishable_from_immutable_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            docs = write_valid_step2_fixture(root)
            write_audit(docs, "PASS")
            write_ledger(docs)
            compiled = SESSION_MODULE.compile_session(root, "step4")
            run = json.loads((Path(compiled["output_dir"]) / "Session-Run.json").read_text(encoding="utf-8"))
            (docs / "Planing-Ledger.md").unlink()

            errors = SESSION_MODULE.validate_session_run(root, run)

            self.assertIn("mutable_output_removed=Planner-docs/Planing-Ledger.md", errors)
            self.assertNotIn("source_snapshot_mismatch", errors)

    def test_duplicate_mutable_output_declarations_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            docs = write_valid_step2_fixture(root)
            write_audit(docs, "PASS")
            compiled = SESSION_MODULE.compile_session(root, "step4")
            run = json.loads((Path(compiled["output_dir"]) / "Session-Run.json").read_text(encoding="utf-8"))
            mutable = run["stage_snapshot"]["mutable_outputs"]
            mutable["declared"].append("Planner-docs/Planing-Ledger.md")
            mutable["duplicates"].append("Planner-docs/Planing-Ledger.md")

            errors = SESSION_MODULE.validate_session_run(root, run)

            self.assertIn("duplicate_mutable_output_declarations", errors)


if __name__ == "__main__":
    unittest.main()
