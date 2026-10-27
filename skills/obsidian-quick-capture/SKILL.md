---
name: obsidian-quick-capture
description: Fast capture of content into the vault's daily input file (input/YYYY-MM-DD.md) without processing it. Use when the user says "capture this", "note this", "quick save", "add to my inbox", "jot this down", or pastes a link or text to save for later. Prefer over obsidian-ingest when the user is mid-task and just wants it recorded.
allowed-tools: Read, Write, Edit, Glob, Bash
---

# Obsidian Quick Capture

Append one entry to `input/YYYY-MM-DD.md`. No entity extraction, no wiki updates, no task filing, no briefing — `obsidian-ingest` processes the file later. This skill runs **inline** in the current conversation so it can see what the user wants captured (do not run it as a forked/background skill).

> **Hard constraint**: the only file written is today's `input/YYYY-MM-DD.md`. Never touch `raw/`, `wiki/`, `tasks/`, `index.md` or `log.md`. Scaffolding today's note via the daily-note script (Step 2) is the sanctioned way to create it.

## Step 1: Resolve vault

Run `python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/marketplaces/obsidian-second-brain}/scripts/resolve_vault.py"`. It prints `root=`, `mode=`, `local=`, `global=`; exit 2 means no vault (tell the user to run `obsidian-configure`). `mode=single` -> use `root`; `mode=ambiguous` -> ask once per session whether to capture to the global or local vault. Do not re-ask mid-session.

## Step 2: Ensure today's file exists

```bash
TODAY=$(date +%Y-%m-%d)
[ -f "<root>/input/$TODAY.md" ] || {
  SCRIPT="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/marketplaces/obsidian-second-brain}/skills/obsidian-daily-note/scripts/create_daily_note.py"
  [ -f "$SCRIPT" ] || SCRIPT="<root>/.claude/skills/obsidian-daily-note/scripts/create_daily_note.py"
  python3 "$SCRIPT" "$TODAY" --vault "<root>"
}
```

Always pass `--vault`. If the script reports the template is missing, tell the user to run `obsidian-init`; never hand-write a bare file. If a legacy file lacks a `## 📥 Captures` heading, add it at the end first.

## Step 3: Append the entry

Take the content **verbatim from the conversation** (pasted text, link, the user's own words). Do not fetch URLs or summarise away detail. Get the time with `date +%H:%M`. Append under `## 📥 Captures` (not at end of file — the template has other sections), with a blank line before it if the section already has content:

```markdown
### HH:MM — <short title>
**src**: <url | personal | file:path | conversation>
**tags**: tag1, tag2

<English summary, 1-3 lines, if the content is not English or is long>

<original content, verbatim — keep non-English text (PL/RU/...) exactly as written>

---
```

Title is 2-5 words; 1-3 tags inferred from content. English-only content needs no separate summary.

## Step 4: Confirm

One line, e.g. `Captured "claude-routines-blog" to input/2026-10-27.md.` Do not promise when ingest will run.
