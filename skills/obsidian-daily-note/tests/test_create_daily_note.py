import datetime
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "create_daily_note.py"
_spec = importlib.util.spec_from_file_location("create_daily_note", _SCRIPT)
cdn = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cdn)


class TestTaskHelpers(unittest.TestCase):
    def test_open_task_is_unfinished(self):
        self.assertTrue(cdn.is_unfinished("- [ ] Draft proposal"))

    def test_postponed_with_due_is_unfinished(self):
        self.assertTrue(cdn.is_unfinished("- [ ] Reply  [due:: 2026-06-30]"))

    def test_done_is_not_unfinished(self):
        self.assertFalse(cdn.is_unfinished("- [x] Send invoice"))

    def test_canceled_is_not_unfinished(self):
        self.assertFalse(cdn.is_unfinished("- [ ] Old idea  [status:: canceled]"))

    def test_indented_subtask_is_not_top_level(self):
        self.assertFalse(cdn.is_unfinished("  - [ ] sub item"))

    def test_normalize_strips_checkbox_and_fields(self):
        self.assertEqual(
            cdn.normalize_task_text("- [ ] Reply  to Vendor  [due:: 2026-06-30] [from:: 2026-06-01]"),
            "reply to vendor",
        )

    def test_stamp_adds_from_when_absent(self):
        self.assertEqual(
            cdn.stamp_provenance("- [ ] Task", "2026-06-21"),
            "- [ ] Task  [from:: 2026-06-21]",
        )

    def test_stamp_preserves_existing_from(self):
        line = "- [ ] Task  [from:: 2026-06-01]"
        self.assertEqual(cdn.stamp_provenance(line, "2026-06-21"), line)


class TestTasksSection(unittest.TestCase):
    NOTE = (
        "---\ndate: 2026-06-21\n---\n\n"
        "## 📅 Agenda\n\nstuff\n\n"
        "## ✅ Tasks\n\n"
        "- [ ] open one\n"
        "- [x] done one\n"
        "- [ ] canceled one  [status:: canceled]\n\n"
        "## 📝 Meeting notes\n\nnotes\n"
    )

    def test_parse_returns_section_lines_only(self):
        lines = cdn.parse_tasks_section(self.NOTE)
        self.assertIn("- [ ] open one", lines)
        self.assertIn("- [x] done one", lines)
        self.assertNotIn("stuff", lines)
        self.assertNotIn("notes", lines)

    def test_parse_missing_heading_returns_empty(self):
        self.assertEqual(cdn.parse_tasks_section("# nothing here\n"), [])

    def test_insert_places_tasks_under_heading(self):
        out = cdn.insert_tasks_into_section(self.NOTE, ["- [ ] carried  [from:: 2026-06-20]"])
        self.assertIn("## ✅ Tasks\n\n- [ ] carried  [from:: 2026-06-20]\n", out)
        # original following section is preserved and still separated by a blank line
        self.assertIn("\n\n## 📝 Meeting notes", out)

    def test_insert_empty_is_noop(self):
        self.assertEqual(cdn.insert_tasks_into_section(self.NOTE, []), self.NOTE)

    def test_insert_without_heading_raises(self):
        with self.assertRaises(ValueError):
            cdn.insert_tasks_into_section("no heading\n", ["- [ ] x"])


class TestPriorNote(unittest.TestCase):
    def _vault(self, tmp):
        v = Path(tmp)
        (v / "input").mkdir()
        (v / "raw" / "2026-06-18").mkdir(parents=True)
        (v / "raw" / "2026-06-01").mkdir(parents=True)  # no daily-note.md here
        (v / "input" / "2026-06-20.md").write_text("x", encoding="utf-8")
        (v / "raw" / "2026-06-18" / "daily-note.md").write_text("x", encoding="utf-8")
        (v / "raw" / "2026-06-01" / "other.md").write_text("x", encoding="utf-8")
        return v

    def test_iter_finds_input_and_raw_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            v = self._vault(tmp)
            notes = cdn.iter_daily_notes(v)
            self.assertEqual(
                set(notes), {datetime.date(2026, 6, 20), datetime.date(2026, 6, 18)}
            )

    def test_find_prior_returns_most_recent_before_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            v = self._vault(tmp)
            d, p = cdn.find_prior_daily_note(v, datetime.date(2026, 6, 22))
            self.assertEqual(d, datetime.date(2026, 6, 20))

    def test_find_prior_excludes_target_and_future(self):
        with tempfile.TemporaryDirectory() as tmp:
            v = self._vault(tmp)
            d, p = cdn.find_prior_daily_note(v, datetime.date(2026, 6, 20))
            self.assertEqual(d, datetime.date(2026, 6, 18))

    def test_find_prior_none_when_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            v = Path(tmp)
            (v / "input").mkdir()
            self.assertIsNone(cdn.find_prior_daily_note(v, datetime.date(2026, 6, 22)))


class TestCarryOver(unittest.TestCase):
    PRIOR = (
        "## ✅ Tasks\n\n"
        "- [ ] keep me\n"
        "- [ ] also keep  [due:: 2026-07-01]\n"
        "- [x] done\n"
        "- [ ] canceled  [status:: canceled]\n\n"
        "## 📝 Meeting notes\n"
    )

    def test_select_carries_open_and_postponed_only(self):
        carried = cdn.select_carry_tasks(self.PRIOR, "2026-06-21", set())
        self.assertTrue(any("keep me" in c for c in carried))
        self.assertTrue(any("also keep" in c for c in carried))
        self.assertFalse(any("done" in c for c in carried))
        self.assertFalse(any("canceled" in c for c in carried))
        self.assertEqual(len(carried), 2)

    def test_select_stamps_provenance(self):
        carried = cdn.select_carry_tasks("## ✅ Tasks\n\n- [ ] x\n", "2026-06-21", set())
        self.assertEqual(carried, ["- [ ] x  [from:: 2026-06-21]"])

    def test_select_dedups_against_existing(self):
        existing = {"keep me"}
        carried = cdn.select_carry_tasks(self.PRIOR, "2026-06-21", existing)
        self.assertFalse(any("keep me" in c for c in carried))
        self.assertEqual(len(carried), 1)


class TestEndToEnd(unittest.TestCase):
    def test_script_carries_tasks_into_new_note(self):
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            v = Path(tmp)
            (v / "input").mkdir()
            (v / "templates").mkdir()
            # Minimal template exercising frontmatter date + Tasks heading.
            (v / "templates" / "raw-note.md").write_text(
                '---\ndate: <% tp.date.now("YYYY-MM-DD", 0, tp.file.title, "YYYY-MM-DD") %>\n'
                "source: personal\ntags: []\n---\n\n"
                "## ✅ Tasks\n\n"
                "## 📝 Meeting notes\n",
                encoding="utf-8",
            )
            (v / "input" / "2026-06-20.md").write_text(
                "## ✅ Tasks\n\n- [ ] carry this\n- [x] not this\n\n## 📝 Meeting notes\n",
                encoding="utf-8",
            )
            out = subprocess.run(
                ["python3", str(_SCRIPT), "2026-06-22", "--vault", str(v)],
                capture_output=True, text=True,
            )
            self.assertEqual(out.returncode, 0, out.stderr)
            note = (v / "input" / "2026-06-22.md").read_text(encoding="utf-8")
            self.assertIn("- [ ] carry this  [from:: 2026-06-20]", note)
            self.assertNotIn("not this", note)
            self.assertIn("date: 2026-06-22", note)


class TestRecollect(unittest.TestCase):
    def _vault(self, tmp):
        v = Path(tmp)
        (v / "input").mkdir()
        (v / "templates").mkdir()
        # Template required for main() to proceed (even in --recollect mode).
        (v / "templates" / "raw-note.md").write_text("dummy", encoding="utf-8")
        # Most-recent prior note (2026-06-20) — handled by normal carry-over, excluded.
        (v / "input" / "2026-06-20.md").write_text(
            "## ✅ Tasks\n\n- [ ] recent task\n\n## x\n", encoding="utf-8"
        )
        # Older notes — recollect candidates.
        (v / "input" / "2026-06-10.md").write_text(
            "## ✅ Tasks\n\n- [ ] old open\n- [x] old done\n\n## x\n", encoding="utf-8"
        )
        (v / "input" / "2026-06-05.md").write_text(
            "## ✅ Tasks\n\n- [ ] older one  [from:: 2026-06-01]\n\n## x\n",
            encoding="utf-8",
        )
        return v

    def test_collects_only_older_than_most_recent(self):
        with tempfile.TemporaryDirectory() as tmp:
            v = self._vault(tmp)
            cands = cdn.collect_recollect_candidates(v, datetime.date(2026, 6, 22))
            texts = [c["line"] for c in cands]
            self.assertTrue(any("old open" in t for t in texts))
            self.assertTrue(any("older one" in t for t in texts))
            self.assertFalse(any("recent task" in t for t in texts))
            self.assertFalse(any("old done" in t for t in texts))

    def test_age_uses_existing_from_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            v = self._vault(tmp)
            cands = cdn.collect_recollect_candidates(v, datetime.date(2026, 6, 22))
            older = next(c for c in cands if "older one" in c["line"])
            self.assertEqual(older["origin"], "2026-06-01")
            self.assertEqual(older["age"], 21)  # 2026-06-22 minus 2026-06-01

    def test_sorted_oldest_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            v = self._vault(tmp)
            cands = cdn.collect_recollect_candidates(v, datetime.date(2026, 6, 22))
            ages = [c["age"] for c in cands]
            self.assertEqual(ages, sorted(ages, reverse=True))

    def test_recollect_cli_prints_and_creates_nothing(self):
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            v = self._vault(tmp)
            out = subprocess.run(
                ["python3", str(_SCRIPT), "2026-06-22", "--recollect", "--vault", str(v)],
                capture_output=True, text=True,
            )
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertIn("older one", out.stdout)
            self.assertFalse((v / "input" / "2026-06-22.md").exists())


if __name__ == "__main__":
    unittest.main()
