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

import argparse
import datetime
import json
import sys
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
