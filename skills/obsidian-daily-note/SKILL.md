---
name: obsidian-daily-note
description: >-
  Create an Obsidian daily note file at input/YYYY-MM-DD.md by rendering the vault's
  templates/raw-note.md template — including the weekday-only "Daily routine" checklist
  and the correct frontmatter date. Use this whenever the user wants to create, scaffold,
  start, or set up a daily note / daily journal for a given day ("make today's note",
  "create a daily note for Saturday", "new journal entry for tomorrow", "set up my
  daily note"). Especially important when the note is being created from the agent /
  terminal rather than inside Obsidian, because Obsidian's Templater plugin only runs on
  notes created through Obsidian itself — created any other way, the file is left with raw
  <% %> syntax. This skill renders that template correctly outside Obsidian. Do NOT use
  it for appending a quick capture to an existing day (that's quick-capture) or for
  processing/ingesting notes (that's ingest).
model: haiku
---

# Obsidian daily note

Create a daily note at `input/YYYY-MM-DD.md` that looks exactly like one Obsidian's
Templater plugin would have produced — same source of truth (`templates/raw-note.md`),
rendered deterministically so it works from the terminal where Templater never runs.

## Step 0: Resolve vault

Resolve this once per session — don't ask again mid-session.

1. Check if a local vault exists: does `schema.md` exist in the current working directory?
2. Read `~/.claude/obsidian-second-brain-config.json` (if it exists) to get `global_vault_path`.

**Decision:**
- Local present + global configured → ask once: *"Create the daily note in the global vault (at `<global_path>`) or the local one (current directory)?"*
- Local present + no global configured → use local, no prompt
- No local + global configured → use global path silently
- No local + no global → stop: *"No vault found here and no global vault is configured. Run `obsidian-configure` to set one up."*

Pass the resolved vault root to the script via `--vault` on every invocation below (the script otherwise searches upward from the current directory, which is wrong in global-vault mode).

## When this matters

Obsidian's Templater only fires when a note is created *inside* Obsidian (the Calendar
plugin, the daily-notes command). A note created any other way — you writing the file, a
script, a sync — never triggers Templater, so the file is left holding literal
`<% tp.date.now(...) %>` text and the weekday routine logic never runs. This skill closes
that gap: it renders the same template the same way, no Obsidian required.

## How to do it

Run the bundled script from the vault root. It finds the vault by walking up to the
folder containing `templates/raw-note.md`, so the working directory just needs to be
inside the vault.

Resolve the script path (prefer the installed plugin, fall back to a vault-local copy):

```bash
SCRIPT=~/.claude/plugins/marketplaces/obsidian-second-brain/skills/obsidian-daily-note/scripts/create_daily_note.py
[ -f "$SCRIPT" ] || SCRIPT=.claude/skills/obsidian-daily-note/scripts/create_daily_note.py
python3 "$SCRIPT" [DATE] --vault "<resolved vault root>"
```

`DATE` is optional and flexible:

- omitted or `today` → today (uses the real system clock)
- `tomorrow` / `yesterday`
- a weekday name like `saturday` → the nearest upcoming one (today counts)
- an explicit `YYYY-MM-DD`

**Examples**

| User says | Command |
|---|---|
| "create today's daily note" | `SCRIPT=~/.claude/plugins/marketplaces/obsidian-second-brain/skills/obsidian-daily-note/scripts/create_daily_note.py; [ -f "$SCRIPT" ] \|\| SCRIPT=.claude/skills/obsidian-daily-note/scripts/create_daily_note.py; python3 "$SCRIPT"` |
| "make a daily note for Saturday" | `SCRIPT=~/.claude/plugins/marketplaces/obsidian-second-brain/skills/obsidian-daily-note/scripts/create_daily_note.py; [ -f "$SCRIPT" ] \|\| SCRIPT=.claude/skills/obsidian-daily-note/scripts/create_daily_note.py; python3 "$SCRIPT" saturday` |
| "set up tomorrow's journal" | `SCRIPT=~/.claude/plugins/marketplaces/obsidian-second-brain/skills/obsidian-daily-note/scripts/create_daily_note.py; [ -f "$SCRIPT" ] \|\| SCRIPT=.claude/skills/obsidian-daily-note/scripts/create_daily_note.py; python3 "$SCRIPT" tomorrow` |
| "new daily note for 2026-07-01" | `SCRIPT=~/.claude/plugins/marketplaces/obsidian-second-brain/skills/obsidian-daily-note/scripts/create_daily_note.py; [ -f "$SCRIPT" ] \|\| SCRIPT=.claude/skills/obsidian-daily-note/scripts/create_daily_note.py; python3 "$SCRIPT" 2026-07-01` |

Every example assumes `--vault "<resolved vault root>"` is appended (omitted above for brevity); it is required whenever the command is not run from inside the target vault.

## What the script guarantees

- **One source of truth.** It renders `templates/raw-note.md`, so any edit to that
  template flows through automatically — don't hardcode the note layout anywhere else.
- **Weekday-aware routine.** The "✅ Daily routine" checklist is included Mon–Fri and
  omitted on weekends, matching the template's Templater conditional.
- **Never clobbers content.** If `input/YYYY-MM-DD.md` already exists it refuses and
  reports the path. Only pass `--force` if the user explicitly wants to overwrite — and
  prefer not to, since these notes hold real journal content.
- **Fails loud, not silent.** If the template grows Templater syntax the script doesn't
  recognise, it stops with an `UNRENDERED:` message instead of writing a half-rendered
  file. If you see that, render the note by hand (read the template, substitute the date,
  include the routine only on Mon–Fri) rather than shipping broken `<% %>` text.
- **No template?** If `templates/raw-note.md` does not exist, the script exits with
  `ERROR: template not found`. Do not hand-write a bare daily note — run
  `obsidian-init` first to scaffold the template, then retry.

## Tasks section & carry-over

The template includes a `## ✅ Tasks` section. Tasks use Dataview inline fields:

- Open → `- [ ] Task`
- Done → `- [x] Task  [done:: YYYY-MM-DD]` (done date optional)
- Canceled → `- [ ] Task  [status:: canceled]`
- Postponed → `- [ ] Task  [status:: postponed]` and/or `[due:: YYYY-MM-DD]`
- Carried-forward tasks gain `[from:: YYYY-MM-DD]` (original creation date).

On creation the script carries forward every unfinished task (`- [ ]`, not
`[status:: canceled]`) from the **most recent prior daily note** — open and
postponed both move; done and canceled stay behind. Duplicates (a task already
typed into the new note) are skipped. This runs **only on the script/agent
path**: a note created inside Obsidian gets an empty Tasks section. Carry-over reads only the lines between `## ✅ Tasks` and the next `## ` heading, so on weekdays the `## ✅ Daily routine` sibling heading bounds it — type real tasks under `## ✅ Tasks` (above the routine), not under the routine heading, or they won't carry forward.

### Recollecting older tasks

Because carry-over only looks at the last note, tasks on skipped days can be
orphaned. To recover them, run the read-only recollect scan and present the
results for the user to choose from:

```bash
SCRIPT=~/.claude/plugins/marketplaces/obsidian-second-brain/skills/obsidian-daily-note/scripts/create_daily_note.py
[ -f "$SCRIPT" ] || SCRIPT=.claude/skills/obsidian-daily-note/scripts/create_daily_note.py
python3 "$SCRIPT" [DATE] --recollect
```

It prints `origin-date · age · task` for every unfinished task older than the
last note (excluding ones already in today's note). It creates/modifies
nothing — after the user picks which to keep, append the chosen lines (with
their `[from::]`/`[due::]`/`[status::]` fields intact) under the target day's
`## ✅ Tasks` heading yourself.

## After creating

Report the path the script printed and whether the routine was included or omitted. Don't
re-read the file just to confirm — the script already validated there's no leftover
Templater syntax. If the user asked for today's note so they can work in it, that's done;
hand it back.
