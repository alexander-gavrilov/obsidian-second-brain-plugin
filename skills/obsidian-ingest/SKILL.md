---
name: obsidian-ingest
description: Process and ingest raw content into an Obsidian knowledge vault — creating wiki pages, extracting entities, and updating the index. Use this skill when the user explicitly wants full processing: sharing content with "ingest this", "process this properly", "add to my brain", "file this", "full ingest", or when they want to process a backlog of quick-captures ("process my input", "ingest yesterday", "process my inbox"). Also runs automatically in the background when triggered by obsidian-quick-capture. Prefer obsidian-quick-capture for fast saves during active work; use this skill when thoroughness matters.
tools: Read, Write, Edit, WebFetch, Glob, Grep, Bash
---

# Obsidian Ingest

## Step 0: Resolve vault

Before doing anything else, determine which vault to use. Ask this question **once** — the answer applies to the entire session.

1. Check if a local vault exists: does `schema.md` exist in the current working directory?
2. Read `~/.claude/obsidian-second-brain-config.json` (if it exists) to get `global_vault_path`.

**Decision:**
- Local present + global configured → ask once: *"Run this globally (at `<global_path>`) or locally (current directory)?"*
- Local present + no global configured → use local, no prompt
- No local + global configured → use global path silently; use it as the vault root for all file operations
- No local + no global → stop: *"No vault found here and no global vault is configured. Run `obsidian-configure` to set one up, or `obsidian-init` to create a new vault here."*

All file operations below use the resolved vault root.

---

Process raw content into the Obsidian vault.

Always read `schema.md` first — it defines the vault's conventions, folder structure, and front matter formats.

---

## Determine mode

**Single mode**: The user provides content directly (URL, pasted text, file path, or an idea). → Follow Steps 1–6 for that one item.

**Batch mode**: The user says "process input", "ingest yesterday", "process my inbox", or a background agent is told to process `input/YYYY-MM-DD.md`. → Follow the **Batch Mode** section below, which runs Steps 1–6 for each entry in the file.

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

Be selective. Not every noun needs a wiki page. Ask: "would this entity accumulate more information over time?" If yes, it deserves a page.

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

Front matter:
```
---
type: person | concept | project | place | topic
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
- Called from a background agent spawned by obsidian-quick-capture

### B1: Read and parse the input file

Read `input/YYYY-MM-DD.md` for the target date. Parse it into discrete entries. Each entry is:
- Delimited by `---` separators, starting with `### HH:MM — <title>`
- OR a free-form section with a `## Section Heading` (treat each section as one entry)
- OR bullet points under a heading (treat the whole heading block as one entry)

For entries without a `**src**:` line, treat source as `"personal"`.

### B2: Process each entry through the full pipeline

For each parsed entry, run Steps 1–6 of Single Mode:
- Use the entry's title to derive the raw file name
- Use the entry's `**src**:` value as the source (fetch if URL)
- Use the entry's `**tags**:` as hints for wiki categorization
- Use the entry's content as the raw content to summarize

Fetch URLs only if the content field is sparse (just a URL with no description). If the user already wrote a summary, use that.

Work through entries sequentially. Log each one as it's processed.

### B3: Batch log entry

After all entries are processed, append to `log.md`:

```
## YYYY-MM-DD
- BATCH-INGEST: processed input/<date>.md → <N> items, created/updated <M> wiki pages
```

### B4: Archive the input file

Move the processed file to preserve it:
```bash
mv input/YYYY-MM-DD.md input/processed/YYYY-MM-DD.md
```

Ensure `input/processed/` exists first.

---

## What good looks like

- Raw file is a faithful, concise record of the original content
- Wiki pages feel like reference articles — useful to read cold, not just a dump of facts
- Cross-links connect related entities (a person links to a project they're involved in, a concept links to books that explain it)
- index.md and log.md are always in sync with what was created
- In batch mode: every entry from the input file becomes a proper raw file; the input file is archived
