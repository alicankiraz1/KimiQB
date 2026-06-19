from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills/kimiqb"


class SkillContentTests(unittest.TestCase):
    def test_kimi_skill_frontmatter_is_complete(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(skill.startswith("---\n"))
        self.assertIn("name: kimiqb", skill)
        self.assertIn("description:", skill)
        self.assertIn("type: prompt", skill)
        self.assertIn("whenToUse:", skill)
        self.assertIn("disableModelInvocation: false", skill)

    def test_skill_uses_kimi_paths_and_invocation(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("${KIMI_SKILL_DIR}/references/repo-aware-intake.md", skill)
        self.assertIn("${KIMI_SKILL_DIR}/scripts/validate_planner_docs.py", skill)
        self.assertIn("/skill:kimiqb", skill)
        self.assertIn("new Kimi Code session", skill)

    def test_required_references_exist(self) -> None:
        required = [
            "First-Planner.md",
            "Autopsy-Planner.md",
            "Second-Planner.md",
            "Third-Planner.md",
            "Fourth-Planner.md",
            "repo-aware-intake.md",
            "workflow-quality.md",
            "vibecoding-principles.md",
            "subagent-playbook.md",
            "planning-ledger.md",
            "project-ontology.md",
            "project-comprehension-methods.md",
            "probe-policy.md",
            "assessment-and-budget.md",
            "engineering-principles.md",
        ]
        for filename in required:
            self.assertTrue((SKILL_ROOT / "references" / filename).is_file(), filename)
        for filename in ["run-step2.md", "run-step3.md", "run-step4.md"]:
            self.assertTrue((SKILL_ROOT / "references/handoffs" / filename).is_file(), filename)

    def test_language_contract_is_documented(self) -> None:
        required_phrases = [
            "KimiQB asks intake questions in the user's language when practical.",
            "Generated Planner-docs artifacts are English by default unless the user explicitly requests another content language.",
            "Required document headings remain English for validator stability.",
        ]
        checked_files = [
            REPO_ROOT / "README.md",
            REPO_ROOT / "docs/USAGE.md",
            SKILL_ROOT / "SKILL.md",
        ]
        for path in checked_files:
            text = path.read_text(encoding="utf-8")
            for phrase in required_phrases:
                self.assertIn(phrase, text, path.name)

        for path in [
            SKILL_ROOT / "references/First-Planner.md",
            SKILL_ROOT / "references/Second-Planner.md",
            SKILL_ROOT / "references/Third-Planner.md",
        ]:
            text = path.read_text(encoding="utf-8")
            self.assertIn("English by default unless the user explicitly requests another content language", text, path.name)
            self.assertIn("Required document headings remain English", text, path.name)

    def test_repo_aware_intake_keeps_stable_four_fields(self) -> None:
        intake = (SKILL_ROOT / "references/repo-aware-intake.md").read_text(encoding="utf-8")
        for field in ["PROJECT_NAME", "PROJECT_INTENT", "TARGET_END_STATE", "KNOWN_CONSTRAINTS"]:
            self.assertIn(field, intake)
        for number in range(1, 5):
            self.assertIn(f"Question {number} / 4", intake)
        self.assertIn("Use plain text only", intake)
        self.assertIn("Pre-Intake Scan", intake)

    def test_first_planner_required_placeholders_remain_stable(self) -> None:
        first_planner = (SKILL_ROOT / "references/First-Planner.md").read_text(encoding="utf-8")
        headings = re.findall(r"^([A-Z_]+):$", first_planner, flags=re.MULTILINE)
        required = ["PROJECT_NAME", "PROJECT_INTENT", "TARGET_END_STATE", "KNOWN_CONSTRAINTS"]
        for field in required:
            self.assertIn(field, headings)
        positions = [headings.index(field) for field in required]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("INTAKE_EVIDENCE_SUMMARY:", first_planner)

    def test_autopsy_planner_is_wired_into_skill_and_step2(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        second = (SKILL_ROOT / "references/Second-Planner.md").read_text(encoding="utf-8")
        autopsy = (SKILL_ROOT / "references/Autopsy-Planner.md").read_text(encoding="utf-8")

        self.assertIn("references/Autopsy-Planner.md", skill)
        self.assertIn("Step 1.5", skill)
        self.assertIn("Planner-docs/Autopsy.md", second)
        self.assertIn("Autopsy.md is not a replacement for Main-Planing.md", second)

        required_headings = [
            "# Project Autopsy",
            "## 1. Executive Summary",
            "## 2. Reviewed Sources",
            "## 3. Project Areas and Ownership Boundaries",
            "## 4. Feature Inventory",
            "## 5. Placeholder, Stub, and Skeleton Analysis",
            "## 6. Technical Debt and Maintenance Risks",
            "## 7. Broken or Missing Integrations",
            "## 8. Test, CI, and Validation Gaps",
            "## 9. Security, Secret, and Governance Findings",
            "## 10. Operational Readiness and Observability",
            "## 11. Alignment Analysis with the Main Plan",
            "## 12. Autopsy Feedback for Step 2",
            "## 13. Priority Fix and Planning Signals",
        ]
        for heading in required_headings:
            self.assertIn(heading, autopsy)

    def test_plugin_metadata_reflects_021_gate_integrity_release(self) -> None:
        manifest_text = (REPO_ROOT / "kimi.plugin.json").read_text(encoding="utf-8")
        self.assertIn('"version": "0.2.1"', manifest_text)
        for phrase in [
            "project comprehension",
            "evidence",
            "traceability",
            "vibecoding",
            "ontology",
            "ledger",
            "gate",
        ]:
            self.assertIn(phrase, manifest_text.lower())

    def test_second_planner_keeps_security_and_ontology_out_of_scope_clean(self) -> None:
        second = (SKILL_ROOT / "references/Second-Planner.md").read_text(encoding="utf-8")
        scope = second.split("## 4. Scope", 1)[1].split("## 5. Out of Scope", 1)[0]
        out_of_scope = second.split("## 5. Out of Scope", 1)[1].split("## 6. Current Repository Evidence", 1)[0]

        self.assertIn("secure coding and secure-by-design expectations where relevant", scope)
        self.assertIn("ontology, lifecycle, or invariant consistency where relevant", scope)
        self.assertNotIn("secure coding and secure-by-design expectations where relevant", out_of_scope)
        self.assertNotIn("ontology, lifecycle, or invariant consistency where relevant", out_of_scope)

    def test_autopsy_sensitive_discovery_is_file_name_only(self) -> None:
        autopsy = (SKILL_ROOT / "references/Autopsy-Planner.md").read_text(encoding="utf-8")
        normal_scan = next(line for line in autopsy.splitlines() if line.strip().startswith("- rg \"TODO|FIXME"))
        sensitive_scan = next(line for line in autopsy.splitlines() if "secret|token|credential" in line and "rg -l" in line)

        self.assertNotIn("secret|token|credential", normal_scan)
        self.assertIn("rg -l", sensitive_scan)
        self.assertIn("file-name-only", autopsy)

    def test_project_comprehension_reference_and_prompts_are_wired(self) -> None:
        ref = SKILL_ROOT / "references/project-comprehension-methods.md"
        self.assertTrue(ref.is_file())
        ref_text = ref.read_text(encoding="utf-8")
        for phrase in [
            "question-driven comprehension",
            "why/how/what hypotheses",
            "Evidence Register",
            "Domain-to-Code Trace Map",
            "Architecture Reflexion",
            "QAW/ATAM-lite",
            "Goal/Question/Evidence",
        ]:
            self.assertIn(phrase, ref_text)

        checked_files = [
            SKILL_ROOT / "SKILL.md",
            SKILL_ROOT / "references/Autopsy-Planner.md",
            SKILL_ROOT / "references/Second-Planner.md",
            SKILL_ROOT / "references/Third-Planner.md",
            SKILL_ROOT / "references/Fourth-Planner.md",
        ]
        for path in checked_files:
            text = path.read_text(encoding="utf-8")
            self.assertIn("Project-Comprehension.md", text, path.name)
            self.assertIn("project-comprehension-methods.md", text, path.name)

    def test_kimi_session_contract_uses_canonical_handoff_sources(self) -> None:
        handoff_root = SKILL_ROOT / "references/handoffs"
        for name in ["run-step2.md", "run-step3.md", "run-step4.md"]:
            path = handoff_root / name
            self.assertTrue(path.is_file(), name)
            text = path.read_text(encoding="utf-8")
            self.assertIn("contract_version: 1", text)
            self.assertIn("Kimi Code Session Contract", text)
            self.assertIn("Resume / Recovery Protocol", text)
            for phrase in [
                "Outcome",
                "Inputs",
                "Boundaries",
                "Source precedence",
                "Validation gates",
                "Stop gates",
                "Context budget",
                "Subagent policy",
            ]:
                self.assertIn(phrase, text, name)

        references = {
            "SKILL.md": SKILL_ROOT / "SKILL.md",
            "Second-Planner.md": SKILL_ROOT / "references/Second-Planner.md",
            "Third-Planner.md": SKILL_ROOT / "references/Third-Planner.md",
            "Fourth-Planner.md": SKILL_ROOT / "references/Fourth-Planner.md",
        }
        for name, path in references.items():
            text = path.read_text(encoding="utf-8")
            self.assertIn("references/handoffs/", text, name)
            self.assertNotIn("Kimi Code Session Contract:\n- Outcome:", text, name)

    def test_comprehension_validator_contract_is_documented(self) -> None:
        validator = (SKILL_ROOT / "scripts/validate_planner_docs.py").read_text(encoding="utf-8")
        for phrase in [
            "COMPREHENSION_HEADINGS",
            "Project-Comprehension.md",
            "ALLOWED_EVIDENCE_TYPES",
            "ALLOWED_CONFIDENCE_VALUES",
            "ALLOWED_CLAIM_TYPES",
            "ALLOWED_ARCHITECTURE_STATUSES",
            "ALLOWED_ONTOLOGY_QUESTION_STATUSES",
            "markdown_headings",
            "validate_optional_comprehension_doc",
            "NOT_APPLICABLE",
            "NO_UNRESOLVED_HYPOTHESES",
        ]:
            self.assertIn(phrase, validator)

    def test_planning_ledger_v2_is_documented_and_legacy_remains_supported(self) -> None:
        ledger_ref = (SKILL_ROOT / "references/planning-ledger.md").read_text(encoding="utf-8")
        validator = (SKILL_ROOT / "scripts/validate_planner_docs.py").read_text(encoding="utf-8")
        for phrase in [
            "Plan Snapshot Registry",
            "Sub-Plan Status Matrix",
            "Ledger v2",
            "legacy v1",
            "Superseded By",
            "Updated At",
        ]:
            self.assertIn(phrase, ledger_ref)
        self.assertIn("LEDGER_V2_HEADINGS", validator)
        self.assertIn("LEDGER_LEGACY_HEADINGS", validator)
        self.assertIn("ALLOWED_LEDGER_STATUSES", validator)

    def test_ci_and_export_sanitized_are_hardened(self) -> None:
        workflow = (REPO_ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8")
        makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("push:", workflow)
        self.assertIn("pull_request:", workflow)
        self.assertNotIn("branches: [main]", workflow)
        self.assertIn("git diff --quiet", makefile)
        self.assertIn("git diff --cached --quiet", makefile)
        self.assertIn("--prefix=KimiQB/", makefile)
        self.assertIn(":(exclude)docs/superpowers/plans", makefile)

    def test_fixture_corpus_infrastructure_is_present(self) -> None:
        runner = REPO_ROOT / "evals/run_fixture_corpus_checks.py"
        wrapper = REPO_ROOT / "evals/run_fixture_checks.py"
        self.assertTrue(runner.is_file())
        self.assertTrue(wrapper.is_file())
        runner_text = runner.read_text(encoding="utf-8")
        self.assertIn("fixture_corpus_checks=passed", runner_text)
        self.assertNotIn("fixture_eval_checks=passed", runner_text)
        fixture_root = REPO_ROOT / "evals/fixtures"
        for fixture in [
            "clean-layered-service",
            "drifted-architecture",
            "distributed-domain-feature",
            "hidden-coupling-signal",
            "stale-ledger",
            "runtime-only-behavior",
            "security-boundary-risk",
        ]:
            self.assertTrue((fixture_root / fixture / "expected.json").is_file(), fixture)

        validate_script = (REPO_ROOT / "scripts/validate.sh").read_text(encoding="utf-8")
        self.assertIn("python3 evals/run_fixture_corpus_checks.py", validate_script)

    def test_probe_policy_and_schema_versions_are_documented(self) -> None:
        probe = SKILL_ROOT / "references/probe-policy.md"
        self.assertTrue(probe.is_file())
        probe_text = probe.read_text(encoding="utf-8")
        for phrase in ["Tier 0", "Tier 1", "Tier 2", "Tier 3", "approval", "timeout", "cleanup"]:
            self.assertIn(phrase, probe_text)

        for path in [REPO_ROOT / "README.md", REPO_ROOT / "docs/USAGE.md", REPO_ROOT / "docs/MAINTAINING.md"]:
            text = path.read_text(encoding="utf-8")
            self.assertIn("artifact_schema_version: 2", text, path.name)
            self.assertIn("handoff_contract_version: 1", text, path.name)
            self.assertIn("fixture corpus", text.lower(), path.name)

    def test_local_skill_sync_docs_exclude_python_caches(self) -> None:
        install = (REPO_ROOT / "docs/INSTALLATION.md").read_text(encoding="utf-8")
        maintaining = (REPO_ROOT / "docs/MAINTAINING.md").read_text(encoding="utf-8")
        for text in [install, maintaining]:
            self.assertIn("--exclude '__pycache__/'", text)
            self.assertIn("--exclude '*.pyc'", text)
            self.assertIn("diff -ru -x __pycache__", text)

    def test_validator_guidance_does_not_assume_global_skill_path(self) -> None:
        checked_files = [
            SKILL_ROOT / "SKILL.md",
            SKILL_ROOT / "references/workflow-quality.md",
            SKILL_ROOT / "references/Second-Planner.md",
            SKILL_ROOT / "references/Third-Planner.md",
        ]
        for path in checked_files:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("~/.codex/skills/codexqb/scripts/validate_planner_docs.py", text, path.name)
            self.assertIn("bundled validator", text, path.name)
            self.assertTrue(
                "skills/kimiqb/scripts/validate_planner_docs.py" in text
                or "${KIMI_SKILL_DIR}/scripts/validate_planner_docs.py" in text,
                path.name,
            )
            self.assertIn("equivalent all-file validation", text, path.name)

    def test_public_skill_text_has_no_stale_codex_packaging_terms(self) -> None:
        stale_terms = [
            "CodexQB",
            "$codexqb",
            "Use $codexqb",
            "Hedefi Takip Et",
            ".codex-plugin",
            "plugins/codexqb",
            "agents/openai.yaml",
            "native Codex skill",
            "Codex thread",
            "Codex plugin",
            "Goal mode",
            "Goal Mode",
            "Goal Run Contract",
            "Goal-mode",
            "You are Codex",
        ]
        checked_files = [
            SKILL_ROOT / "SKILL.md",
            *sorted((SKILL_ROOT / "references").glob("*.md")),
            *sorted((SKILL_ROOT / "references/handoffs").glob("*.md")),
        ]
        for path in checked_files:
            text = path.read_text(encoding="utf-8")
            for term in stale_terms:
                self.assertNotIn(term, text, f"{path.relative_to(REPO_ROOT)} contains {term}")

    def test_fourth_planner_mentions_optional_kimi_execution_skills(self) -> None:
        fourth = (SKILL_ROOT / "references/handoffs/run-step4.md").read_text(encoding="utf-8")
        self.assertIn("if installed/available", fourth)
        self.assertIn("Kimi Code", fourth)
        self.assertIn("superpowers:executing-plans", fourth)
        self.assertIn("security-focused Kimi-compatible skills/plugins", fourth)
        self.assertIn("continue using the audit", fourth)

    def test_fourth_planner_runs_queue_continuously_with_stop_gates(self) -> None:
        fourth = (SKILL_ROOT / "references/handoffs/run-step4.md").read_text(encoding="utf-8")
        self.assertIn("Build an ordered implementation queue", fourth)
        self.assertIn("Checkpoint after every completed slice", fourth)
        self.assertIn("instead of stopping", fourth)
        self.assertIn("Stop only when one of these stop gates is hit", fourth)
        self.assertIn("token/context budget too low to continue safely", fourth)

    def test_fourth_planner_has_mechanical_per_slice_loop(self) -> None:
        fourth = (SKILL_ROOT / "references/handoffs/run-step4.md").read_text(encoding="utf-8")
        for phrase in [
            "For each implementation slice:",
            "Name the active phase/sub-plan",
            "Read AGENTS.md",
            "Run git status",
            "Inspect relevant files before editing",
            "focused failing test",
            "smallest change",
            "Run targeted validation",
            "Run the repo-level gate",
            "Summarize:",
            "scope would exceed the selected sub-plan",
        ]:
            self.assertIn(phrase, fourth)

    def test_validate_script_covers_archive_and_secret_hygiene(self) -> None:
        validate_script = (REPO_ROOT / "scripts/validate.sh").read_text(encoding="utf-8")
        for phrase in [
            "tracked_secret_hygiene_failed",
            "package_secret_hygiene_failed",
            "package_secret_hygiene_mode=filesystem",
            "openrouter_api_key",
            "OPENROUTER_API_KEY",
            "git\", \"archive\"",
            "archive_hygiene_failed",
            "package_hygiene_failed",
            "package_hygiene_mode=filesystem",
            "KIMIQB_VALIDATE_SKIP_UNITTESTS",
            "__MACOSX",
            ".local",
            "personal_path_pattern",
        ]:
            self.assertIn(phrase, validate_script)

    def test_validate_script_runs_without_git_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            package_root = Path(temp_dir) / "KimiQB"

            def ignore(_dir: str, names: list[str]) -> set[str]:
                ignored = {
                    ".git",
                    "__pycache__",
                    ".pytest_cache",
                    ".mypy_cache",
                    ".ruff_cache",
                    "KimiQB-sanitized.zip",
                }
                return ignored.intersection(names)

            shutil.copytree(REPO_ROOT, package_root, ignore=ignore)
            env = os.environ.copy()
            env["KIMIQB_VALIDATE_SKIP_UNITTESTS"] = "1"
            result = subprocess.run(
                ["bash", "scripts/validate.sh"],
                cwd=package_root,
                env=env,
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("package_secret_hygiene_mode=filesystem", result.stdout)
            self.assertIn("package_hygiene_mode=filesystem", result.stdout)
            self.assertIn("unit_tests_skipped=1", result.stdout)

    def test_archive_hygiene_pattern_matches_forbidden_paths(self) -> None:
        pattern = re.compile(
            r"(^|/)(\.git|__pycache__|\.env|artifacts|logs|tmp|__MACOSX)(/|$)"
            r"|\.pyc$|\.pem$|\.key$|\.local($|\.)"
        )
        forbidden = [
            ".git/config",
            "pkg/__pycache__/module.pyc",
            ".env",
            "artifacts/build.log",
            "logs/run.txt",
            "tmp/cache.txt",
            "__MACOSX/file",
            "keys/prod.pem",
            "keys/prod.key",
            "settings.local",
            "settings.local.json",
        ]
        allowed = [
            "README.md",
            "docs/MAINTAINING.md",
            "skills/kimiqb/SKILL.md",
        ]
        for path in forbidden:
            self.assertRegex(path, pattern)
        for path in allowed:
            self.assertNotRegex(path, pattern)

    def test_autopsy_validator_mode_is_documented(self) -> None:
        validator = (SKILL_ROOT / "scripts/validate_planner_docs.py").read_text(encoding="utf-8")
        autopsy = (SKILL_ROOT / "references/Autopsy-Planner.md").read_text(encoding="utf-8")
        maintaining = (REPO_ROOT / "docs/MAINTAINING.md").read_text(encoding="utf-8")
        self.assertIn('"autopsy"', validator)
        self.assertIn("--mode autopsy --strict", autopsy)
        self.assertIn("--mode autopsy --strict", maintaining)

    def test_vibecoding_and_subagent_references_are_wired(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        usage = (REPO_ROOT / "docs/USAGE.md").read_text(encoding="utf-8")

        expected_refs = [
            "vibecoding-principles.md",
            "subagent-playbook.md",
            "planning-ledger.md",
            "project-ontology.md",
            "assessment-and-budget.md",
            "engineering-principles.md",
        ]
        for ref in expected_refs:
            self.assertTrue((SKILL_ROOT / "references" / ref).is_file(), ref)
            self.assertIn(ref, skill, ref)

        for text_blob in [skill, readme, usage]:
            self.assertIn("vibecoding-first", text_blob.lower())
            self.assertIn("subagent", text_blob.lower())

    def test_planning_ledger_and_ontology_are_documented(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        usage = (REPO_ROOT / "docs/USAGE.md").read_text(encoding="utf-8")
        second = (SKILL_ROOT / "references/Second-Planner.md").read_text(encoding="utf-8")
        fourth = (SKILL_ROOT / "references/handoffs/run-step4.md").read_text(encoding="utf-8")

        for artifact in [
            "Planner-docs/Planing-Ledger.md",
            "Planner-docs/Project-Ontology.md",
            "Planner-docs/Project-Comprehension.md",
        ]:
            self.assertIn(artifact, skill)
            self.assertIn(artifact, usage)

        self.assertIn("Planing-Ledger.md", second)
        self.assertIn("Project-Ontology.md", second)
        self.assertIn("Planing-Ledger.md", fourth)

    def test_prompt_secret_scans_do_not_print_secret_values(self) -> None:
        prompt_paths = list((SKILL_ROOT / "references").glob("*.md")) + [SKILL_ROOT / "SKILL.md"]
        for path in prompt_paths:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn('rg -n "sk-', text, path.name)
        workflow_quality = (SKILL_ROOT / "references/workflow-quality.md").read_text(encoding="utf-8")
        self.assertIn("file-name-only", workflow_quality)

    def test_fourth_planner_mentions_subagent_roles_and_ledger(self) -> None:
        fourth = (SKILL_ROOT / "references/Fourth-Planner.md").read_text(encoding="utf-8")
        for phrase in [
            "explorer maps relevant files and risks",
            "tester/verifier identifies validation path",
            "implementer/worker makes the smallest change",
            "reviewer/security reviews the diff",
            "Only one writer should modify files per slice",
            "Planner-docs/Planing-Ledger.md",
        ]:
            self.assertIn(phrase, fourth)

    def test_validator_supports_optional_ontology_and_ledger_headings(self) -> None:
        validator = (SKILL_ROOT / "scripts/validate_planner_docs.py").read_text(encoding="utf-8")
        for phrase in [
            "ONTOLOGY_HEADINGS",
            "LEDGER_HEADINGS",
            "Project-Ontology.md",
            "Planing-Ledger.md",
            "validate_optional_continuity_docs",
        ]:
            self.assertIn(phrase, validator)


if __name__ == "__main__":
    unittest.main()
