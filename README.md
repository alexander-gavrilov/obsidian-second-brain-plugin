# Obsidian Second Brain Plugin

A Claude Code plugin with four skills for managing an [Obsidian](https://obsidian.md) knowledge vault — vault-agnostic, works with any vault structure defined in a `schema.md`.

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

## Vault conventions

Each skill reads `schema.md` in the vault root first. Create this file to describe your folder structure, front matter formats, and naming conventions — the skills adapt to it.

## License

MIT
