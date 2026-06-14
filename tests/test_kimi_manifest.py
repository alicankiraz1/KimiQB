from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "kimi.plugin.json"


class KimiManifestTests(unittest.TestCase):
    def test_manifest_has_kimi_plugin_shape(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

        self.assertEqual(manifest["name"], "kimiqb")
        self.assertRegex(manifest["name"], r"^[a-z0-9][a-z0-9_-]{0,63}$")
        self.assertRegex(manifest["version"], r"^\d+\.\d+\.\d+$")
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertEqual(manifest["license"], "MIT")

        interface = manifest["interface"]
        self.assertEqual(interface["displayName"], "KimiQB")
        self.assertIn("planning", interface["shortDescription"].lower())
        self.assertEqual(interface["developerName"], "Alican Kiraz")
        self.assertTrue(interface["websiteURL"].startswith("https://github.com/"))

    def test_manifest_avoids_codex_only_or_unsupported_runtime_fields(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        unsupported = {"tools", "commands", "hooks", "apps", "inject", "configFile"}
        self.assertFalse(unsupported.intersection(manifest), unsupported.intersection(manifest))
        self.assertNotIn(".codex-plugin", json.dumps(manifest))
        self.assertNotIn("codexqb", json.dumps(manifest).lower())


if __name__ == "__main__":
    unittest.main()
