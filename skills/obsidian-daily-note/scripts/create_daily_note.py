#!/usr/bin/env python3
"""Create an Obsidian daily note at ``input/YYYY-MM-DD.md`` by rendering the vault's
``templates/raw-note.md`` Templater template.

Why this exists: Obsidian's Templater plugin only runs when a note is created through
Obsidian itself (Calendar, the daily-notes command). When a note is created any other
way — an agent writing the file to disk, a script, a sync — Templater never fires and you
end up with raw ``<% ... %>`` syntax sitting in the file. This script renders the same
template deterministically so the daily-note flow works outside Obsidian too, keeping
``templates/raw-note.md`` as the single source of truth.

It understands the specific Templater constructs this vault's template uses:
  * the frontmatter ``date:`` expression  -> the target date
  * the weekday-only ``<%* ... %>`` "Daily routine" execution block

If it meets Templater syntax it does not recognise, it stops rather than writing a
half-rendered note, so you can fall back to rendering by hand.
"""
from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

WEEKDAY_NAMES = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}

TASKS_HEADING = "## ✅ Tasks"

# A task that has been explicitly canceled (UK/US spelling tolerated).
CANCELED_RE = re.compile(r"\[status::\s*cancell?ed\s*\]", re.IGNORECASE)
# Provenance field: the task's original creation date.
FROM_RE = re.compile(r"\[from::\s*(\d{4}-\d{2}-\d{2})\s*\]")
# Any Dataview inline field, e.g. [due:: 2026-06-30].
INLINE_FIELD_RE = re.compile(r"\[[A-Za-z][\w-]*::[^\]]*\]")
# A top-level (non-indented) open checkbox item.
_OPEN_TOP_LEVEL_RE = re.compile(r"^- \[ \] ")


def is_unfinished(line: str) -> bool:
    """True for a top-level open task that has not been canceled.

    Carries open + postponed + postponed-with-due forward; excludes done
    (``- [x]``) and ``[status:: canceled]`` items, and indented sub-items.
    """
    return bool(_OPEN_TOP_LEVEL_RE.match(line)) and not CANCELED_RE.search(line)


def normalize_task_text(line: str) -> str:
    """Task text with list marker, checkbox, and inline fields stripped,
    whitespace collapsed and lowercased. Used to dedup tasks by content."""
    text = re.sub(r"^\s*- \[[ xX-]\]\s*", "", line)
    text = INLINE_FIELD_RE.sub("", text)
    return " ".join(text.split()).lower()


def stamp_provenance(line: str, source_date: str) -> str:
    """Append ``[from:: source_date]`` unless the line already records a
    ``from`` (the original creation date, preserved across carries)."""
    stripped = line.rstrip()
    if FROM_RE.search(stripped):
        return stripped
    return f"{stripped}  [from:: {source_date}]"


def parse_tasks_section(text: str) -> list[str]:
    """Return the raw lines under the ``## ✅ Tasks`` heading, up to the next
    ``## `` heading or end of file. Empty list if the heading is absent."""
    out: list[str] = []
    in_section = False
    for line in text.splitlines():
        if line.strip() == TASKS_HEADING:
            in_section = True
            continue
        if in_section:
            if line.startswith("## "):
                break
            out.append(line)
    return out


_TASKS_HEADING_RE = re.compile(rf"(?m)^{re.escape(TASKS_HEADING)}[ \t]*\n\n?")


def insert_tasks_into_section(text: str, task_lines: list[str]) -> str:
    """Insert ``task_lines`` directly beneath the Tasks heading."""
    if not task_lines:
        return text
    block = "\n".join(task_lines)
    new_text, n = _TASKS_HEADING_RE.subn(
        lambda m: f"{TASKS_HEADING}\n\n{block}\n\n", text, count=1
    )
    if n == 0:
        raise ValueError(f"{TASKS_HEADING!r} heading not found in note")
    return new_text


def iter_daily_notes(vault: Path) -> dict[datetime.date, Path]:
    """Map each daily-note date to its path. Scans ``input/YYYY-MM-DD.md`` and
    archived ``raw/YYYY-MM-DD/daily-note.md``; the live ``input/`` copy wins
    when a date exists in both."""
    notes: dict[datetime.date, Path] = {}
    input_dir = vault / "input"
    if input_dir.exists():
        for p in input_dir.glob("*.md"):
            try:
                notes[datetime.date.fromisoformat(p.stem)] = p
            except ValueError:
                continue
    raw_dir = vault / "raw"
    if raw_dir.exists():
        for p in raw_dir.glob("*/daily-note.md"):
            try:
                notes.setdefault(datetime.date.fromisoformat(p.parent.name), p)
            except ValueError:
                continue
    return notes


def find_prior_daily_note(vault: Path, target_date: datetime.date):
    """Most recent (date, path) strictly before ``target_date``, or None."""
    priors = [(d, p) for d, p in iter_daily_notes(vault).items() if d < target_date]
    if not priors:
        return None
    return max(priors, key=lambda dp: dp[0])


def select_carry_tasks(prior_text: str, source_date: str,
                        existing_normalized: set) -> list:
    """Unfinished tasks from ``prior_text``, deduped against
    ``existing_normalized`` (mutated), each stamped with provenance."""
    carried = []
    for line in parse_tasks_section(prior_text):
        if not is_unfinished(line):
            continue
        norm = normalize_task_text(line)
        if not norm or norm in existing_normalized:
            continue
        existing_normalized.add(norm)
        carried.append(stamp_provenance(line, source_date))
    return carried


def collect_recollect_candidates(vault: Path, target_date: datetime.date) -> list:
    """Unfinished tasks from daily notes older than the most recent prior note
    (the most recent is handled by normal carry-over). Each candidate is
    ``{"origin", "age", "line"}``; excludes tasks already in the target note;
    sorted oldest first."""
    notes = iter_daily_notes(vault)
    prior_dates = sorted(d for d in notes if d < target_date)
    if len(prior_dates) < 2:
        return []  # nothing older than the most recent prior note
    most_recent = prior_dates[-1]

    seen = set()
    target_path = vault / "input" / f"{target_date.isoformat()}.md"
    if target_path.exists():
        seen = {
            normalize_task_text(l)
            for l in parse_tasks_section(target_path.read_text(encoding="utf-8"))
            if l.strip()
        }

    candidates = []
    for d in prior_dates:
        if d >= most_recent:
            continue
        text = notes[d].read_text(encoding="utf-8")
        for line in parse_tasks_section(text):
            if not is_unfinished(line):
                continue
            norm = normalize_task_text(line)
            if not norm or norm in seen:
                continue
            seen.add(norm)
            m = FROM_RE.search(line)
            origin = m.group(1) if m else d.isoformat()
            age = (target_date - datetime.date.fromisoformat(origin)).days
            candidates.append(
                {"origin": origin, "age": age, "line": stamp_provenance(line, d.isoformat())}
            )
    candidates.sort(key=lambda c: c["age"], reverse=True)
    return candidates


def find_vault(start: Path) -> Path:
    """Walk upward from ``start`` looking for a vault root (has templates/raw-note.md)."""
    start = start.resolve()
    for candidate in (start, *start.parents):
        if (candidate / "templates" / "raw-note.md").exists():
            return candidate
    return start


def parse_target_date(arg: str | None, today: datetime.date) -> datetime.date:
    """Resolve the requested date. Accepts today/tomorrow/yesterday, a weekday name
    (the nearest upcoming one, today included), or an explicit YYYY-MM-DD."""
    if not arg or arg.strip().lower() == "today":
        return today
    s = arg.strip().lower()
    if s == "tomorrow":
        return today + datetime.timedelta(days=1)
    if s == "yesterday":
        return today - datetime.timedelta(days=1)
    if s in WEEKDAY_NAMES:
        delta = (WEEKDAY_NAMES[s] - today.weekday()) % 7
        return today + datetime.timedelta(days=delta)
    try:
        return datetime.date.fromisoformat(arg.strip())
    except ValueError:
        sys.exit(
            f"ERROR: could not parse date {arg!r}. "
            "Use YYYY-MM-DD, today, tomorrow, yesterday, or a weekday name."
        )


def render(template: str, target: datetime.date) -> str:
    """Render the known Templater constructs for ``target``."""
    iso = target.isoformat()
    is_weekday = 0 <= target.weekday() <= 4  # Mon-Fri (Python: Mon=0..Sun=6)

    text = template

    # 1) Frontmatter date expression -> the target ISO date.
    text = re.sub(
        r"(?m)^(date:\s*)<%.*?%>\s*$",
        lambda m: f"{m.group(1)}{iso}",
        text,
    )

    # 2) Templater execution blocks. The template wraps the routine checklist in a
    #    weekday conditional whose markdown lives in the first `...` template literal.
    #    On weekdays we emit that markdown; on weekends we drop the whole block.
    def render_exec_block(m: re.Match) -> str:
        if not is_weekday:
            return ""
        literal = re.search(r"`(.*?)`", m.group(1), re.DOTALL)
        return literal.group(1) if literal else ""

    text = re.sub(r"<%\*(.*?)%>", render_exec_block, text, flags=re.DOTALL)

    return text


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "date", nargs="?",
        help="today | tomorrow | yesterday | <weekday name> | YYYY-MM-DD (default: today)",
    )
    ap.add_argument("--vault", help="vault root (default: search upward from CWD)")
    ap.add_argument(
        "--force", action="store_true",
        help="overwrite an existing note (default: refuse, to protect real content)",
    )
    ap.add_argument(
        "--recollect", action="store_true",
        help="list unfinished tasks older than the last daily note (read-only) "
             "instead of creating a note",
    )
    args = ap.parse_args()

    vault = Path(args.vault).resolve() if args.vault else find_vault(Path.cwd())
    template_path = vault / "templates" / "raw-note.md"
    if not template_path.exists():
        sys.exit(f"ERROR: template not found at {template_path}")

    target = parse_target_date(args.date, datetime.date.today())
    if args.recollect:
        cands = collect_recollect_candidates(vault, target)
        if not cands:
            print("RECOLLECT: no older unfinished tasks found.")
            return
        print(f"RECOLLECT: {len(cands)} candidate(s) older than the last daily note:")
        for c in cands:
            print(f"  {c['origin']} · {c['age']}d · {c['line']}")
        return

    out_path = vault / "input" / f"{target.isoformat()}.md"

    if out_path.exists() and not args.force:
        sys.exit(
            f"EXISTS: {out_path} already exists; refusing to overwrite "
            "to protect existing content. Pass --force to replace it."
        )

    rendered = render(template_path.read_text(encoding="utf-8"), target)

    carried = []
    prior = find_prior_daily_note(vault, target)
    if prior:
        prior_date, prior_path = prior
        existing = {
            normalize_task_text(l)
            for l in parse_tasks_section(rendered)
            if l.strip()
        }
        carried = select_carry_tasks(
            prior_path.read_text(encoding="utf-8"),
            prior_date.isoformat(),
            existing,
        )
        if carried:
            rendered = insert_tasks_into_section(rendered, carried)

    if "<%" in rendered:
        sys.exit(
            "UNRENDERED: the template contains Templater syntax this script does not "
            "understand. Render the note by hand instead of writing a broken file."
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered, encoding="utf-8")

    routine = "included" if 0 <= target.weekday() <= 4 else "omitted (weekend)"
    print(f"CREATED: {out_path}")
    print(f"  date: {target.isoformat()} ({target.strftime('%A')}); daily routine {routine}")
    if carried:
        print(f"  carried forward {len(carried)} task(s) from {prior_date.isoformat()}")


if __name__ == "__main__":
    main()
