# Design: `obsidian-park-session`

**Date:** 2026-08-02
**Status:** Approved, ready for implementation planning

## Problem

At the end of a working session with Claude Code there is no durable record of
what happened. The conversation is thrown away on `/clear`, and the only
artifacts left behind are commits — which capture the code but not the
decisions, the dead ends, or what was about to happen next.

The user wants to "park" a session: capture a summary of it into the Obsidian
vault, together with the session's factual metadata — models used, session id,
working folder, and the start and end times.

## Solution

A new skill, `obsidian-park-session`, that summarizes the current conversation
and writes it into the resolved vault as a session note, with the metadata in
front matter.

The skill follows the plugin's existing split of responsibilities: a
deterministic Python script extracts facts from the Claude Code transcript, and
the skill prose handles the parts that need judgment (the summary, the wiki
links). This mirrors `obsidian-daily-note`, which pairs `SKILL.md` with
`scripts/create_daily_note.py`.

### Rejected alternatives

- **Pure-prose skill** that instructs Claude to pull fields out of the JSONL
  with inline `jq`/`bash`. Fragile across transcript-format changes and
  token-heavy on every run.
- **A script that also writes the note.** The summary is inherently
  LLM-generated; a script could only template around it, so the split would buy
  nothing and cost flexibility.
- **Parking arbitrary past sessions.** Summaries reconstructed from a transcript
  are strictly worse than ones written from lived context. Current-session-only
  keeps a single code path. Backfilling past sessions is explicitly out of
  scope.

## Scope

The skill parks **the current session only**. The summary comes from the live
conversation context; the metadata comes from that session's transcript file.

## Session identity

Claude Code stores transcripts at
`~/.claude/projects/<cwd-slug>/<session-id>.jsonl`, where `<cwd-slug>` is the
working directory with `/` replaced by `-`.

Two independent ways to identify the current session:

1. The scratchpad path given to the agent —
   `/tmp/claude-<uid>/<cwd-slug>/<session-id>/scratchpad` — embeds the session
   id.
2. The most recently modified `.jsonl` in `~/.claude/projects/<cwd-slug>/` is
   the live session.

`session_meta.py` accepts an optional `--session-id` and falls back to
newest-mtime when it is absent.

**The skill runs inline — not `context: fork`.** A forked session risks
resolving to the wrong session id, and since the point of parking is to end the
session, keeping the main context clean has no value here.

## Components

### `scripts/session_meta.py`

Takes an optional `--session-id` and an optional `--cwd` (defaults to the
process working directory). Locates the transcript, parses it line by line, and
prints a single JSON object to stdout:

| Field | Source |
|---|---|
| `session_id` | `sessionId` on any record, or the filename |
| `cwd` | `cwd` field on records |
| `git_branches` | all distinct `gitBranch` values, in order of appearance |
| `models` | distinct `message.model` values, in order of first use |
| `started_at` | earliest `timestamp` |
| `ended_at` | latest `timestamp` |
| `duration` | `ended_at - started_at`, humanized |
| `user_turn_count` | count of `type: "user"` records |
| `title` | the transcript's `ai-title` record, used for the filename slug |
| `transcript_path` | absolute path to the `.jsonl` |

Any field that cannot be determined is emitted as `null` rather than omitted, so
the skill can distinguish "unknown" from "absent". Malformed JSONL lines are
skipped rather than fatal. If no transcript can be found at all, the script
exits non-zero with a message on stderr — the skill treats this as the
degradation path, not an error.

The script must not write anything.

### `SKILL.md`

Front matter: `name`, `description`, and
`tools: Read, Write, Edit, Glob, Grep, Bash`. No `context: fork`.

Flow:

1. **Step 0 — Resolve vault.** Reuse the vault-resolution block from
   `obsidian-quick-capture`: local `schema.md` in the cwd wins; otherwise
   `global_vault_path` from `~/.claude/obsidian-second-brain-config.json`; ask
   only when both exist; stop with a pointer to `obsidian-configure` when
   neither does.
2. **Read `schema.md`** for the vault's folder layout and front-matter
   conventions, and adapt the paths below to it.
3. **Run `session_meta.py`.** On success, use its fields. On failure, continue
   with what is knowable without a transcript — the working directory and
   today's date — and record the remaining fields as `unknown`. This is what
   makes the skill usable outside Claude Code (the plugin also ships as a Gemini
   CLI extension).
4. **Summarize the conversation** into three sections, and identify entities,
   projects, and topics worth linking as `[[wiki links]]` inline in the prose.
5. **Write the note.**
6. **Append one line to `log.md`.**
7. **Report** the note path, and mention that `obsidian-ingest` can later flesh
   out the linked wiki pages.

## Output

### Session note

Path: `raw/YYYY-MM-DD/session-<slug>.md`, where `<slug>` is a kebab-case
shortening of the transcript's `ai-title` (or, when that is unavailable, of the
summary's own topic).

```markdown
---
type: session
source: claude-session
session_id: a9e79288-e90e-4658-be0a-2d32a30b6b04
models: [claude-opus-5]
cwd: /home/alexander/projects/obsidian-second-brain-plugin
branch: master
started: 2026-08-02T19:12:29Z
ended: 2026-08-02T19:41:03Z
duration: 28m
---

# <title>

## What happened

<narrative summary of the work, with [[wiki links]] inline>

## Decisions

<decisions reached and the reasoning behind them>

## Resume from here

<open threads, unfinished work, what to pick up next>
```

Unknown metadata fields carry the literal value `unknown`. When the session
spanned more than one git branch, `branch` lists them comma-separated in the
order they appeared.

### `log.md` entry

One line appended under today's `## YYYY-MM-DD` header, creating the header if
it does not exist:

```
- PARK: [[raw/YYYY-MM-DD/session-<slug>]] — <title>
```

## Hard constraint

The skill writes exactly two things: the session note and the `log.md` line. It
never creates or edits wiki pages, and never touches `index.md`. Wiki links are
written into the note's prose as links even when the target page does not exist;
a later `obsidian-ingest` run is what turns them into pages.

## Triggers

"park this session", "park the chat", "wrap up this session", "save this
session", "summarize and park", "I'm done for today".

## Testing

- `evals/evals.json` alongside the skill, matching the structure used by
  `obsidian-quick-capture`. Cases: parking with a local vault, parking with only
  a global vault configured, and the no-transcript degradation path.
- Direct runs of `session_meta.py` against the real transcripts under
  `~/.claude/projects/-home-alexander-projects-obsidian-second-brain-plugin/`,
  verifying each extracted field against the transcript contents.
- A malformed-JSONL fixture, verifying that bad lines are skipped and the
  remaining fields still come through.

## Documentation

Add an `obsidian-park-session` section to the README's skill list.
