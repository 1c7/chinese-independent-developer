import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT_PATH = Path(__file__).parents[2] / ".github" / "scripts" / "check_links.py"

GOOD_LINE = "* :white_check_mark: [KinetMagicDisk](https://apps.apple.com/cn/app/id6813423397)：Mac 磁盘清理"
DEAD_LINE = "* :white_check_mark: [KinetTask](https://apps.apple.com/cn/app/id6780944289)：端侧 AI 任务管理"
HEADER = "#### phinn - [Github](https://github.com/phinn)"


def load_script():
    spec = importlib.util.spec_from_file_location("check_links", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CheckLinksTests(unittest.TestCase):
    def setUp(self):
        self.script = load_script()

    def test_app_store_target_parses_region_and_id(self):
        self.assertEqual(
            self.script.app_store_target("https://apps.apple.com/cn/app/id6813423397"),
            ("cn", "6813423397"),
        )
        self.assertIsNone(self.script.app_store_target("https://example.com/app"))

    def test_app_store_link_available_in_china_passes(self):
        with patch.object(self.script, "lookup_app_store", return_value={"trackName": "X"}):
            self.assertIsNone(self.script.check_url("https://apps.apple.com/cn/app/id1"))

    def test_app_store_link_missing_in_china_reports_other_regions(self):
        def fake_lookup(app_id, country):
            return {"trackName": "X"} if country == "us" else None

        with patch.object(self.script, "lookup_app_store", side_effect=fake_lookup):
            reason = self.script.check_url("https://apps.apple.com/cn/app/id2")

        self.assertIn("CN 区查不到", reason)
        self.assertIn("US", reason)

    def test_app_store_link_missing_everywhere(self):
        with patch.object(self.script, "lookup_app_store", return_value=None):
            reason = self.script.check_url("https://apps.apple.com/cn/app/id3")

        self.assertIn("App Store 查不到", reason)

    def test_lookup_failure_is_not_treated_as_dead_link(self):
        with patch.object(
            self.script, "lookup_app_store", side_effect=RuntimeError("rate limited")
        ):
            self.assertIsNone(self.script.check_url("https://apps.apple.com/cn/app/id4"))

    def test_http_404_is_dead_link(self):
        with patch.object(self.script, "_fetch", return_value=404):
            self.assertIn("404", self.script.check_url("https://dead.example.com"))

    def test_http_403_is_treated_as_blocked_not_dead(self):
        with patch.object(self.script, "_fetch", return_value=403):
            self.assertIsNone(self.script.check_url("https://strict.example.com"))

    def test_http_unreachable_is_dead_link(self):
        with patch.object(self.script, "_fetch", return_value=None):
            self.assertEqual(self.script.check_url("https://down.example.com"), "无法连接")

    def test_filter_entry_drops_only_broken_lines(self):
        entry = "\n".join([HEADER, GOOD_LINE, DEAD_LINE])

        def fake_lookup(app_id, country):
            return {"trackName": "OK"} if app_id == "6813423397" else None

        with patch.object(self.script, "lookup_app_store", side_effect=fake_lookup):
            kept, problems = self.script.filter_entry(entry)

        self.assertIn(HEADER, kept)
        self.assertIn(GOOD_LINE, kept)
        self.assertNotIn(DEAD_LINE, kept)
        self.assertEqual(len(problems), 1)
        self.assertEqual(problems[0].label, "KinetTask")

    def test_format_problems_lists_reasons(self):
        problem = self.script.LinkProblem(
            url="https://apps.apple.com/cn/app/id5",
            label="KinetTask",
            reason="CN 区查不到这个 App（US 区在售）",
        )

        text = self.script.format_problems([problem])

        self.assertIn("补好链接后回复", text)
        self.assertIn("CN 区查不到这个 App", text)

    def test_format_problems_empty_when_no_problem(self):
        self.assertEqual(self.script.format_problems([]), "")


if __name__ == "__main__":
    unittest.main()
