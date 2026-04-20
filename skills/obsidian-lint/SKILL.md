---
name: obsidian-lint
description: Run a health check on an Obsidian knowledge vault. Use this skill when the user asks to lint, audit, clean up, or check the vault. Trigger on phrases like "lint the vault", "check vault health", "audit my notes", "find orphaned pages", "clean up my brain", "what's missing from the index", or periodically when the user says "let's do some maintenance".
tools: Read, Glob, Grep, Edit
---

# Obsidian Lint

## Step 0: Resolve vault

1. Check if a local vault exists: does `schema.md` exist in the current working directory?
2. Read `~/.claude/obsidian-second-brain-config.json` (if it exists) to get `global_vault_path`.

**Decision:**
- Local present + global configured → ask: *"Lint globally (at `<global_path>`) or locally (current directory)?"*
- Local present + no global configured → use local, no prompt
- No local + global configured → use global path silently
- No local + no global → stop: *"No vault found here and no global vault is configured. Run `obsidian-configure` to set one up."*

All file operations below use the resolved vault root.

---

Audit the Obsidian vault and report issues.

Always read `schema.md` first.

## What to check

Run all checks, then produce a single consolidated report before making any changes.

### 1. Index completeness
Find all wiki pages and verify each has an entry in `index.md`.

```
Glob: wiki/**/*.md
```

For each page found, check if its path appears in `index.md`. Missing entries are a lint error.

### 2. Orphaned pages
Find wiki pages with no inbound `[[links]]` from any other file (wiki pages, index.md, or raw notes).

A page is orphaned if no other file contains `[[wiki/category/page-name]]` or any reasonable variant. Orphaned pages aren't always wrong (some topics are standalone) but they should be flagged.

### 3. Missing wiki pages for recurring entities
Scan raw notes and wiki pages for entity names that appear in 3+ files but don't have their own wiki page. These are candidates for promotion — they've accumulated enough mentions to justify a dedicated page.

To scan raw notes use `Glob: raw/**/*.md` (covers the date-folder structure).

### 4. Stale pages
Flag wiki pages whose `updated` front matter date is older than 6 months. These may need review — not necessarily wrong, but worth knowing about.

### 5. Broken links
Scan all files for `[[links]]` that point to paths that don't exist. These are broken references.

For raw file links, the expected format is `[[raw/YYYY-MM-DD/title]]` (date folder, not date prefix). Flag any links still using the old `[[raw/YYYY-MM-DD-title]]` flat format as broken.

### 6. Log gaps
Check if `log.md` has entries for the approximate period when wiki pages were created (based on `updated` dates). Large gaps suggest activity that wasn't logged.

## Report format

Output a structured report before asking to fix anything:

```
## Vault Lint Report — YYYY-MM-DD

### Summary
- Wiki pages: N
- Index entries: N (missing: N)
- Orphaned pages: N
- Broken links: N
- Recurring entities without pages: N
- Stale pages (>6mo): N

### Issues

#### Missing from index.md
- wiki/category/page → suggested index entry

#### Orphaned pages
- wiki/category/page — no inbound links found

#### Broken links
- wiki/category/page:line — [[broken-link]]

#### Recurring entities without pages
- "Entity Name" — mentioned in: raw/..., wiki/..., wiki/...

#### Stale pages
- wiki/category/page — last updated YYYY-MM-DD
```

## Fixes

After presenting the report, ask: "Want me to fix these?"

Apply fixes in this order:
1. Add missing `index.md` entries
2. Fix broken links (prompt user if the correct target is ambiguous)
3. Create stub pages for recurring entities (a minimal page with a note to expand)

Don't auto-fix orphaned pages or stale pages — those need human judgment. Just report them.

Append to `log.md`:
```
- LINT: found N issues, fixed N
```
