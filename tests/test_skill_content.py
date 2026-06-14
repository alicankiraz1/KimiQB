from __future__ import annotations

import re
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
        ]
        for filename in required:
            self.assertTrue((SKILL_ROOT / "references" / filename).is_file(), filename)

    def test_planner_contract_keeps_stable_four_fields(self) -> None:
        intake = (SKILL_ROOT / "references/repo-aware-intake.md").read_text(encoding="utf-8")
        for field in ["PROJECT_NAME", "PROJECT_INTENT", "TARGET_END_STATE", "KNOWN_CONSTRAINTS"]:
            self.assertIn(field, intake)
        for number in range(1, 5):
            self.assertIn(f"Soru {number} / 4", intake)

    def test_first_planner_required_placeholders_remain_stable(self) -> None:
        first_planner = (SKILL_ROOT / "references/First-Planner.md").read_text(encoding="utf-8")
        headings = re.findall(r"^([A-Z_]+):$", first_planner, flags=re.MULTILINE)
        required = ["PROJECT_NAME", "PROJECT_INTENT", "TARGET_END_STATE", "KNOWN_CONSTRAINTS"]
        for field in required:
            self.assertIn(field, headings)
        positions = [headings.index(field) for field in required]
        self.assertEqual(positions, sorted(positions))

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
            "You are Codex",
        ]
        checked_files = [SKILL_ROOT / "SKILL.md", *sorted((SKILL_ROOT / "references").glob("*.md"))]
        for path in checked_files:
            text = path.read_text(encoding="utf-8")
            for term in stale_terms:
                self.assertNotIn(term, text, f"{path.relative_to(REPO_ROOT)} contains {term}")

    def test_fourth_planner_mentions_optional_kimi_execution_skills(self) -> None:
        fourth = (SKILL_ROOT / "references/Fourth-Planner.md").read_text(encoding="utf-8")
        self.assertIn("if installed/available", fourth)
        self.assertIn("Kimi Code", fourth)
        self.assertIn("continue using the audit", fourth)

    def test_fourth_planner_runs_queue_continuously_with_stop_gates(self) -> None:
        fourth = (SKILL_ROOT / "references/Fourth-Planner.md").read_text(encoding="utf-8")
        self.assertIn("Build an ordered implementation queue", fourth)
        self.assertIn("Execute the queue continuously", fourth)
        self.assertIn("instead of stopping", fourth)
        self.assertIn("Stop only when one of these stop gates is hit", fourth)
        self.assertIn("token/context budget too low to continue safely", fourth)


if __name__ == "__main__":
    unittest.main()
