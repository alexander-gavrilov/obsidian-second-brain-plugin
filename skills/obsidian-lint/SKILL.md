---
name: obsidian-lint
description: Run a health check on an Obsidian knowledge vault. Use this skill when the user asks to lint, audit, clean up, or check the vault. Trigger on phrases like "lint the vault", "check vault health", "audit my notes", "find orphaned pages", "clean up my brain", "what's missing from the index", or periodically when the user says "let's do some maintenance".
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Obsidian Lint

## Step 0: Resolve vault

Run the shared resolver (`${CLAUDE_PLUGIN_ROOT}/scripts/resolve_vault.py`; if that variable is unset use `~/.claude/plugins/marketplaces/obsidian-second-brain/scripts/resolve_vault.py`):

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/marketplaces/obsidian-second-brain}/scripts/resolve_vault.py"
```

It prints `root=`, `mode=`, `local=`, `global=`. Exit code 2 means no vault is available: stop and tell the user to run `obsidian-configure` (or `obsidian-init` to create one here).

- `mode=single` (including when the current directory *is* the global vault) -> use `root`, never prompt.
- `mode=ambiguous` (a local vault and a different global vault) -> ask once per session: *"Lint global (at `<global>`) or local (`<local>`)?"* Use the answer as the root.

All file operations below use `root`.

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

### 6. Contradictions
Look for pages that state conflicting facts about the same entity (dates, amounts, ownership, status) — typically a wiki page versus a newer raw note or another wiki page. Report both locations and the conflicting claims; don't resolve them yourself.

### 7. Task maintenance
Applies only if the vault has `tasks/`. Rules are in `schema.md` (Lint > Task maintenance) and `conductor/task-storage-spec.md` §3.2 and §7 — follow those; summary:
- **Rollover**: move every `tasks/scheduled.md` line whose `due:` is today or earlier into `tasks/today.md` (`## Overdue`, oldest first, or `## Due Today`); remove emptied date headers; log `LINT: rolled over N tasks from scheduled.md to today.md`.
- **Archive**: remove `tasks/done.md` lines completed 30+ days ago and log one flat `TASK_ARCHIVE: N tasks archived (30+ days done): "<description>" (completed: YYYY-MM-DD), ... → log.md` line (descriptions verbatim).
- **Duplicates**: no task may appear in more than one of `today.md` / `scheduled.md` / `someday.md`; also flag near-duplicates within a file.
- **Moot tasks**: flag tasks that look obsolete (cancelled plan, already done elsewhere) for the user to confirm; cancel only with the user's go-ahead, via `TASK_CANCEL`.

### 8. Log gaps
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
- Contradictions: N
- Tasks: N rolled over, N to archive, N duplicates, N possibly moot

### Issues

#### Missing from index.md
- wiki/category/page → suggested index entry

#### Orphaned pages
- wiki/category/page — no inbound links found

#### Broken links
- wiki/category/page:line — [[broken-link]]

#### Recurring entities without pages
- "Entity Name" — mentioned in: raw/..., wiki/..., wiki/...

#### Contradictions
- wiki/a vs wiki/b — "claim A" vs "claim B"

#### Tasks
- rollover / archive / duplicate / moot candidates

#### Stale pages
- wiki/category/page — last updated YYYY-MM-DD
```

## Fixes

After presenting the report, ask: "Want me to fix these?"

Apply fixes in this order:
1. Add missing `index.md` entries
2. Fix broken links (prompt user if the correct target is ambiguous)
3. Create stub pages for recurring entities (a minimal page with a note to expand)

Task rollover and archive are mechanical and may be applied with the other fixes. Don't auto-fix orphaned pages, stale pages, contradictions or moot tasks — those need human judgment. Just report them.

Append to `log.md`:
```
- LINT: found N issues, fixed N
```
