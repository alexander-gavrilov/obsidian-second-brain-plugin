---
name: obsidian-init
description: Initialize a new Obsidian knowledge vault with the second-brain structure. Use this skill when the user wants to set up a new vault, scaffold a fresh knowledge base, or prepare a directory for use with the obsidian-ingest/query/lint/migrate skills. Trigger on phrases like "set up my vault", "initialize this vault", "create my second brain", "scaffold my notes", "new vault setup", or when the user is in an empty directory and wants to start taking notes with Claude.
tools: Read, Write, Bash, Glob
---

# Obsidian Init

Set up a fresh Obsidian second-brain vault.

The vault structure follows the LLM Wiki pattern: raw inputs are preserved as-is, then processed into a living, interlinked wiki. The `schema.md` you create here is the instruction manual for the vault — every other skill reads it first.

## Step 0: Choose init mode

Read `~/.claude/obsidian-second-brain-config.json` (if it exists) to check whether a global vault is already configured.

Ask the user:

> "Initialize a **local vault** here (in the current directory — useful for project-specific notes) or set up your **global vault** (a single personal vault used across all projects)?"

**Local mode**: proceed with the current working directory as the vault root. Skip to Step 1.

**Global mode**:
- If a global vault is already configured at `<path>`: confirm *"Your global vault is already at `<path>`. Re-initialize it? This will not delete existing content, but will rewrite `schema.md`."*
- If no global is configured: ask for the path — *"Where should your global vault live? Enter an absolute path (it can be a new or existing directory)."*
  - If the directory doesn't exist: create it with `mkdir -p <path>`
  - Set this as the vault root for all steps below
  - After completing init, save the path to `~/.claude/obsidian-second-brain-config.json`:
    ```json
    { "global_vault_path": "<absolute_path>" }
    ```
  - Confirm: *"Global vault initialized at `<path>` and saved as your default."*

---

## Step 1: Interview the user

Before creating anything, ask a few quick questions to shape the vault for their situation:

1. **What's this vault for?** (personal life, work, a specific project, research, etc.)
2. **Which categories make sense?** Suggest the default set and let them add, remove, or rename:
   - `health/` — fitness, diet, habits, medical
   - `people/` — contacts, relationships
   - `finance/` — budget, accounts, goals
   - `learning/` — books, courses, ideas, concepts
   - `projects/` — personal projects, hobbies
   - `places/` — travel, restaurants, locations
   - `work/` — professional notes
3. **Vault owner name?** (used to personalize schema.md)

Keep it conversational — if they say "just personal stuff" that's enough to proceed. Don't interrogate them. Make reasonable inferences and confirm with a brief summary before writing anything.

## Step 2: Create the folder structure

```bash
mkdir -p raw
mkdir -p wiki/<category1> wiki/<category2> ...
```

Create only the `wiki/` subdirectories they actually want. Don't create empty placeholders — the folders are enough.

## Step 3: Write schema.md

`schema.md` is the vault's instruction manual. Every LLM working in this vault reads it first. Tailor it to the vault's actual purpose and categories.

Template structure:

```markdown
# Vault Schema

This file is the instruction manual for this vault. Any LLM working on this vault should read this file first.

## Purpose

<1-2 sentences describing the vault's purpose and owner>

## Folder Structure

\`\`\`
<vault-name>/
├── schema.md       ← this file; read before doing anything
├── index.md        ← content catalog organized by category
├── log.md          ← append-only chronological activity log
├── raw/            ← immutable raw inputs organized by date (raw/YYYY-MM-DD/)
└── wiki/           ← living knowledge pages, LLM-maintained
    ├── <category1>/
    ├── <category2>/
    └── ...
\`\`\`

## Raw Notes (`raw/`)

- Organized by date: `raw/YYYY-MM-DD/<short-title>.md`
- One folder per day; each file within is one input (article, idea, clipping, etc.)
- Media files (images, PDFs, audio, video) live in the same date folder alongside their `.md` companion
- Never edited after creation — they are the source of truth
- Front matter:
  \`\`\`
  ---
  date: YYYY-MM-DD
  source: url | "personal" | "google-keep" | etc.
  tags: [tag1, tag2]
  ---
  \`\`\`

## Wiki Pages (`wiki/`)

- One page per entity: person, concept, project, place, topic
- Named in lowercase with hyphens: `wiki/people/john-doe.md`
- Use `[[wiki links]]` to cross-reference other pages
- Front matter:
  \`\`\`
  ---
  type: person | concept | project | place | topic | event
  updated: YYYY-MM-DD
  ---
  \`\`\`
- Pages are updated in place as new information arrives — they grow over time
- Strive for dense cross-linking; every named entity that has a page should be linked

## Categories

| Folder | What goes here |
|--------|---------------|
<one row per category>

## Operations

### Ingest
When given a raw input (article, note, idea, or media file):
1. Create `raw/YYYY-MM-DD/` for today's date and place the file inside it
2. Identify entities mentioned (people, concepts, projects, places)
3. Create or update the relevant wiki pages
4. Add a link to the raw source in each updated wiki page
5. Update `index.md` if new pages were created
6. Append a line to `log.md`

### Query
When asked a question:
1. Answer from the wiki
2. If the answer is novel and worth keeping, file it as a new wiki page or update an existing one
3. Append to `log.md`

### Lint (periodic)
Check for:
- Orphaned wiki pages (not linked from anywhere)
- Contradictions between pages
- Stale pages that haven't been updated in a long time
- Entities mentioned in multiple pages that should have their own page but don't
- `index.md` entries missing for existing wiki pages

## Linking Conventions

- Always use `[[relative/path]]` style Obsidian wiki links
- Link on first mention within a page, not every mention
- `index.md` links to all wiki pages; wiki pages link to each other and back to raw sources

## index.md Format

Organized by category. Each line: `- [[path/to/page]] — one-line description`

## log.md Format

Append-only. Each entry:
\`\`\`
## YYYY-MM-DD
- ACTION: description
\`\`\`
Actions: `INGEST`, `CREATE`, `UPDATE`, `QUERY`, `LINT`, `MIGRATE`
```

Adapt the Purpose section and Categories table to the user's actual answers. Keep everything else consistent — the other skills depend on this exact structure.

## Step 4: Write index.md

```markdown
# Index

Content catalog. Every wiki page should have an entry here.
See [[schema]] for structure and conventions.

## <Category1>
<!-- wiki/<category1>/ pages -->

## <Category2>
<!-- wiki/<category2>/ pages -->

...
```

One `##` section per category. Leave them empty (just the comment placeholder) — they'll fill up as the user ingests content.

## Step 5: Write log.md

```markdown
# Log

Append-only activity record. See [[schema]] for format.

## YYYY-MM-DD
- CREATE: vault scaffold — schema, index, log, raw/, wiki/ with categories (<list>)
```

Use today's actual date for the first log entry.

## What good looks like

The user ends up with a vault that:
- Has a `schema.md` they could hand to any LLM and it would understand the vault
- Has directories that match their actual use case (no useless empty folders)
- Is immediately ready for `/ingest`, `/query`, `/lint`, and `/migrate` — no further setup needed

If the user already has some content in the directory (existing `.md` files), don't overwrite anything. Instead, adapt the schema to match what's already there and note what you found.
