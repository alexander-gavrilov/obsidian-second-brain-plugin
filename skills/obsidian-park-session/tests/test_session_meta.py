import importlib.util
import unittest
from pathlib import Path
import tempfile

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "session_meta.py"
_spec = importlib.util.spec_from_file_location("session_meta", _SCRIPT)
sm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sm)


class TestCwdSlug(unittest.TestCase):
    def test_plain_path(self):
        self.assertEqual(
            sm.cwd_slug("/home/alexander/projects/obsidian-second-brain-plugin"),
            "-home-alexander-projects-obsidian-second-brain-plugin",
        )

    def test_dots_become_dashes(self):
        self.assertEqual(
            sm.cwd_slug("/home/alexander/.tmp-move/projects-folder"),
            "-home-alexander--tmp-move-projects-folder",
        )

    def test_trailing_slash_ignored(self):
        self.assertEqual(sm.cwd_slug("/tmp/"), "-tmp")


class TestFindTranscript(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def _make(self, slug, name, mtime=None):
        d = self.root / slug
        d.mkdir(parents=True, exist_ok=True)
        p = d / name
        p.write_text("{}\n", encoding="utf-8")
        if mtime is not None:
            import os
            os.utime(p, (mtime, mtime))
        return p

    def test_finds_by_session_id_across_projects(self):
        self._make("-a-b", "sess-one.jsonl")
        target = self._make("-c-d", "sess-two.jsonl")
        self.assertEqual(
            sm.find_transcript("sess-two", "/a/b", self.root), target
        )

    def test_falls_back_to_newest_in_cwd_project(self):
        self._make("-a-b", "old.jsonl", mtime=1000)
        newest = self._make("-a-b", "new.jsonl", mtime=2000)
        self.assertEqual(sm.find_transcript(None, "/a/b", self.root), newest)

    def test_raises_when_project_dir_missing(self):
        with self.assertRaises(sm.TranscriptNotFound):
            sm.find_transcript(None, "/nowhere", self.root)

    def test_raises_when_session_id_unknown(self):
        self._make("-a-b", "sess-one.jsonl")
        with self.assertRaises(sm.TranscriptNotFound):
            sm.find_transcript("missing", "/a/b", self.root)


import json


def _write_transcript(path, records):
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")


SAMPLE = [
    {"type": "mode", "mode": "normal", "sessionId": "sess-1"},
    {"type": "ai-title", "aiTitle": "Park chat sessions", "sessionId": "sess-1"},
    {
        "type": "user", "sessionId": "sess-1", "cwd": "/work/repo",
        "gitBranch": "master", "timestamp": "2026-08-02T19:00:00.000Z",
        "message": {"role": "user", "content": "build me a thing"},
    },
    {
        "type": "assistant", "sessionId": "sess-1", "cwd": "/work/repo",
        "gitBranch": "master", "timestamp": "2026-08-02T19:05:00.000Z",
        "message": {"role": "assistant", "model": "claude-opus-5", "content": []},
    },
    {
        "type": "user", "sessionId": "sess-1", "cwd": "/work/repo",
        "gitBranch": "wip/thing", "timestamp": "2026-08-02T19:10:00.000Z",
        "message": {"role": "user", "content": [{"type": "tool_result", "content": "ok"}]},
    },
    {
        "type": "assistant", "sessionId": "sess-1", "cwd": "/work/repo",
        "gitBranch": "wip/thing", "timestamp": "2026-08-02T19:30:00.000Z",
        "message": {"role": "assistant", "model": "claude-sonnet-5", "content": []},
    },
]


class TestRealUserTurn(unittest.TestCase):
    def test_plain_text_turn_counts(self):
        self.assertTrue(sm.is_real_user_turn(
            {"type": "user", "message": {"content": "hello"}}))

    def test_meta_turn_does_not_count(self):
        self.assertFalse(sm.is_real_user_turn(
            {"type": "user", "isMeta": True, "message": {"content": "hello"}}))

    def test_sidechain_turn_does_not_count(self):
        self.assertFalse(sm.is_real_user_turn(
            {"type": "user", "isSidechain": True, "message": {"content": "hello"}}))

    def test_tool_result_does_not_count(self):
        self.assertFalse(sm.is_real_user_turn({
            "type": "user",
            "message": {"content": [{"type": "tool_result", "content": "ok"}]},
        }))

    def test_slash_command_wrapper_does_not_count(self):
        self.assertFalse(sm.is_real_user_turn(
            {"type": "user", "message": {"content": "<command-name>/clear</command-name>"}}))

    def test_assistant_record_does_not_count(self):
        self.assertFalse(sm.is_real_user_turn(
            {"type": "assistant", "message": {"content": "hi"}}))


class TestHumanizeDuration(unittest.TestCase):
    def test_seconds(self):
        self.assertEqual(sm.humanize_duration(45), "45s")

    def test_minutes(self):
        self.assertEqual(sm.humanize_duration(28 * 60), "28m")

    def test_hours_and_minutes(self):
        self.assertEqual(sm.humanize_duration(3 * 3600 + 4 * 60), "3h 4m")

    def test_zero(self):
        self.assertEqual(sm.humanize_duration(0), "0s")


class TestParseTranscript(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "sess-1.jsonl"
        self.addCleanup(self._tmp.cleanup)
        _write_transcript(self.path, SAMPLE)
        self.meta = sm.parse_transcript(self.path)

    def test_session_id(self):
        self.assertEqual(self.meta["session_id"], "sess-1")

    def test_cwd(self):
        self.assertEqual(self.meta["cwd"], "/work/repo")

    def test_branches_in_order_of_appearance(self):
        self.assertEqual(self.meta["git_branches"], ["master", "wip/thing"])

    def test_models_in_order_of_first_use(self):
        self.assertEqual(self.meta["models"], ["claude-opus-5", "claude-sonnet-5"])

    def test_start_and_end(self):
        self.assertEqual(self.meta["started_at"], "2026-08-02T19:00:00Z")
        self.assertEqual(self.meta["ended_at"], "2026-08-02T19:30:00Z")

    def test_duration(self):
        self.assertEqual(self.meta["duration"], "30m")

    def test_user_turn_count_excludes_tool_results(self):
        self.assertEqual(self.meta["user_turn_count"], 1)

    def test_title(self):
        self.assertEqual(self.meta["title"], "Park chat sessions")

    def test_transcript_path(self):
        self.assertEqual(self.meta["transcript_path"], str(self.path))


class TestParseTranscriptDegraded(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_malformed_lines_are_skipped(self):
        path = self.dir / "sess-2.jsonl"
        with path.open("w", encoding="utf-8") as fh:
            fh.write("not json at all\n")
            fh.write(json.dumps(SAMPLE[3]) + "\n")
            fh.write("{ broken\n")
        meta = sm.parse_transcript(path)
        self.assertEqual(meta["models"], ["claude-opus-5"])

    def test_missing_fields_are_null(self):
        path = self.dir / "sess-3.jsonl"
        _write_transcript(path, [{"type": "mode", "mode": "normal"}])
        meta = sm.parse_transcript(path)
        self.assertIsNone(meta["title"])
        self.assertIsNone(meta["started_at"])
        self.assertIsNone(meta["duration"])
        self.assertEqual(meta["models"], [])
        self.assertEqual(meta["user_turn_count"], 0)

    def test_session_id_falls_back_to_filename(self):
        path = self.dir / "sess-4.jsonl"
        _write_transcript(path, [{"type": "mode", "mode": "normal"}])
        self.assertEqual(sm.parse_transcript(path)["session_id"], "sess-4")


class TestMain(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        (self.root / "-work-repo").mkdir(parents=True)
        _write_transcript(self.root / "-work-repo" / "sess-1.jsonl", SAMPLE)

    def test_prints_json_and_returns_zero(self):
        import contextlib, io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = sm.main(["--cwd", "/work/repo", "--projects-root", str(self.root)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(buf.getvalue())["session_id"], "sess-1")

    def test_missing_transcript_returns_nonzero(self):
        import contextlib, io
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = sm.main(["--cwd", "/nope", "--projects-root", str(self.root)])
        self.assertNotEqual(code, 0)
        self.assertIn("transcript", err.getvalue().lower())


if __name__ == "__main__":
    unittest.main()
