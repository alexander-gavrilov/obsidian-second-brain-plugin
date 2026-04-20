---
name: obsidian-quick-capture
description: Fast, non-blocking capture of content into the Obsidian vault's daily input file. Use this skill when the user wants to save something quickly without waiting — URLs, ideas, notes, meeting bullets, or anything they say like "capture this", "note this", "quick save", "add to my inbox", "jot this down", or just pastes a link or text and says "save for later". Strongly prefer this over obsidian-ingest when the user is in the middle of something and just wants to capture without being blocked. Also trigger when the user starts their day or says something like "let's get started" or "morning" — in that case, run the first-capture-of-day briefing even with no content.
tools: Read, Write, Edit, Glob, Grep, Bash, Agent
---

# Obsidian Quick Capture

Capture content fast into `input/YYYY-MM-DD.md`. No entity extraction, no wiki updates — that happens later in the background. The goal is to get content recorded in under 5 seconds of wait time.

## Step 0: Resolve vault

Resolve this once per session — don't ask again mid-session.

1. Check if a local vault exists: does `schema.md` exist in the current working directory?
2. Read `~/.claude/obsidian-second-brain-config.json` (if it exists) to get `global_vault_path`.

**Decision:**
- Local present + global configured → ask once: *"Capture to global vault (at `<global_path>`) or local (current directory)?"*
- Local present + no global configured → use local, no prompt
- No local + global configured → use global path silently
- No local + no global → stop: *"No vault found here and no global vault is configured. Run `obsidian-configure` to set one up."*

All file operations below use the resolved vault root.

---

Read `schema.md` only if you haven't already in this session.

> **Hard constraint**: This skill writes to exactly ONE file: `input/YYYY-MM-DD.md`. Never create or modify anything in `raw/`, `wiki/`, `index.md`, or `log.md`. Reading `wiki/projects/` for the morning briefing is fine — but reading is not a trigger to write. If you notice an entity or concept worth tracking, do not create a wiki page. Just capture the content and let the background ingest handle it later.

---

## Step 1: Check if this is the first capture of the day

Check whether `input/YYYY-MM-DD.md` exists for today's date:
- **If the file does not exist**: this is the first capture of the day → run the **First-Capture-of-Day routine** (Step 2) before proceeding
- **If the file exists**: skip to Step 3

---

## Step 2: First-capture-of-day routine

This runs once per day, before the first capture is written. It has two parts: a background catch-up and a morning briefing.

### 2a: Trigger background ingest for all unprocessed days

Scan for every input file that hasn't been ingested yet:

1. Glob `input/YYYY-MM-DD.md` files (exclude `input/processed/`). For each file found, extract the date from the filename.
2. Read `log.md` once. For each date, check whether a `- BATCH-INGEST:` or `- INGEST:` line appears under its `## YYYY-MM-DD` header.
3. Collect all dates where an input file **exists** but the log has **no INGEST entry** for that date. Skip today — only process past days.

If there are unprocessed days, spawn a **single** background agent to process all of them sequentially:

**How to spawn the background ingest:**

Read the obsidian-ingest skill at `~/.claude/plugins/marketplaces/obsidian-second-brain/skills/obsidian-ingest/SKILL.md` to get its instructions. Then spawn:

```
Agent(
  description: "Background ingest for <N> unprocessed days",
  run_in_background: true,
  prompt: """
Working directory: <vault_absolute_path>
Today's date for logging purposes: <today's date>

Process all unprocessed quick-capture input files in order (oldest first):
<list each unprocessed file: input/YYYY-MM-DD.md>

Read and follow these instructions exactly:
<full contents of obsidian-ingest SKILL.md>

For each file:
  Parse each entry (separated by `---`, starting with `### HH:MM —`).
  For each entry run the full ingest pipeline: create raw file, extract entities,
  update wiki pages, update index.md. Fetch URLs if the content is sparse.

After processing each file:
  - Append `- BATCH-INGEST: processed input/<date>.md → <N> items` to log.md
    under the <today's date> header (create it once if it doesn't exist)
  - Move the file: mv input/<date>.md input/processed/<date>.md

Work autonomously — no user interaction needed.
"""
)
```

Tell the user how many days are queued: "Running background ingest for N unprocessed day(s) — I'll notify you when done." If nothing is unprocessed, skip silently.

### 2b: Generate the morning briefing

Read these files to build context (read them in parallel):
- `log.md` — last 40 lines (recent activity)
- All files in `wiki/projects/` (glob then read each)
- `input/<yesterday>.md` if it exists (to know what was captured but not yet processed)

Then produce a **Daily Briefing** in this format:

```
## Daily Briefing — <Weekday>, <Month Day>

**Active projects** (from wiki):
- <project name>: <one-line status or last notable update>
- ...

**Captured yesterday** (not yet processed):
- <brief list of titles from yesterday's input, if any>

**Suggested focus for today**:
- <2-4 concrete suggestions based on recent log activity, project states, and unprocessed items>

**Worth keeping in mind**:
- <1-2 observations — e.g. a project that went quiet, a person you haven't checked in with, a concept with open questions>
```

Be specific and concrete. Pull from actual content in the files, not generic advice. If a project page mentions a deadline or milestone, surface it. If log.md shows a topic ingested 10 days ago with no follow-up, note it.

---

## Step 3: Parse the input

The user provides one of:
- **URL** — the title is inferred from the URL or surrounding context
- **Pasted text or idea** — treat as a personal note
- **File path** — use the filename as the title
- **Nothing** (morning trigger only) — skip to Step 4, no entry to write

Infer a short title (2–5 words, lowercase-hyphenated). Infer 1–3 tags from content. Do not fetch URLs yet — that happens during full ingest.

For text content: keep it verbatim or lightly cleaned. For URLs: use any surrounding context the user gave as the content (don't fetch). Mark source appropriately.

---

## Step 4: Append to the daily input file

Create `input/YYYY-MM-DD.md` if it doesn't exist yet (no header needed — just entries).

Append this entry block to the file:

```markdown
### HH:MM — <title>
**src**: <url | note | file:path>
**tags**: tag1, tag2

<content — the user's text, verbatim idea, or a one-line description of the URL>

---
```

Get the actual current time by running `date +%H:%M` via Bash. Use that value as the timestamp. Leave a blank line before `### HH:MM` if the file already has content.

---

## Step 5: Confirm to the user

Reply with a single short confirmation — one line. Example:

> Captured: "claude-routines-blog" — added to today's input. Full ingest will run in the background tonight.

If the morning briefing was shown (Step 2b), the confirmation can be even shorter since you already said plenty.

---

## What good looks like

- The user waited less than 5 seconds
- The entry is in `input/YYYY-MM-DD.md` with correct format
- If it was the first capture of the day: background ingest was triggered for all unprocessed days (not just yesterday) and the briefing was relevant and actionable
- No wiki files were touched, no entity extraction was done
