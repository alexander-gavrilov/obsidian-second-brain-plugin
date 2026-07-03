# Upstream `obsidian-daily-note`, decouple the template from work tooling

**Date:** 2026-07-03
**Status:** Approved design, ready for planning
**Scope:** TODO items 1 & 2 (upstream the daily-note skill and quick-capture
divergence; ship a vault-agnostic default template). TODO items 3 (local↔global
reconciliation process) and 4 (per-skill scope model for Step 0) are explicitly
**deferred to future specs** and out of scope here. A longer-term idea to
transform the plugin into a standalone CLI tool is noted but not addressed.

## Problem

The live vault `knowledge-base/general`
(`github.com/aliaksandr-haurylau-godel/knowledge-base-general`) has drifted ahead
of this plugin repo with fixes made during real-world use:

1. A new skill **`obsidian-daily-note`** (SKILL.md + `scripts/create_daily_note.py`)
   that renders the vault's `templates/raw-note.md` outside Obsidian (Templater
   only runs inside Obsidian), carries unfinished tasks forward, and offers a
   read-only `--recollect` scan. **This skill does not exist in the plugin at all.**
2. **`obsidian-quick-capture`** diverged: Step 2c now scaffolds today's note from
   the template via `obsidian-daily-note` instead of writing a bare file; Step 4
   appends under a `## 📥 Captures` heading (with a legacy fallback); a hard-constraint
   note sanctions the scaffolding as the one allowed file creation.

Two coupling problems block a clean upstream:

- **Work-tool coupling lives in vault content, not skill code.** The only
  Outlook/Teams-specific material is the `## ✅ Daily routine` checklist inside
  `templates/raw-note.md` ("Read Teams Messages", "Check Task Tracker"). The
  `create_daily_note.py` script is already vault-agnostic — it renders whatever
  template the vault holds. The `## 📅 Agenda` block is **calendar-agnostic**: it
  reads events via the Obsidian `ics` community plugin, whose feed source (Outlook
  vs. Google Calendar) is configured inside Obsidian, not in the template. So the
  same template works at work and at home; only the ICS feed URL differs, and that
  is an Obsidian-side setting outside this plugin.
- **The plugin ships no template at all.** `obsidian-init` scaffolds
  `schema.md`, `index.md`, `log.md`, `raw/`, `wiki/` but never
  `templates/raw-note.md`. On a fresh plugin-initialized vault, `obsidian-daily-note`
  would fail with "template not found".

## Design

### 1. Add the `obsidian-daily-note` skill to the plugin

Copy the vault's `obsidian-daily-note` skill into `skills/obsidian-daily-note/`
(SKILL.md + `scripts/create_daily_note.py`). The script logic is already
vault-agnostic and needs no behavioral change. One required fix:

- **Plugin-aware script path.** SKILL.md and quick-capture Step 2c currently invoke
  the vault-local path `.claude/skills/obsidian-daily-note/scripts/create_daily_note.py`.
  When installed as a plugin the script lives under
  `~/.claude/plugins/marketplaces/obsidian-second-brain/skills/obsidian-daily-note/scripts/`.
  The invocation must resolve the script in both locations, preferring the installed
  plugin copy. (The other plugin skills already reference the
  `~/.claude/plugins/marketplaces/obsidian-second-brain/skills/...` path — follow that
  convention.)

Keep the `model: haiku` frontmatter and all existing behavior (weekday-aware
routine rendering, task carry-forward, `--recollect`, `--force`, refuse-to-clobber,
`UNRENDERED:` fail-loud).

### 2. Ship a neutral default template

Add `templates/raw-note.md` to the plugin as the shipped default. It mirrors the
vault's template **except** the routine checklist is de-worked:

- Keep the `## 📅 Agenda` `dataviewjs` ICS block **verbatim** — it is
  calendar-agnostic and degrades gracefully ("_ICS plugin not enabled._") when the
  `ics`/`dataview` community plugins are absent.
- Replace the work-specific `## ✅ Daily routine` items with neutral ones, e.g.:
  ```
  - [ ] 📆 Check calendar
  - [ ] 📥 Check inboxes
  - [ ] 🎛️ Check tasks
  ```
- Keep the `## ✅ Tasks`, `## 📝 Meeting notes`, and `## 📥 Captures` sections and
  the weekday `<%* %>` conditional structure the script expects.
- Add a short comment documenting that the calendar source (Outlook, Google
  Calendar, etc.) is configured in Obsidian's `ics` plugin settings, not here.

Customization model = **variant 1**: one neutral default; each vault edits its own
`templates/raw-note.md` by hand (work vault re-adds Teams/Task-Tracker, home vault
leaves it generic). No config-assembly, no preset files — the template file itself
remains the single source of truth, which is what the script relies on.

### 3. Template handling in `obsidian-init`

`obsidian-init` gains template scaffolding. Behavior:

- **No `templates/raw-note.md` in the target vault** → copy the plugin's neutral
  default into `templates/raw-note.md`. No prompt.
- **Existing `templates/raw-note.md` identical to the plugin default** → do nothing,
  proceed silently.
- **Existing `templates/raw-note.md` differs from the plugin default** → do not
  overwrite silently. Offer three choices:
  1. **Keep existing** (default) — leave the vault's file untouched.
  2. **Use plugin default** — overwrite with the shipped neutral template. Before
     overwriting, back up the current file to `templates/raw-note.md.bak`.
  3. **Interactive hybrid** — read both the existing file and the plugin default,
     interactively assemble a merged template (e.g. keep the user's Agenda block and
     sections, adjust the routine for this vault), show the proposed result before
     writing, and back up the original to `templates/raw-note.md.bak`.

Record the template action in `log.md` alongside the existing scaffold entry.

### 4. Upstream the `obsidian-quick-capture` divergence

Port the three vault-local changes into `skills/obsidian-quick-capture/SKILL.md`:

- **Step 2c** — scaffold today's note from the template via `obsidian-daily-note`'s
  script (plugin-aware path per §1) instead of creating a bare file.
- **Step 4** — append the entry under the `## 📥 Captures` heading, with the legacy
  fallback for notes predating that heading (add the heading at end-of-file first,
  then append under it).
- **Hard-constraint note** — clarify that scaffolding via `obsidian-daily-note` is the
  sanctioned exception to "quick-capture writes exactly one file."

The Step 2b morning briefing is **already present** in the plugin's quick-capture
(TODO item 2 is effectively already upstreamed) — no change needed there.

### 5. `obsidian-daily-note` fallback when no template exists

To avoid duplicating the template-choice logic in two places: when
`obsidian-daily-note` runs in a vault that has no `templates/raw-note.md`, it does
**not** build or choose a template. It stops and directs the user to run
`obsidian-init`. (Per user decision: keep this behavior simple.)

## Out of scope (future specs)

- **TODO 3** — a lint/diff tool (`scripts/skill-diff.py`) to detect when a vault's
  local `.claude/skills/` copies drift from the plugin, plus a documented "don't
  vendor plugin skills into vaults" workflow.
- **TODO 4** — splitting Step 0 "Resolve vault" into user-scope (silent global) vs.
  kb-scope (local) variants per skill.
- Transforming the plugin into a standalone CLI tool.

## Versioning

Bump `.claude-plugin/plugin.json` from `1.3.0` → `1.4.0` on the shipping commit
(new skill + new default template + init behavior). Per the standing rule, the
version bump ships in the same commit as the skill changes.

## What good looks like

- A fresh vault created via `obsidian-init` has a working `templates/raw-note.md`
  and `obsidian-daily-note` renders it with no "template not found" error.
- Re-running `obsidian-init` on the live `knowledge-base/general` vault leaves its
  customized template intact (keep-existing default), never silently clobbering it.
- The shipped default carries no Teams/Task-Tracker wording; the Agenda block works
  against either an Outlook or a Google Calendar ICS feed with only an Obsidian-side
  setting change.
- `obsidian-quick-capture` on the plugin behaves like the vault-local copy
  (template scaffold + Captures-heading append).
