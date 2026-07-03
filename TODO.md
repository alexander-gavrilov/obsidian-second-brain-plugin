# Improvement backlog

Notes captured 2026-07-03 from real-world use of the plugin in a live vault
(`knowledge-base/general`). That vault's `.claude/skills/` has drifted ahead
of this repo with fixes that should be upstreamed — see below.

> **Status (2026-07-03):** Items 1 & 2 DONE — shipped in v1.4.0 (commit
> `b34a30b`). Added the `obsidian-daily-note` skill, a work-neutral default
> `templates/raw-note.md`, non-destructive template scaffolding in
> `obsidian-init`, and the quick-capture Step 2c/Step 4 changes. Morning
> briefing (item 2) was already upstreamed prior to this. Spec/plan under
> `docs/superpowers/`. Items 3 & 4 remain open below. A separate future idea:
> transform the plugin into a standalone CLI tool.

## ~~1. Upstream the local `obsidian-quick-capture` divergence~~ ✅ DONE

The vault-local copy at `knowledge-base/general/.claude/skills/obsidian-quick-capture/SKILL.md`
has diverged from `skills/obsidian-quick-capture/SKILL.md` in this repo (still
at the 1.3.0 "Add global/local vault mode" state). Diff and merge these fixes in:

- **Step 2c — scaffold today's note from a template** instead of writing a bare
  file. The local copy calls a new `obsidian-daily-note` skill
  (`python3 .claude/skills/obsidian-daily-note/scripts/create_daily_note.py <date>`)
  that renders the vault's `templates/raw-note.md` (Agenda / Tasks / Daily
  routine / Meeting notes / Captures sections) and carries forward unfinished
  tasks from the prior daily note. This `obsidian-daily-note` skill does not
  exist in this repo at all yet — it needs to be added as vault-agnostic (the
  local version hardcodes a Templater-flavored template; decide how much of
  the template should be configurable via `schema.md` vs. shipped as a
  default).
- Step 4 (append entry) changed to append under a `## 📥 Captures` heading
  instead of at end-of-file, with a legacy fallback for notes that predate
  the heading.
- Hard-constraint note clarifying that scaffolding via `obsidian-daily-note`
  is a sanctioned exception to "quick-capture writes exactly one file."

## ~~2. Add the morning-briefing / daily-digest feature to the global skill~~ ✅ DONE

User feedback (2026-07-03): "Мне нравится дайджест/фокус на новый день, давай
добавим его в скил" — the Step 2b "morning briefing" in the local
`obsidian-quick-capture` (reads `log.md` tail, all `wiki/projects/*`, and
yesterday's input file, then produces an Active Projects / Captured Yesterday
/ Suggested Focus / Worth Keeping in Mind briefing) is well-liked and should
be promoted from a vault-local addition into the shipped skill, alongside
item 1's template-scaffolding.

## 3. Reconcile local vs. global skill versions generally

Beyond quick-capture specifically: there's no process today for noticing when
a per-vault `.claude/skills/` copy has been patched ahead of this repo's
`skills/`. Worth designing:
- A lint/diff check (maybe an `obsidian-lint` extension, or a standalone
  script) that flags when a vault's local skill copy differs from the
  installed plugin version.
- A lightweight upstream workflow so fixes made live, in a vault, get ported
  back here instead of silently diverging (this TODO doc is today's manual
  version of that).

## 4. Scope model: not all skills need the same vault-resolution rules

Current `Step 0: Resolve vault` logic is identical across every skill (ask if
both local+global are present, otherwise pick whichever is configured).
Feedback (2026-07-03): this is wrong for some skills.

- **User-scope skills** (`obsidian-quick-capture`, `obsidian-query`) are
  meant to be invoked from anywhere — a quick capture or a question shouldn't
  require `cd`-ing into the knowledge-base directory first. These should
  default to the global vault silently when no local vault is present,
  without the "ask which one" friction, since the whole point is speed.
- **Knowledge-base-scope skills** (`obsidian-ingest`, `obsidian-lint`,
  `obsidian-migrate`, `obsidian-restructure`, `obsidian-init`) are heavier
  maintenance operations that make sense only when working within the vault
  project itself — these should keep requiring (or assuming) local scope.

Action: split `Step 0` into two variants and apply the right one per skill
per the categorization above, rather than one-size-fits-all vault resolution.
