# Obsidian Second Brain — Gemini CLI Context

This extension provides skills for managing an Obsidian knowledge vault.

## Available skills

- **obsidian-ingest** — process content, `input/` files and `incoming/` backlogs into raw notes, wiki pages, tasks
- **obsidian-query** — answer questions from stored knowledge
- **obsidian-quick-capture** — fast capture into the daily input file (no processing)
- **obsidian-lint** — health check: orphans, broken links, index gaps, contradictions, task maintenance
- **obsidian-migrate** — import notes from Google Keep or other export formats
- **obsidian-init** — scaffold a fresh vault with the second-brain structure
- **obsidian-restructure** — upgrade vault from flat raw/ layout to date-subfolder layout
- **obsidian-daily-note** — scaffold a daily note from the vault template, carrying unfinished tasks forward
- **obsidian-park-session** — summarize and park current work session to a note
- **obsidian-configure** — configure global Obsidian vault path

## Vault conventions

Each skill reads `schema.md` in the vault root first. Create this file to describe your folder structure, front matter formats, and naming conventions — the skills adapt to it.

Skills work on the **current working directory** — run Gemini CLI from the vault root.

Skills locate the shared vault resolver at `scripts/resolve_vault.py` in this extension's directory (`${CLAUDE_PLUGIN_ROOT}` under Claude Code); when running under Gemini CLI use that path relative to the extension install.
