import re
import subprocess
import tempfile
import unittest
from pathlib import Path

# plugin root = skills/obsidian-daily-note/tests/ -> up 3
PLUGIN_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TEMPLATE = PLUGIN_ROOT / "templates" / "raw-note.md"
SCRIPT = PLUGIN_ROOT / "skills" / "obsidian-daily-note" / "scripts" / "create_daily_note.py"

WORK_WORDS = re.compile(r"teams|task tracker|outlook", re.IGNORECASE)


class TestDefaultTemplate(unittest.TestCase):
    def test_template_exists(self):
        self.assertTrue(DEFAULT_TEMPLATE.exists(), f"missing {DEFAULT_TEMPLATE}")

    def test_template_has_no_work_specific_wording(self):
        text = DEFAULT_TEMPLATE.read_text(encoding="utf-8")
        # The neutrality rule covers the human-facing routine/section content,
        # not the Agenda dataviewjs block's meeting-platform detection regex or
        # the explanatory HTML comment (which names calendar sources as examples).
        # Strip fenced code blocks and HTML comments before scanning.
        prose = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        prose = re.sub(r"<!--.*?-->", "", prose, flags=re.DOTALL)
        self.assertIsNone(
            WORK_WORDS.search(prose),
            "default template routine/sections must be work-neutral",
        )

    def test_template_has_required_sections(self):
        text = DEFAULT_TEMPLATE.read_text(encoding="utf-8")
        for heading in ("## 📅 Agenda", "## ✅ Tasks", "## 📝 Meeting notes", "## 📥 Captures"):
            self.assertIn(heading, text)

    def test_template_renders_cleanly_on_a_weekday(self):
        with tempfile.TemporaryDirectory() as tmp:
            v = Path(tmp)
            (v / "templates").mkdir()
            (v / "input").mkdir()
            (v / "templates" / "raw-note.md").write_text(
                DEFAULT_TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8"
            )
            # 2026-07-06 is a Monday -> routine block must render.
            out = subprocess.run(
                ["python3", str(SCRIPT), "2026-07-06", "--vault", str(v)],
                capture_output=True, text=True,
            )
            self.assertEqual(out.returncode, 0, out.stderr)
            note = (v / "input" / "2026-07-06.md").read_text(encoding="utf-8")
            self.assertNotIn("<%", note)
            self.assertIn("date: 2026-07-06", note)
            self.assertIn("## ✅ Daily routine", note)

    def test_template_omits_routine_on_weekend(self):
        with tempfile.TemporaryDirectory() as tmp:
            v = Path(tmp)
            (v / "templates").mkdir()
            (v / "input").mkdir()
            (v / "templates" / "raw-note.md").write_text(
                DEFAULT_TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8"
            )
            # 2026-07-04 is a Saturday -> routine block must be dropped.
            subprocess.run(
                ["python3", str(SCRIPT), "2026-07-04", "--vault", str(v)],
                capture_output=True, text=True, check=True,
            )
            note = (v / "input" / "2026-07-04.md").read_text(encoding="utf-8")
            self.assertNotIn("## ✅ Daily routine", note)


if __name__ == "__main__":
    unittest.main()
