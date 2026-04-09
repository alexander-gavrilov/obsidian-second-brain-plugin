# Obsidian Second Brain Plugin

A Claude Code plugin and Gemini CLI extension with skills for managing an [Obsidian](https://obsidian.md) knowledge vault — vault-agnostic, works with any vault structure defined in a `schema.md`.

## Install

**Claude Code:**
```
/plugin install alexander-gavrilov/obsidian-second-brain-plugin
```

**Gemini CLI:**
```
gemini extensions add alexander-gavrilov/obsidian-second-brain-plugin
```

## Skills

### `obsidian-ingest`
Save anything to your vault — URLs, pasted text, ideas, files. Fetches content, creates a raw note, extracts entities, and creates or updates wiki pages.

**Trigger:** "ingest this", "save this to my vault", "remember this", or paste a URL.

### `obsidian-query`
Answer questions from your stored knowledge. Searches wiki pages and raw notes, cites sources, and distinguishes vault knowledge from general knowledge.

**Trigger:** "what do I know about X", "find my notes on X", "remind me about X".

### `obsidian-lint`
Health check for your vault — finds missing index entries, orphaned pages, broken links, recurring entities without wiki pages, and stale pages.

**Trigger:** "lint the vault", "audit my notes", "check vault health".

### `obsidian-migrate`
Import notes from Google Keep (or other sources) via export files. Filters, creates raw notes, selectively builds wiki pages.

**Trigger:** "migrate my Keep notes", "import this export", share a path to a Keep export folder.

### `obsidian-init`
Scaffold a fresh vault with the second-brain structure — interviews you on categories, creates folder layout, writes `schema.md`.

**Trigger:** "set up my vault", "initialize this vault", "create my second brain".

### `obsidian-restructure`
Migrate an existing vault from the old flat `raw/` layout (`raw/YYYY-MM-DD-title.md`) to the date-folder layout (`raw/YYYY-MM-DD/title.md`), updating all internal links.

**Trigger:** "restructure raw folder", "upgrade my vault", "convert to date folders".

## Vault conventions

Each skill reads `schema.md` in the vault root first. Create this file to describe your folder structure, front matter formats, and naming conventions — the skills adapt to it.

## Development

### Eval workspace

`obsidian-skills-workspace/` contains skill evaluation runs used to verify the `raw/` date-folder restructure (2026-04-09):

- `evals/evals.json` — test cases and assertions
- `iteration-1/` — first run (shared vaults between with/without_skill; baseline for eval 1 invalid)
- `iteration-2/` — fixed run (separate vaults; old `schema.md` used for eval 2 to test skill override)

**Key findings:**
- Skills correctly produce `raw/YYYY-MM-DD/` structure in all cases
- With an outdated `schema.md`, `obsidian-ingest` is the only mechanism enforcing the new convention (baseline falls back to old flat format)
- `obsidian-restructure` reliably adds the `RESTRUCTURE` log entry; baseline consistently skips it

To run future evals, use separate vault copies per agent to avoid contamination.

## License

MIT
