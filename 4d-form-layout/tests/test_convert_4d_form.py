from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TESTS_DIR.parent
SCRIPT = SKILL_DIR / "scripts" / "convert_4d_form.py"
WORKSPACE_ROOT = SKILL_DIR.parents[1]
NATIVE_FIXTURES_DIR = TESTS_DIR / "fixtures" / "native"
FIGMA_FIXTURES_DIR = TESTS_DIR / "fixtures" / "figma"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def run_cli(*args: str, check: bool = True):
    return subprocess.run(
        ["python3", str(SCRIPT), *args],
        cwd=str(WORKSPACE_ROOT),
        capture_output=True,
        text=True,
        check=check,
    )


class Convert4DFormTests(unittest.TestCase):
    maxDiff = None

    def test_round_trip_known_native_fixtures(self):
        native_fixtures = [
            NATIVE_FIXTURES_DIR / "basic.form.4DForm",
            NATIVE_FIXTURES_DIR / "with_image.form.4DForm",
            NATIVE_FIXTURES_DIR / "vscode-preview.form.4DForm",
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            for source in native_fixtures:
                self.assertTrue(source.exists(), f"Missing fixture: {source}")
                layout_path = tmp / f"{source.stem}.layout.json"
                round_trip_path = tmp / f"{source.stem}.roundtrip.4DForm"
                run_cli("form-to-layout", str(source), str(layout_path))
                run_cli("layout-to-form", str(layout_path), str(round_trip_path))
                self.assertEqual(load_json(source), load_json(round_trip_path), source.as_posix())

    def test_relational_only_layout_generates_expected_coordinates(self):
        fixture = TESTS_DIR / "fixtures" / "relational.layout.json"
        with tempfile.TemporaryDirectory() as tmpdir:
            native_path = Path(tmpdir) / "relational.4DForm"
            run_cli("layout-to-form", str(fixture), str(native_path))
            native = load_json(native_path)
            page = native["pages"][0]["objects"]
            self.assertEqual(page["submitButton"]["top"], 76)
            self.assertEqual(page["submitButton"]["left"], 20)
            self.assertEqual(page["cancelButton"]["top"], 76)
            self.assertEqual(page["cancelButton"]["left"], 178)
            self.assertEqual(page["centeredTitle"]["left"], 150)
            self.assertEqual(page["centeredTitle"]["top"], 140)

    def test_mixed_mode_and_entry_order_round_trip(self):
        fixture = TESTS_DIR / "fixtures" / "mixed.layout.json"
        with tempfile.TemporaryDirectory() as tmpdir:
            native_path = Path(tmpdir) / "mixed.4DForm"
            layout_back = Path(tmpdir) / "mixed.back.layout.json"
            run_cli("layout-to-form", str(fixture), str(native_path))
            run_cli("form-to-layout", str(native_path), str(layout_back))
            native = load_json(native_path)
            self.assertEqual(native["pages"][0]["entryOrder"], ["email", "saveButton"])
            self.assertEqual(native["pages"][1]["objects"]["notes"]["left"], 30)
            self.assertEqual(native["pages"][1]["objects"]["notes"]["top"], 40)
            self.assertEqual(load_json(layout_back)["pages"][0]["entryOrder"], ["email", "saveButton"])

    def test_shared_page_zero_layout_is_preserved(self):
        fixture = TESTS_DIR / "fixtures" / "shared-page.layout.json"
        with tempfile.TemporaryDirectory() as tmpdir:
            native_path = Path(tmpdir) / "shared-page.4DForm"
            layout_back = Path(tmpdir) / "shared-page.back.layout.json"
            run_cli("layout-to-form", str(fixture), str(native_path))
            run_cli("form-to-layout", str(native_path), str(layout_back))
            native = load_json(native_path)
            roundtrip = load_json(layout_back)
            self.assertEqual(native["pages"][0]["objects"], {})
            self.assertIn("title", native["pages"][1]["objects"])
            self.assertEqual(roundtrip["pages"][0]["role"], "shared")
            self.assertEqual(roundtrip["pages"][0]["name"], "page 0")
            self.assertEqual(roundtrip["pages"][1]["role"], "page")

    def test_validate_rejects_missing_target(self):
        fixture = TESTS_DIR / "fixtures" / "invalid-target.layout.json"
        result = run_cli("validate", str(fixture), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("target 'missingField'", result.stderr)
        self.assertIn("submitButton", result.stderr)

    def test_validate_rejects_forward_reference_cycle(self):
        fixture = TESTS_DIR / "fixtures" / "cycle.layout.json"
        result = run_cli("validate", str(fixture), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must reference an earlier element", result.stderr)
        self.assertIn("first", result.stderr)

    def test_validate_all_rules_passes_for_shared_page_fixture(self):
        fixture = TESTS_DIR / "fixtures" / "shared-page.layout.json"
        result = run_cli("validate", str(fixture), "--all-rules")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Validation passed", result.stdout)

    def test_validate_shared_page_rule_fails_for_single_page_native_form(self):
        fixture = NATIVE_FIXTURES_DIR / "basic.form.4DForm"
        result = run_cli("validate", str(fixture), "--rule", "shared_page_required", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("shared_page_required", result.stderr)
        self.assertIn("at least 2 pages", result.stderr)

    def test_validate_no_overlap_can_be_ignored(self):
        fixture = TESTS_DIR / "fixtures" / "overlap-ignored.layout.json"
        result = run_cli("validate", str(fixture), "--rule", "no_overlap")
        self.assertEqual(result.returncode, 0)
        self.assertIn("no_overlap", result.stdout)

    def test_figma_to_layout_requires_page_selection_for_multi_page_file(self):
        fixture = FIGMA_FIXTURES_DIR / "multi-page-file.json"
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "figma.layout.json"
            result = run_cli("figma-to-layout", str(fixture), str(output), check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("multiple pages", result.stderr)
            self.assertIn("Auth (1:1)", result.stderr)
            self.assertIn("Settings (1:2)", result.stderr)

    def test_figma_to_layout_imports_selected_page(self):
        fixture = FIGMA_FIXTURES_DIR / "multi-page-file.json"
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "figma.layout.json"
            run_cli("figma-to-layout", str(fixture), str(output), "--page", "Auth")
            layout = load_json(output)
            self.assertEqual(layout["meta"]["sourceFigma"]["pageName"], "Auth")
            self.assertEqual(layout["form"]["windowTitle"], "Auth")
            self.assertEqual(layout["pages"][0]["role"], "shared")
            self.assertEqual(layout["pages"][1]["role"], "page")
            self.assertEqual(len(layout["pages"][1]["elements"]), 5)
            self.assertEqual(layout["pages"][1]["elements"][0]["id"], "Canvas_Title")
            self.assertEqual(layout["pages"][1]["elements"][0]["layout"]["frame"]["top"], 0)
            self.assertEqual(layout["pages"][1]["elements"][1]["id"], "Email_Label")
            self.assertEqual(layout["pages"][1]["elements"][1]["layout"]["frame"]["left"], 70)
            self.assertEqual(layout["pages"][1]["elements"][2]["type"], "rectangle")
            self.assertEqual(layout["pages"][1]["elements"][3]["type"], "line")

    def test_figma_to_layout_imports_selected_subtree(self):
        fixture = FIGMA_FIXTURES_DIR / "multi-page-file.json"
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "figma-node.layout.json"
            run_cli(
                "figma-to-layout",
                str(fixture),
                str(output),
                "--page",
                "Auth",
                "--node",
                "Login Form",
            )
            layout = load_json(output)
            self.assertEqual(layout["meta"]["sourceFigma"]["nodeName"], "Login Form")
            self.assertEqual(layout["form"]["windowTitle"], "Login Form")
            self.assertEqual(layout["form"]["width"], 320)
            self.assertEqual(layout["form"]["height"], 220)
            self.assertEqual(len(layout["pages"][1]["elements"]), 4)
            self.assertEqual(layout["pages"][1]["elements"][0]["layout"]["frame"]["top"], 24)
            self.assertEqual(layout["pages"][1]["elements"][0]["layout"]["frame"]["left"], 20)
            self.assertEqual(layout["pages"][1]["elements"][1]["props"]["cornerRadius"], 6)


if __name__ == "__main__":
    unittest.main()
