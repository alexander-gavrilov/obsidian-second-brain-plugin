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
