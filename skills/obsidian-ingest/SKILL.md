---
name: obsidian-ingest
description: >-
  Process content into the Obsidian vault - raw record, wiki pages, index, log, and tasks.
  Use when the user wants full processing: "ingest this", "process this properly", "add to
  my brain", "file this", or a backlog ("process my input", "ingest yesterday", "process my
  inbox", "process incoming"). Prefer obsidian-quick-capture for fast saves mid-task.
allowed-tools: Read, Write, Edit, WebFetch, Glob, Grep, Bash
---

# Obsidian Ingest

## Step 0: Resolve vault

Run the shared resolver (`${CLAUDE_PLUGIN_ROOT}/scripts/resolve_vault.py`; if that variable is unset use `~/.claude/plugins/marketplaces/obsidian-second-brain/scripts/resolve_vault.py`):

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/marketplaces/obsidian-second-brain}/scripts/resolve_vault.py"
```

It prints `root=`, `mode=`, `local=`, `global=`. Exit code 2 means no vault is available: stop and tell the user to run `obsidian-configure` (or `obsidian-init` to create one here).

- `mode=single` (including when the current directory *is* the global vault) -> use `root`, never prompt.
- `mode=ambiguous` (a local vault and a different global vault) -> ask once per session: *"Run this global (at `<global>`) or local (`<local>`)?"* Use the answer as the root.

All file operations below use `root`.

---

Process raw content into the Obsidian vault.

Always read `schema.md` first — it defines the vault's conventions, folder structure, and front matter formats. The vault specs referenced below (`conductor/task-storage-spec.md`, `conductor/daily-briefing-prompt.md` §3.2) are authoritative; read them when the vault has them and don't duplicate their rules here.

---

## Determine mode

**Single mode**: The user provides content directly (URL, pasted text, file path, or an idea). → Follow Steps 1–6 for that one item.

**Incoming mode**: the user says "process incoming" or points at files in `incoming/` -> see **Incoming Mode**.

**Batch mode**: The user says "process input", "ingest yesterday", "process my inbox", or an agent is told to process `input/YYYY-MM-DD.md`. → Follow the **Batch Mode** section below, which runs Steps 1–6 for each entry in the file.

---

## Single Mode

### Step 1: Determine input type

The user will provide one of:
- **URL** — fetch the content with WebFetch
- **Pasted text** — use as-is
- **File path** — read the file

If the input is ambiguous, make a reasonable guess rather than asking.

### Step 2: Check for duplicates, then create the raw file

Before creating anything, check if this source was already ingested:
- For URLs: `Grep source: <url>` across `raw/` — if found, update the existing wiki pages instead of creating a new raw file, and note the update in log.md
- For pasted text: scan raw titles for obvious overlap, but err on the side of creating rather than skipping

If a duplicate is found, tell the user and proceed to update the relevant wiki pages with any new information.

Create a folder `raw/YYYY-MM-DD/` for today's date (if it doesn't exist), then create a file inside it named `short-title.md`. The title should be 2-5 words, lowercase-hyphenated, descriptive of the content (not generic like "note" or "article").

For **media files** (images, PDFs, audio, video) provided as file paths: copy or reference them into the same `raw/YYYY-MM-DD/` folder. Create a companion `.md` file (e.g., `screenshot.md`) to hold the front matter and any notes about the media.

Front matter:
```
---
date: YYYY-MM-DD
source: <url | "personal" | "file:<path>" | "google-keep">
tags: [<2-4 relevant tags>]
---
```

Write a clean, faithful summary of the content under the front matter. For URLs: summarize the key ideas, not just headlines. For personal notes: preserve the content verbatim or lightly formatted. Keep it concise — this is the immutable source record, not the wiki page.

### Step 3: Extract entities

Scan the content for named entities worth tracking:
- **People** — named individuals worth remembering
- **Concepts** — ideas, frameworks, terms that have depth
- **Projects** — specific initiatives or efforts
- **Places** — locations worth remembering
- **Topics** — recurring themes that don't fit the above
- **Events** — dated happenings (trip, appointment, meeting) -> page `type: event`

Be selective. Not every noun needs a wiki page. Ask: "would this entity accumulate more information over time?" If yes, it deserves a page.

### Step 3b: Detect tasks and file them

In addition to — never instead of — normal wiki filing, check whether the content states an obligation on Alexander's own future action ("надо", "не забыть", "need to", "remember to", an explicit "task"/"todo", ...). Follow `schema.md` Operations > Ingest and `conductor/task-storage-spec.md` (line format, buckets, §7 duplicate rules):
- Determine the due date (ISO) if stated or clearly implied; write the task line (`- [ ] description (created: today) (due: ...) [[links]]`).
- Dup check against open tasks in `tasks/today.md`, `tasks/scheduled.md` and `tasks/someday.md`; if a near-duplicate exists, don't write it but still log it.
- File to `someday.md` (no date), `scheduled.md` (future, under `## YYYY-MM-DD`) or `today.md` (today/overdue, right sub-heading).
- Append a **separate** `TASK_ADD` line to `log.md` per task, even inside a BATCH-INGEST.
- Ambiguous commitments: file to the wiki only and mention the ambiguity in the summary.
- Ignore someone else's action items and past events.

### Step 3c: Detect completions

For newly ingested content, compare with all open tasks in `tasks/`. On confident evidence a task is done (proof of payment, confirmed booking, explicit statement), follow `conductor/daily-briefing-prompt.md` §3.2 Step 2: flip to `- [x]`, add `(completed: <today's run date>)`, move the line to the top of `tasks/done.md`, and log `TASK_DONE: "<description>" → tasks/done.md`. Be conservative: ambiguous or partial evidence stays open. Evidence that makes a task moot rather than done -> `TASK_CANCEL` per spec §7.

### Original language

Keep non-English text (PL/RU/...) **verbatim** in raw files and quote it in wiki pages where it matters (names, document wording, amounts). Add an English summary alongside it; never replace the original with a translation.

### Step 4: Create or update wiki pages

For each entity identified:

1. **Check if a page exists** using Glob: `wiki/<category>/<entity-name>.md`
2. **If it exists**: read it and append or integrate new information. Don't duplicate what's already there — add only what's new. Update the `updated` date in front matter.
3. **If it doesn't exist**: create it.

#### Wiki page format

File path: `wiki/<category>/<entity-name>.md` (lowercase, hyphenated)

Category mapping:
- People → `wiki/people/`
- Health topics, habits, medical → `wiki/health/`
- Money, budgets, accounts → `wiki/finance/`
- Books, courses, ideas, frameworks → `wiki/learning/`
- Personal projects, hobbies → `wiki/projects/`
- Locations, restaurants, travel → `wiki/places/`
- Work-related → `wiki/work/`
- Owned devices and gadgets → `wiki/devices/` (a register `devices.md` plus one page per device: purchase date, warranty, notes; add new devices to the register). Use only if `schema.md` lists the category.

Front matter:
```
---
type: person | concept | project | place | topic | event
updated: YYYY-MM-DD
---
```

Content guidelines:
- Write in a neutral, encyclopedic tone — this is a reference, not a diary
- Link to related wiki pages using `[[wiki/category/page-name]]`
- Include a "Sources" section at the bottom linking back to the raw file(s): `[[raw/YYYY-MM-DD/title]]`
- Keep it dense and scannable — use headers for longer pages, bullet points for lists of facts

### Step 5: Update index.md

For any **newly created** wiki pages (not updates), add an entry to the appropriate section in `index.md`:

```
- [[wiki/category/page-name]] — one-line description
```

Don't add entries for existing pages that were just updated.

### Step 6: Append to log.md

Add an entry at the bottom of `log.md`:

```
## YYYY-MM-DD
- INGEST: <short-title> → created raw/YYYY-MM-DD/short-title, [created|updated] wiki/<pages>
```

If a log entry for today already exists, append to it rather than creating a duplicate header.

---

## Batch Mode

Batch mode processes all entries in an `input/YYYY-MM-DD.md` file. Use when:
- The user asks to process their inbox or a specific date's captures
- An agent (e.g. the vault's scheduled daily briefing) is told to process specific input files

### B1: Read and parse the input file

Read `input/YYYY-MM-DD.md` (ignore the template sections — Agenda, Tasks checklists, routine, Meeting notes — unless the user wrote content there; process what is under `## 📥 Captures`). Parse tolerantly into entries:
- An entry starts at a `### HH:MM — <title>` heading (em dash; a hyphen is accepted) and runs to the next such heading. `---` delimiters are optional.
- Tags may be a `**tags**: a, b` line or a `#tag #tag2` line; source is `**src**: ...`. With no `**src**`, source is `"personal"`.
- Free-form `## Section` blocks or bullet groups under a heading count as one entry each.
- Entries that are empty or only template scaffolding are skipped (not counted).

### B2: Process each entry through the full pipeline

For each parsed entry, run Steps 1–6 of Single Mode:
- Use the entry's title to derive the raw file name
- Use the entry's `**src**:` value as the source (fetch if URL)
- Use the entry's `**tags**:` as hints for wiki categorization
- Use the entry's content as the raw content to summarize

Task detection (3b) and completion detection (3c) run per entry. Fetch URLs only if the content field is sparse (just a URL with no description). If the user already wrote a summary, use that.

Work through entries sequentially. Log each one as it's processed.

### B3: Batch log entry

After all entries are processed, append to `log.md`:

```
## YYYY-MM-DD
- BATCH-INGEST: processed input/<date>.md → <N> items, created/updated <M> wiki pages
```

`TASK_ADD` / `TASK_DONE` lines stay separate (see Step 3b).

### B4: Archive the input file

Move the processed file to preserve it:
```bash
mv input/YYYY-MM-DD.md input/processed/YYYY-MM-DD.md
```

Ensure `input/processed/` exists first.

---

## Incoming Mode

`incoming/` is a drop folder for loose files (photos, screenshots, PDFs, invoices, bank confirmations). For each file (oldest first):
1. Read/inspect it (images and PDFs are readable); decide the document's real date and a 2-5 word title.
2. Move it into `raw/YYYY-MM-DD/` (use the document's date, else today's) and create the companion `<title>.md` there with the usual front matter (`source: "file:incoming/<original-name>"`) plus a faithful summary; keep any non-English text verbatim (see Original language).
3. Run Steps 3-6 on it (entities, wiki, tasks 3b, completions 3c, index). A payment confirmation commonly completes an open task.
4. Skip and delete only files that are exact duplicates of something already ingested (check `raw/` first).
5. Log each with `INGEST: incoming/<file> (<what>) → created raw/..., created|updated wiki/...`, or one `BATCH-INGEST: processed incoming/ backlog (N files ...)` line for a backlog, matching earlier `log.md` entries. Leave `incoming/` empty.

---

## What good looks like

- Raw file is a faithful, concise record of the original content
- Wiki pages feel like reference articles — useful to read cold, not just a dump of facts
- Cross-links connect related entities (a person links to a project they're involved in, a concept links to books that explain it)
- index.md and log.md are always in sync with what was created
- In batch mode: every entry from the input file becomes a proper raw file; the input file is archived
