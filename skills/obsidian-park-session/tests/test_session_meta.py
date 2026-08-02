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


if __name__ == "__main__":
    unittest.main()
