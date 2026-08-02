# obsidian-park-session Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an `obsidian-park-session` skill that summarizes the current Claude Code session into an Obsidian vault note carrying the session id, models used, working folder, and start/end times.

**Architecture:** A stdlib-only Python script (`scripts/session_meta.py`) locates and parses the session's transcript JSONL under `~/.claude/projects/` and prints the facts as a single JSON object. `SKILL.md` holds the judgment work — resolving the vault, summarizing the conversation, writing the note and a `log.md` line. This mirrors the existing `obsidian-daily-note` skill's script + prose split.

**Tech Stack:** Python 3 standard library only (`json`, `argparse`, `datetime`, `pathlib`, `re`). Tests use `unittest`, loaded via `importlib` exactly as `skills/obsidian-daily-note/tests/` does.

Spec: `docs/superpowers/specs/2026-08-02-park-session-design.md`

## Global Constraints

- **No third-party dependencies.** Python standard library only, matching `skills/obsidian-daily-note/scripts/create_daily_note.py`.
- **The script never writes.** `session_meta.py` reads the transcript and prints JSON to stdout. Nothing else.
- **The skill writes exactly two things:** the session note and one `log.md` line. Never wiki pages, never `index.md`.
- **Unknown fields are `null` in the script's JSON**, and the literal string `unknown` in the note's front matter. Absent is never the same as unknown.
- **Malformed JSONL lines are skipped, never fatal.**
- **New skill directory:** `skills/obsidian-park-session/` containing `SKILL.md`, `scripts/session_meta.py`, `tests/test_session_meta.py`, `evals/evals.json`.
- Run tests with `python3 -m unittest discover -s skills/obsidian-park-session/tests -v` from the repo root.

---

### Task 1: Transcript discovery

Locate the transcript file for a session. Two paths: an explicit session id (glob every project directory for `<session-id>.jsonl`), or no session id (derive the project directory from the working directory and take the most recently modified transcript).

The slug rule is verified against real directories on this machine: `/home/alexander/projects/obsidian-second-brain-plugin` → `-home-alexander-projects-obsidian-second-brain-plugin`, and `/home/alexander/.tmp-move/projects-folder` → `-home-alexander--tmp-move-projects-folder`. Both `/` and `.` become `-`.

**Files:**
- Create: `skills/obsidian-park-session/scripts/session_meta.py`
- Test: `skills/obsidian-park-session/tests/test_session_meta.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `cwd_slug(cwd: str | Path) -> str`
  - `find_transcript(session_id: str | None, cwd: str | Path, projects_root: Path) -> Path` — raises `TranscriptNotFound` (a subclass of `Exception`) when nothing matches.
  - `TranscriptNotFound` exception class.

- [ ] **Step 1: Write the failing test**

Create `skills/obsidian-park-session/tests/test_session_meta.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest discover -s skills/obsidian-park-session/tests -v`
Expected: FAIL — `FileNotFoundError` / import error, because `scripts/session_meta.py` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Create `skills/obsidian-park-session/scripts/session_meta.py`:

```python
#!/usr/bin/env python3
"""Extract factual metadata about a Claude Code session from its transcript.

Claude Code writes one JSONL transcript per session to
``~/.claude/projects/<cwd-slug>/<session-id>.jsonl``. This script locates that
file and prints the session's facts — id, working directory, git branches,
models used, start and end times, duration, user turn count, title — as a
single JSON object on stdout.

It is read-only by design: the ``obsidian-park-session`` skill owns all writing.
"""
from __future__ import annotations

from pathlib import Path

DEFAULT_PROJECTS_ROOT = Path.home() / ".claude" / "projects"


class TranscriptNotFound(Exception):
    """No transcript file could be located for the requested session."""


def cwd_slug(cwd) -> str:
    """Claude Code's project-directory name for a working directory.

    Both path separators and dots collapse to dashes:
    ``/home/me/.config/app`` -> ``-home-me--config-app``.
    """
    text = str(cwd).rstrip("/")
    return text.replace("/", "-").replace(".", "-")


def find_transcript(session_id, cwd, projects_root=DEFAULT_PROJECTS_ROOT) -> Path:
    """Locate a session transcript.

    With a session id, search every project directory for ``<id>.jsonl`` — the
    id is unique, so the working directory does not need to match. Without one,
    fall back to the most recently modified transcript in the project directory
    for ``cwd``, which is the live session.
    """
    projects_root = Path(projects_root)
    if session_id:
        matches = sorted(projects_root.glob(f"*/{session_id}.jsonl"))
        if not matches:
            raise TranscriptNotFound(
                f"No transcript named {session_id}.jsonl under {projects_root}"
            )
        return matches[0]

    project_dir = projects_root / cwd_slug(cwd)
    candidates = list(project_dir.glob("*.jsonl"))
    if not candidates:
        raise TranscriptNotFound(f"No transcripts in {project_dir}")
    return max(candidates, key=lambda p: p.stat().st_mtime)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest discover -s skills/obsidian-park-session/tests -v`
Expected: PASS — 7 tests.

- [ ] **Step 5: Commit**

```bash
git add skills/obsidian-park-session/scripts/session_meta.py skills/obsidian-park-session/tests/test_session_meta.py
git commit -m "feat: locate Claude Code session transcripts for park-session"
```

---

### Task 2: Parse the transcript into metadata JSON

Parse the located transcript and emit the JSON object the skill consumes.

Record shapes verified against real transcripts:
- Every record has `type`. Interesting types: `user`, `assistant`, `ai-title`.
- `assistant` and `user` records carry `timestamp`, `cwd`, `sessionId`, `gitBranch`.
- The model lives at `message.model` on `assistant` records.
- The title lives at `aiTitle` on the single `ai-title` record.
- `user` records include tool results and injected content. A **real** user turn is one that is not `isMeta`, not `isSidechain`, whose content is not a `tool_result` block list, and whose text does not start with a harness wrapper (`<command-name>`, `<local-command-stdout>`, `<local-command-caveat>`).
- Timestamps look like `2026-08-02T19:12:29.863Z`.

**Files:**
- Modify: `skills/obsidian-park-session/scripts/session_meta.py`
- Test: `skills/obsidian-park-session/tests/test_session_meta.py`

**Interfaces:**
- Consumes: `find_transcript`, `TranscriptNotFound` from Task 1.
- Produces:
  - `is_real_user_turn(record: dict) -> bool`
  - `humanize_duration(seconds: float) -> str`
  - `parse_transcript(path: Path) -> dict` — the metadata dict with keys `session_id`, `cwd`, `git_branches`, `models`, `started_at`, `ended_at`, `duration`, `user_turn_count`, `title`, `transcript_path`
  - `main(argv=None) -> int` — CLI accepting `--session-id`, `--cwd`, `--projects-root`

- [ ] **Step 1: Write the failing tests**

Append to `skills/obsidian-park-session/tests/test_session_meta.py` (above the `if __name__` block):

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest discover -s skills/obsidian-park-session/tests -v`
Expected: FAIL — `AttributeError: module 'session_meta' has no attribute 'is_real_user_turn'` and similar for the other new names.

- [ ] **Step 3: Write the implementation**

Add to `skills/obsidian-park-session/scripts/session_meta.py` — extend the imports at the top to:

```python
from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path
```

Then append below `find_transcript`:

```python
# User records that are not really the user talking: harness-injected content,
# slash-command bookkeeping, and local command output.
_WRAPPER_PREFIXES = (
    "<command-name>",
    "<local-command-stdout>",
    "<local-command-caveat>",
)


def is_real_user_turn(record) -> bool:
    """True for a record that represents the human actually saying something.

    Excludes tool results, subagent (sidechain) traffic, harness-injected meta
    records, and the wrapper records slash commands leave behind.
    """
    if record.get("type") != "user":
        return False
    if record.get("isMeta") or record.get("isSidechain"):
        return False
    content = (record.get("message") or {}).get("content")
    if isinstance(content, list):
        return not any(
            isinstance(block, dict) and block.get("type") == "tool_result"
            for block in content
        )
    if isinstance(content, str):
        stripped = content.lstrip()
        return bool(stripped) and not stripped.startswith(_WRAPPER_PREFIXES)
    return False


def _parse_timestamp(raw: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(
        datetime.timezone.utc
    )


def humanize_duration(seconds: float) -> str:
    """Compact duration: ``45s``, ``28m``, ``3h 4m``."""
    total = int(seconds)
    if total < 60:
        return f"{total}s"
    minutes, _ = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def _append_unique(items: list, value) -> None:
    if value and value not in items:
        items.append(value)


def parse_transcript(path) -> dict:
    """Read a transcript JSONL and return its session facts.

    Fields that cannot be determined come back as ``None`` (or an empty list)
    rather than being omitted, so callers can tell "unknown" from "absent".
    Unparseable lines are skipped.
    """
    path = Path(path)
    session_id = None
    cwd = None
    title = None
    branches: list = []
    models: list = []
    timestamps: list = []
    user_turns = 0

    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if not isinstance(record, dict):
                continue

            session_id = session_id or record.get("sessionId")
            cwd = cwd or record.get("cwd")
            if record.get("type") == "ai-title" and record.get("aiTitle"):
                title = record["aiTitle"]
            _append_unique(branches, record.get("gitBranch"))

            message = record.get("message")
            if isinstance(message, dict):
                _append_unique(models, message.get("model"))

            stamp = record.get("timestamp")
            if stamp:
                try:
                    timestamps.append(_parse_timestamp(stamp))
                except ValueError:
                    pass

            if is_real_user_turn(record):
                user_turns += 1

    started = min(timestamps) if timestamps else None
    ended = max(timestamps) if timestamps else None

    return {
        "session_id": session_id or path.stem,
        "cwd": cwd,
        "git_branches": branches,
        "models": models,
        "started_at": started.strftime("%Y-%m-%dT%H:%M:%SZ") if started else None,
        "ended_at": ended.strftime("%Y-%m-%dT%H:%M:%SZ") if ended else None,
        "duration": (
            humanize_duration((ended - started).total_seconds())
            if started and ended
            else None
        ),
        "user_turn_count": user_turns,
        "title": title,
        "transcript_path": str(path),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Print JSON metadata for a Claude Code session transcript."
    )
    parser.add_argument(
        "--session-id",
        default=None,
        help="Session id to look up. Omit to use the newest transcript for --cwd.",
    )
    parser.add_argument(
        "--cwd",
        default=None,
        help="Working directory whose project transcripts to search. "
        "Defaults to the current directory.",
    )
    parser.add_argument(
        "--projects-root",
        default=str(DEFAULT_PROJECTS_ROOT),
        help="Override the ~/.claude/projects location (for testing).",
    )
    args = parser.parse_args(argv)

    cwd = args.cwd or Path.cwd()
    try:
        path = find_transcript(args.session_id, cwd, Path(args.projects_root))
    except TranscriptNotFound as exc:
        print(f"Could not locate a session transcript: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(parse_transcript(path), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest discover -s skills/obsidian-park-session/tests -v`
Expected: PASS — all tests from Tasks 1 and 2.

- [ ] **Step 5: Verify against a real transcript**

Run from the repo root:

```bash
python3 skills/obsidian-park-session/scripts/session_meta.py
```

Expected: a JSON object for this repo's most recent session, with a real `session_id`, `cwd` of `/home/alexander/projects/obsidian-second-brain-plugin`, a non-empty `models` list, and plausible `started_at`/`ended_at`. Spot-check the values against
`~/.claude/projects/-home-alexander-projects-obsidian-second-brain-plugin/<id>.jsonl`. If any field is `null` that should not be, fix the parser and re-run the unit tests before continuing.

- [ ] **Step 6: Commit**

```bash
git add skills/obsidian-park-session/scripts/session_meta.py skills/obsidian-park-session/tests/test_session_meta.py
git commit -m "feat: parse session transcripts into metadata JSON"
```

---

### Task 3: The skill

Write `SKILL.md`, its evals, and the README entry.

**Files:**
- Create: `skills/obsidian-park-session/SKILL.md`
- Create: `skills/obsidian-park-session/evals/evals.json`
- Modify: `README.md` (skill list, after the `obsidian-daily-note` section)

**Interfaces:**
- Consumes: `scripts/session_meta.py` from Tasks 1–2, invoked as
  `python3 <skill_dir>/scripts/session_meta.py` with an optional `--session-id`.
- Produces: the `obsidian-park-session` skill.

- [ ] **Step 1: Write `SKILL.md`**

Create `skills/obsidian-park-session/SKILL.md`:

````markdown
---
name: obsidian-park-session
description: Park the current Claude Code session — summarize what happened into an Obsidian vault note carrying the session id, models used, working folder, and start/end times. Use this skill when the user wants to wrap up and record a working session, says "park this session", "park the chat", "wrap up this session", "save this session", "summarize and park", or "I'm done for today". Writes one session note plus a log entry; it does not create wiki pages.
tools: Read, Write, Edit, Glob, Grep, Bash
---

# Obsidian Park Session

Capture the session you are in right now — a summary of the work plus its
factual metadata — as a note in the vault, so the conversation survives being
cleared.

> **Hard constraint**: This skill writes exactly TWO things: the session note
> under `raw/YYYY-MM-DD/` and one line in `log.md`. Never create or edit wiki
> pages, and never touch `index.md`. Wiki links go into the note's prose as
> links even when the target page does not exist yet — a later
> `obsidian-ingest` run is what turns them into pages.

This skill parks **the current session only**. If the user asks to park an
earlier session, say that only the live session can be parked, and offer to
park this one instead.

## Step 0: Resolve vault

Resolve this once per session — don't ask again mid-session.

1. Check if a local vault exists: does `schema.md` exist in the current working directory?
2. Read `~/.claude/obsidian-second-brain-config.json` (if it exists) to get `global_vault_path`.

**Decision:**
- Local present + global configured → ask once: *"Park this session into the global vault (at `<global_path>`) or local (current directory)?"*
- Local present + no global configured → use local, no prompt
- No local + global configured → use global path silently
- No local + no global → stop: *"No vault found here and no global vault is configured. Run `obsidian-configure` to set one up."*

All file operations below use the resolved vault root.

## Step 1: Read the vault's conventions

Read `schema.md` (only if you haven't already this session) for the vault's
folder layout and front-matter conventions. If it specifies different paths than
the defaults below, follow `schema.md`.

## Step 2: Collect the session metadata

Run the metadata script from this skill's directory. When the plugin is
installed that is
`~/.claude/plugins/marketplaces/obsidian-second-brain/skills/obsidian-park-session`;
when running from a checkout of the plugin repo it is
`skills/obsidian-park-session`. Use whichever exists.

```bash
python3 <skill_dir>/scripts/session_meta.py
```

With no arguments it picks the most recently modified transcript for the current
working directory — that is this session. If you know the session id (the
scratchpad path you were given contains it, as
`/tmp/claude-<uid>/<project-slug>/<session-id>/scratchpad`), pass it explicitly
for certainty:

```bash
python3 <skill_dir>/scripts/session_meta.py --session-id <session-id>
```

The script prints a JSON object with `session_id`, `cwd`, `git_branches`,
`models`, `started_at`, `ended_at`, `duration`, `user_turn_count`, `title`, and
`transcript_path`.

**If the script exits non-zero or a field comes back `null`**, that is expected
in environments without Claude Code transcripts (for example the Gemini CLI
extension). Do not stop. Carry on with what you know — the working directory and
today's date — and record every unavailable field as the literal `unknown`.

## Step 3: Summarize the session

From the conversation you are in — not from the transcript file — write three
sections:

- **What happened** — a narrative of the work done, in a few short paragraphs
  or a tight bullet list. Concrete: what was built, changed, investigated.
- **Decisions** — choices made and the reasoning behind them, including
  rejected alternatives. Skip the heading entirely if no real decisions were made.
- **Resume from here** — open threads, unfinished work, and what to pick up
  next. This is the section that makes the note worth writing; be specific
  enough that a fresh session could continue from it.

While writing, link entities, projects, people, and topics as `[[wiki links]]`
inline in the prose, following the vault's linking conventions from `schema.md`.
Link what the vault would plausibly want a page for — don't link every noun.

## Step 4: Write the session note

Path: `raw/YYYY-MM-DD/session-<slug>.md`, using today's date.

`<slug>` is a kebab-case shortening of the metadata `title` — lowercase, spaces
to dashes, punctuation dropped, roughly 3–6 words. If `title` is `null`, derive
the slug from the topic of your own summary. If the file already exists, append
`-2` (then `-3`, …) rather than overwriting it.

Create the `raw/YYYY-MM-DD/` directory if it does not exist.

```markdown
---
type: session
source: claude-session
session_id: <session_id>
models: [<models, comma-separated>]
cwd: <cwd>
branch: <git_branches, comma-separated in order of appearance>
started: <started_at>
ended: <ended_at>
duration: <duration>
---

# <title>

## What happened

<narrative, with [[wiki links]] inline>

## Decisions

<decisions and reasoning>

## Resume from here

<open threads and next steps>
```

Any metadata value that could not be determined is the literal `unknown`.

## Step 5: Append to `log.md`

Append one line under today's `## YYYY-MM-DD` header in `log.md`, creating that
header if it is not there:

```
- PARK: [[raw/YYYY-MM-DD/session-<slug>]] — <title>
```

## Step 6: Confirm

Report the note path in one line, and mention that `obsidian-ingest` can later
flesh out the wiki pages for the entities you linked. If any metadata came back
`unknown`, say which fields and why in one short sentence.
````

- [ ] **Step 2: Write the evals**

Create `skills/obsidian-park-session/evals/evals.json`:

```json
{
  "skill_name": "obsidian-park-session",
  "evals": [
    {
      "id": 1,
      "prompt": "Park this session.",
      "expected_output": "A session note is created at raw/YYYY-MM-DD/session-<slug>.md with front matter carrying session_id, models, cwd, branch, started, ended and duration, and a body with What happened / Decisions / Resume from here. One PARK line is appended to log.md. No wiki pages are created.",
      "files": [],
      "assertions": [
        "A file matching raw/*/session-*.md was created",
        "The note front matter includes session_id, models, cwd, started and ended",
        "The note body contains a 'What happened' section",
        "The note body contains a 'Resume from here' section",
        "A line starting with '- PARK:' was appended to log.md",
        "No wiki/ files were created or modified",
        "index.md was not modified"
      ]
    },
    {
      "id": 2,
      "prompt": "I'm done for today, wrap up this session.",
      "expected_output": "Same as eval 1 — the phrase 'I'm done for today' triggers parking. The summary reflects the actual work of the conversation and links relevant entities as [[wiki links]] without creating those pages.",
      "files": [],
      "assertions": [
        "A file matching raw/*/session-*.md was created",
        "The note contains at least one [[wiki link]]",
        "No wiki/ files were created or modified",
        "Exactly one line was appended to log.md"
      ]
    },
    {
      "id": 3,
      "prompt": "Park this session.",
      "expected_output": "No transcript is available (no ~/.claude/projects entry for this working directory). The skill still writes the session note, filling session_id, models, started, ended and duration with the literal 'unknown', and says which fields were unavailable.",
      "files": [],
      "assertions": [
        "A file matching raw/*/session-*.md was created despite the missing transcript",
        "Unavailable front matter fields carry the value 'unknown'",
        "The confirmation mentions that some metadata was unavailable",
        "The skill did not stop with an error"
      ]
    },
    {
      "id": 4,
      "prompt": "Park yesterday's session about the database migration.",
      "expected_output": "The skill explains that only the current session can be parked, and offers to park the current one instead. No note is written for the past session.",
      "files": [],
      "assertions": [
        "The response explains only the current session can be parked",
        "No note was written summarizing a past session",
        "The skill offers to park the current session instead"
      ]
    }
  ]
}
```

- [ ] **Step 3: Add the README entry**

In `README.md`, immediately after the `### obsidian-daily-note` section and before `## Vault conventions`, insert:

```markdown
### `obsidian-park-session`
Park the session you're in — summarizes what happened, the decisions made, and
what to resume next into `raw/YYYY-MM-DD/session-<slug>.md`, with the session
id, models used, working folder, and start/end times in the front matter.
Writes the note plus one `log.md` line; wiki pages are left to `obsidian-ingest`.

**Trigger:** "park this session", "wrap up this session", "I'm done for today".
```

- [ ] **Step 4: Verify the skill loads and the script path resolves**

Run:

```bash
python3 -c "
import sys, pathlib
p = pathlib.Path('skills/obsidian-park-session/SKILL.md').read_text()
assert p.startswith('---'), 'missing front matter'
assert 'name: obsidian-park-session' in p
assert 'description:' in p
print('front matter ok')
"
python3 -m json.tool skills/obsidian-park-session/evals/evals.json > /dev/null && echo "evals json ok"
python3 -m unittest discover -s skills/obsidian-park-session/tests -v
```

Expected: `front matter ok`, `evals json ok`, and all unit tests passing.

- [ ] **Step 5: Commit**

```bash
git add skills/obsidian-park-session/SKILL.md skills/obsidian-park-session/evals/evals.json README.md
git commit -m "feat: add obsidian-park-session skill"
```

---

### Task 4: Manual end-to-end check

Prove the skill actually works against a real vault before calling it done.

**Files:**
- Modify: none (verification only, plus any fixes it turns up)

**Interfaces:**
- Consumes: everything from Tasks 1–3.
- Produces: nothing.

- [ ] **Step 1: Build a throwaway vault**

```bash
VAULT=$(mktemp -d)
mkdir -p "$VAULT/raw" "$VAULT/wiki" "$VAULT/input"
printf '# Schema\n\nraw notes: raw/YYYY-MM-DD/<title>.md\nwiki pages: wiki/<topic>.md\nlog: log.md\n' > "$VAULT/schema.md"
printf '# Log\n' > "$VAULT/log.md"
printf '# Index\n' > "$VAULT/index.md"
echo "$VAULT"
```

- [ ] **Step 2: Park a session into it**

From a Claude Code session whose working directory is `$VAULT`, ask: "Park this session." Confirm by hand:

- `raw/<today>/session-*.md` exists and its front matter values match the JSON from `python3 <repo>/skills/obsidian-park-session/scripts/session_meta.py`
- the three body sections are present and the summary is accurate
- `log.md` gained exactly one `- PARK:` line
- `wiki/` is still empty and `index.md` is unchanged (`git`-free check: `ls "$VAULT/wiki"` is empty, and `index.md` still reads `# Index`)

- [ ] **Step 3: Check the degraded path**

```bash
python3 skills/obsidian-park-session/scripts/session_meta.py --cwd /nonexistent-directory; echo "exit=$?"
```

Expected: a message on stderr and `exit=1`. Confirm `SKILL.md` Step 2 tells the agent to continue and write `unknown` in this case.

- [ ] **Step 4: Fix anything the check turned up, then commit**

If Steps 2–3 turned up problems, fix them, re-run
`python3 -m unittest discover -s skills/obsidian-park-session/tests -v`, and commit:

```bash
git add -A skills/obsidian-park-session
git commit -m "fix: address issues found in park-session end-to-end check"
```

If nothing needed fixing, skip the commit and note that the check passed clean.
