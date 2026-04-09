# Obsidian Second Brain — Gemini CLI Context

This extension provides skills for managing an Obsidian knowledge vault.

## Available skills

- **obsidian-ingest** — save URLs, text, ideas, or files into the vault
- **obsidian-query** — answer questions from stored knowledge
- **obsidian-lint** — health check: orphaned pages, broken links, missing index entries
- **obsidian-migrate** — import notes from Google Keep or other export formats
- **obsidian-init** — scaffold a fresh vault with the second-brain structure
- **obsidian-restructure** — upgrade vault from flat raw/ layout to date-subfolder layout

## Vault conventions

Each skill reads `schema.md` in the vault root first. Create this file to describe your folder structure, front matter formats, and naming conventions — the skills adapt to it.

Skills work on the **current working directory** — run Gemini CLI from the vault root.
