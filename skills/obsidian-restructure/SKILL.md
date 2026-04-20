---
name: obsidian-restructure
description: Migrate an existing Obsidian vault from the old flat raw/ structure (raw/YYYY-MM-DD-title.md) to the new date-folder structure (raw/YYYY-MM-DD/title.md). Use this skill when the user wants to restructure an existing vault, upgrade to the new raw folder layout, or migrate multiple vaults. Trigger on phrases like "migrate my vault structure", "restructure raw folder", "upgrade my vault", "convert to date folders".
tools: Read, Write, Edit, Glob, Grep, Bash
---

# Obsidian Restructure

## Step 0: Resolve vault

1. Check if a local vault exists: does `schema.md` exist in the current working directory?
2. Read `~/.claude/obsidian-second-brain-config.json` (if it exists) to get `global_vault_path`.

**Decision:**
- Local present + global configured → ask: *"Restructure the global vault (at `<global_path>`) or the local one (current directory)?"*
- Local present + no global configured → use local, no prompt
- No local + global configured → use global path silently
- No local + no global → stop: *"No vault found here and no global vault is configured. Run `obsidian-configure` to set one up."*

All file operations below use the resolved vault root.

---

Migrate an existing vault's `raw/` folder from the old flat layout to the new date-folder layout, and update all internal links accordingly.

**Old format:** `raw/YYYY-MM-DD-short-title.md`
**New format:** `raw/YYYY-MM-DD/short-title.md`

Always read `schema.md` first to understand the vault's conventions.

## Step 1: Audit the vault

Find all flat raw files that need to be moved:

```
Glob: raw/*.md
```

Also check if any files are already in date folders (partially migrated vaults):

```
Glob: raw/**/*.md
```

Report to the user:
- Total flat files found (old format)
- Total already in date folders (already migrated)
- Date range of the flat files
- Estimated number of date folders that will be created

Ask the user to confirm before proceeding: "Found N files to migrate spanning YYYY-MM-DD to YYYY-MM-DD. This will create N date folders and update all internal links. Proceed?"

## Step 2: Move raw files into date folders

For each file matching `raw/YYYY-MM-DD-*.md`:

1. Parse the date prefix: extract `YYYY-MM-DD` from the filename
2. Derive the new slug: strip the date prefix and the leading hyphen (e.g., `2024-03-15-my-article.md` → slug is `my-article`)
3. Create the date folder if it doesn't exist:
   ```bash
   mkdir -p raw/YYYY-MM-DD
   ```
4. Move the file:
   ```bash
   mv raw/YYYY-MM-DD-slug.md raw/YYYY-MM-DD/slug.md
   ```

**Handle slug collisions**: if `raw/YYYY-MM-DD/slug.md` already exists, append `-2`, `-3`, etc. to the new filename and note the rename.

Process in batches of 20 and report progress: "Moved 20/N files..."

## Step 3: Update all internal links

After all files are moved, scan every `.md` file in the vault for links using the old format and rewrite them:

**Pattern to find:** `[[raw/YYYY-MM-DD-slug]]` or `[[raw/YYYY-MM-DD-slug|alias]]`

**Replacement:** `[[raw/YYYY-MM-DD/slug]]` or `[[raw/YYYY-MM-DD/slug|alias]]`

Files to scan:
```
Glob: wiki/**/*.md
Glob: index.md
Glob: log.md
```

For each file containing old-format raw links:
1. Read the file
2. Replace all occurrences of the old link pattern with the new format
3. Write the updated file

Report which files were updated and how many links were rewritten.

## Step 4: Update schema.md

If `schema.md` still describes the old flat format, update the Raw Notes section to reflect the new date-folder convention:

- Old: `Named: YYYY-MM-DD-short-title.md`
- New: `Organized by date: raw/YYYY-MM-DD/<short-title>.md`

## Step 5: Verify

Run a quick sanity check after migration:

1. Confirm no `.md` files remain in `raw/` root (they should all be in date folders):
   ```
   Glob: raw/*.md
   ```
   If any remain, report them — they may be files that didn't match the `YYYY-MM-DD-` prefix pattern (e.g., a readme or index in raw/).

2. Confirm no broken old-format links remain:
   ```
   Grep pattern: \[\[raw/\d{4}-\d{2}-\d{2}-  in wiki/, index.md, log.md
   ```

3. Report any anomalies found.

## Step 6: Append to log.md

```
## YYYY-MM-DD
- RESTRUCTURE: migrated N raw files to date-folder layout, updated N links across N wiki pages
```

## Edge cases

- **Files without date prefix** (e.g., `raw/readme.md`): leave in place, report to user
- **Already-migrated files** in `raw/YYYY-MM-DD/`: skip, don't touch
- **Media files** (`.png`, `.jpg`, `.pdf`, etc.) in `raw/` root: move to `raw/YYYY-MM-DD/` using the file's modification date if no date prefix is present; report these separately
- **Multiple vaults**: if the user has multiple vaults, run this skill once per vault (each in its own working directory)
