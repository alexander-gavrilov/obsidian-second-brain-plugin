---
name: obsidian-migrate
description: Migrate notes from Google Keep (or other external sources) into an Obsidian knowledge vault. Use this skill when the user wants to import, migrate, or bring in notes from Google Keep, a JSON export, or another external note app. Trigger on phrases like "migrate my Keep notes", "import this export", "bring in my old notes", "let's migrate", or when the user shares a path to a Keep export file.
tools: Read, Write, Edit, Glob, Bash
---

# Obsidian Migrate

Import external notes into the Obsidian vault rooted at the current working directory.

Always read `schema.md` first.

## Google Keep export format

Google Keep exports (via Google Takeout) produce a folder containing:
- `.json` files — one per note, structured data
- `.html` files — rendered versions of the same notes

Prefer `.json` files — they contain the original timestamp, labels, and clean text.

### JSON note structure
```json
{
  "color": "DEFAULT",
  "isTrashed": false,
  "isPinned": false,
  "isArchived": false,
  "textContent": "note body text",
  "title": "optional title",
  "userEditedTimestampUsec": 1234567890000000,
  "labels": [{"name": "label"}],
  "attachments": []
}
```

## Step 1: Locate and parse the export

Ask the user for the export path if not provided. Then:

```bash
ls <export-path>/*.json | head -20
```

Count total notes. Show the user a quick summary: how many notes, date range, labels found.

## Step 2: Filter

Skip notes that are:
- `isTrashed: true`
- Empty (no `textContent` and no `title`)
- Duplicates of content already in the vault (check by title similarity)

Show the user the filter results before proceeding: "Found N notes, skipping N trashed/empty. Ready to migrate N notes."

## Step 3: Create raw files

For each note, create `raw/YYYY-MM-DD/<slug>.md` where:
- Date comes from `userEditedTimestampUsec` (divide by 1,000,000 to get Unix timestamp)
- Slug is derived from the title (if present) or first 5 words of content, lowercase-hyphenated
- Group all notes from the same date into the same `raw/YYYY-MM-DD/` folder

Front matter:
```
---
date: YYYY-MM-DD
source: google-keep
labels: [<keep labels if any>]
---
```

Body: the note's text content, preserved as-is.

**Batch processing**: Process notes in chunks of 20. After each chunk, report progress: "Migrated 20/N notes..."

## Step 4: Ingest into wiki (selective)

Don't create a wiki page for every raw note — that would create noise. Instead, look for patterns across notes:

- Notes with the same label → likely belong in one wiki page
- Notes that mention the same person/place/project repeatedly → entity deserves a wiki page
- Notes that form a coherent topic (e.g., 5 notes about running) → merge into one wiki page

For each wiki page created from migration:
- Synthesize across the source notes rather than copying verbatim
- Link to all contributing raw files in a "Sources" section
- Use the `updated` date of the most recent contributing note

Use your judgment — it's better to under-create wiki pages during migration and let them grow organically than to create dozens of thin stubs.

## Step 5: Update index.md and log.md

Add new wiki pages to `index.md`.

Append a migration summary to `log.md`:
```
## YYYY-MM-DD
- MIGRATE: Google Keep — N notes → N raw files, N wiki pages created/updated
```

## If the export format is different

If the user provides a format other than Google Keep JSON (e.g., HTML export, CSV, another app), read a sample file first and adapt the parsing logic. The goal is the same: preserve the original date, create raw files, selectively build wiki pages.
