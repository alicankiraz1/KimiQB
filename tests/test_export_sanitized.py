from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EXPORTER = REPO_ROOT / "scripts/export_sanitized.py"


def load_export_module():
    spec = importlib.util.spec_from_file_location("kimiqb_export_sanitized", EXPORTER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load export_sanitized from {EXPORTER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


EXPORT_MODULE = load_export_module()


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, text=True, capture_output=True)


def git_commit_all(root: Path, message: str = "fixture") -> None:
    git(root, "add", ".")
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=KimiQB Export Test",
            "-c",
            "user.email=kimiqb-export@example.invalid",
            "commit",
            "-m",
            message,
        ],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    )


def write_minimal_kimiqb_tree(root: Path) -> None:
    (root / "kimi.plugin.json").write_text(
        json.dumps({"version": "0.3.0"}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / "CHANGELOG.md").write_text("# Changelog\n\n## Unreleased\n\n- 0.3.0 fixture.\n", encoding="utf-8")
    (root / "README.md").write_text("# Fixture\n", encoding="utf-8")


def archive_names(output: Path) -> set[str]:
    with zipfile.ZipFile(output) as archive:
        return set(archive.namelist())


def archive_name_list(output: Path) -> list[str]:
    with zipfile.ZipFile(output) as archive:
        return archive.namelist()


def package_manifest(output: Path) -> dict[str, object]:
    with zipfile.ZipFile(output) as archive:
        return json.loads(archive.read("KimiQB/PACKAGE-MANIFEST.json").decode("utf-8"))


class ExportSanitizedTests(unittest.TestCase):
    def test_release_export_writes_manifest_from_clean_tracked_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            git(root, "init")
            write_minimal_kimiqb_tree(root)
            git_commit_all(root)
            output = root / "KimiQB-sanitized.zip"

            count = EXPORT_MODULE.create_zip(root, output)

            self.assertEqual(count, 3)
            names = archive_names(output)
            self.assertIn("KimiQB/README.md", names)
            self.assertIn("KimiQB/PACKAGE-MANIFEST.json", names)
            manifest = package_manifest(output)
            self.assertEqual(manifest["package_schema_version"], 1)
            self.assertEqual(manifest["plugin_version"], "0.3.0")
            self.assertEqual(manifest["file_count"], 3)
            self.assertEqual(manifest["working_tree_clean"], True)
            self.assertEqual(manifest["tracked_only"], True)
            self.assertEqual(manifest["include_untracked"], False)
            self.assertEqual(manifest["changelog_mentions_plugin_version"], True)
            self.assertIsInstance(manifest["tree_sha256"], str)

    def test_release_export_replaces_existing_package_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            git(root, "init")
            write_minimal_kimiqb_tree(root)
            (root / "PACKAGE-MANIFEST.json").write_text('{"stale": true}\n', encoding="utf-8")
            git_commit_all(root)
            output = root / "KimiQB-sanitized.zip"

            count = EXPORT_MODULE.create_zip(root, output)

            names = archive_name_list(output)
            self.assertEqual(count, 3)
            self.assertEqual(names.count("KimiQB/PACKAGE-MANIFEST.json"), 1)
            manifest = package_manifest(output)
            self.assertNotIn("stale", manifest)
            self.assertFalse(any(item["path"] == "PACKAGE-MANIFEST.json" for item in manifest["files"]))

    def test_release_export_rejects_dirty_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            git(root, "init")
            write_minimal_kimiqb_tree(root)
            git_commit_all(root)
            (root / "notes.txt").write_text("local draft\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "working_tree_dirty"):
                EXPORT_MODULE.create_zip(root, root / "KimiQB-sanitized.zip")

    def test_include_untracked_scans_secret_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            git(root, "init")
            write_minimal_kimiqb_tree(root)
            git_commit_all(root)
            (root / "notes.txt").write_text("leaked sk-" + "A" * 40 + "\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "secret_like_content=notes.txt"):
                EXPORT_MODULE.create_zip(
                    root,
                    root / "KimiQB-sanitized.zip",
                    include_untracked=True,
                    allow_dirty=True,
                    allow_head_mismatch=True,
                )

    def test_worktree_export_can_include_scanned_untracked_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            git(root, "init")
            write_minimal_kimiqb_tree(root)
            git_commit_all(root)
            (root / "notes.txt").write_text("local draft without secrets\n", encoding="utf-8")
            output = root / "KimiQB-sanitized.zip"

            count = EXPORT_MODULE.create_zip(
                root,
                output,
                include_untracked=True,
                allow_dirty=True,
                allow_head_mismatch=True,
            )

            self.assertEqual(count, 4)
            self.assertIn("KimiQB/notes.txt", archive_names(output))
            manifest = package_manifest(output)
            self.assertEqual(manifest["tracked_only"], False)
            self.assertEqual(manifest["include_untracked"], True)
            self.assertEqual(manifest["working_tree_clean"], False)

    @unittest.skipUnless(hasattr(Path, "symlink_to"), "symlink support required")
    def test_export_rejects_symlink_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, tempfile.TemporaryDirectory() as outside_dir:
            root = Path(temp_dir)
            outside = Path(outside_dir) / "outside.txt"
            outside.write_text("outside secret\n", encoding="utf-8")
            git(root, "init")
            write_minimal_kimiqb_tree(root)
            (root / "external-link.txt").symlink_to(outside)
            git_commit_all(root)

            with self.assertRaisesRegex(ValueError, "symlink_rejected=external-link.txt"):
                EXPORT_MODULE.create_zip(root, root / "KimiQB-sanitized.zip")


if __name__ == "__main__":
    unittest.main()
