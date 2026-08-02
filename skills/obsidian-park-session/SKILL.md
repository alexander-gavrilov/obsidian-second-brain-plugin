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

Resolve the script path (prefer the installed plugin, fall back to a checkout-local copy):

```bash
SCRIPT=~/.claude/plugins/marketplaces/obsidian-second-brain/skills/obsidian-park-session/scripts/session_meta.py
[ -f "$SCRIPT" ] || SCRIPT=.claude/skills/obsidian-park-session/scripts/session_meta.py
python3 "$SCRIPT"
```

With no arguments it picks the most recently modified transcript for the current
working directory — that is this session. If you know the session id (the
scratchpad path you were given contains it, as
`/tmp/claude-<uid>/<project-slug>/<session-id>/scratchpad`), pass it explicitly
for certainty:

```bash
python3 "$SCRIPT" --session-id <session-id>
```

The script prints a JSON object with `session_id`, `cwd`, `git_branches`,
`models`, `started_at`, `ended_at`, `duration`, `user_turn_count`, `title`, and
`transcript_path`.

**If the script exits non-zero or a field comes back `null` or empty (`[]`)**, that is expected
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

The `# <title>` heading in the note body uses the same rule: if `title` is
`null`, use the same summary-derived phrase used for the slug, title-cased.

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

## Decisions (optional)

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
