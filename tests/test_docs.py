from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class DocumentationTests(unittest.TestCase):
    def test_docs_are_kimi_facing(self) -> None:
        docs = [
            REPO_ROOT / "README.md",
            REPO_ROOT / "docs/INSTALLATION.md",
            REPO_ROOT / "docs/USAGE.md",
            REPO_ROOT / "docs/MAINTAINING.md",
        ]
        for path in docs:
            text = path.read_text(encoding="utf-8")
            self.assertIn("KimiQB", text, path)
            self.assertIn("Kimi Code", text, path)
            self.assertNotIn("codex plugin", text.lower(), path)
            self.assertNotIn("$codexqb", text, path)
            self.assertNotIn("Hedefi Takip Et", text, path)

    def test_installation_docs_include_supported_kimi_commands(self) -> None:
        install = (REPO_ROOT / "docs/INSTALLATION.md").read_text(encoding="utf-8")
        for command in [
            "/plugins install /Users/alicankiraz/Desktop/BillionDollarsIdeas/KimiQB",
            "/plugins install https://github.com/alicankiraz1/KimiQB",
            "/plugins info kimiqb",
            "/plugins reload",
            "/new",
            "/skill:kimiqb",
        ]:
            self.assertIn(command, install)

    def test_maintaining_docs_include_release_validation(self) -> None:
        maintaining = (REPO_ROOT / "docs/MAINTAINING.md").read_text(encoding="utf-8")
        self.assertIn("make check", maintaining)
        self.assertIn("KimiQB-sanitized.zip", maintaining)
        self.assertIn("CodexQB source is read-only", maintaining)


if __name__ == "__main__":
    unittest.main()
