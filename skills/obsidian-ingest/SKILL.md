---
name: obsidian-ingest
description: Process and ingest raw content into an Obsidian knowledge vault. Use this skill whenever the user shares something to save, file, or remember — URLs, articles, pasted text, ideas, notes, or file paths. Trigger on phrases like "ingest this", "save this to my vault", "add this to my brain", "file this", "remember this", "add a note about", "I want to keep this", or when the user simply pastes a URL or chunk of text and seems to want it stored.
tools: Read, Write, Edit, WebFetch, Glob, Grep, Bash
---

# Obsidian Ingest

Process raw content into the Obsidian vault rooted at the current working directory.

Always read `schema.md` first — it defines the vault's conventions, folder structure, and front matter formats.

## Step 1: Determine input type

The user will provide one of:
- **URL** — fetch the content with WebFetch
- **Pasted text** — use as-is
- **File path** — read the file

If the input is ambiguous, make a reasonable guess rather than asking.

## Step 2: Check for duplicates, then create the raw file

Before creating anything, check if this source was already ingested:
- For URLs: `Grep source: <url>` across `raw/` — if found, update the existing wiki pages instead of creating a new raw file, and note the update in log.md
- For pasted text: scan raw titles for obvious overlap, but err on the side of creating rather than skipping

If a duplicate is found, tell the user and proceed to update the relevant wiki pages with any new information.

Create a file in `raw/` named `YYYY-MM-DD-short-title.md` using today's date. The title should be 2-5 words, lowercase-hyphenated, descriptive of the content (not generic like "note" or "article").

Front matter:
```
---
date: YYYY-MM-DD
source: <url | "personal" | "file:<path>" | "google-keep">
tags: [<2-4 relevant tags>]
---
```

Write a clean, faithful summary of the content under the front matter. For URLs: summarize the key ideas, not just headlines. For personal notes: preserve the content verbatim or lightly formatted. Keep it concise — this is the immutable source record, not the wiki page.

## Step 3: Extract entities

Scan the content for named entities worth tracking:
- **People** — named individuals worth remembering
- **Concepts** — ideas, frameworks, terms that have depth
- **Projects** — specific initiatives or efforts
- **Places** — locations worth remembering
- **Topics** — recurring themes that don't fit the above

Be selective. Not every noun needs a wiki page. Ask: "would this entity accumulate more information over time?" If yes, it deserves a page.

## Step 4: Create or update wiki pages

For each entity identified:

1. **Check if a page exists** using Glob: `wiki/<category>/<entity-name>.md`
2. **If it exists**: read it and append or integrate new information. Don't duplicate what's already there — add only what's new. Update the `updated` date in front matter.
3. **If it doesn't exist**: create it.

### Wiki page format

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
- Include a "Sources" section at the bottom linking back to the raw file(s): `[[raw/YYYY-MM-DD-title]]`
- Keep it dense and scannable — use headers for longer pages, bullet points for lists of facts

## Step 5: Update index.md

For any **newly created** wiki pages (not updates), add an entry to the appropriate section in `index.md`:

```
- [[wiki/category/page-name]] — one-line description
```

Don't add entries for existing pages that were just updated.

## Step 6: Append to log.md

Add an entry at the bottom of `log.md`:

```
## YYYY-MM-DD
- INGEST: <short-title> → created raw/YYYY-MM-DD-short-title, [created|updated] wiki/<pages>
```

If a log entry for today already exists, append to it rather than creating a duplicate header.

## What good looks like

- Raw file is a faithful, concise record of the original content
- Wiki pages feel like reference articles — useful to read cold, not just a dump of facts
- Cross-links connect related entities (a person links to a project they're involved in, a concept links to books that explain it)
- index.md and log.md are always in sync with what was created
