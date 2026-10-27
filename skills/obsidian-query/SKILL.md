---
name: obsidian-query
description: Query an Obsidian knowledge vault to answer questions from stored knowledge. Use this skill when the user asks about something they might have saved, wants to recall information, or asks "what do I know about X", "find my notes on X", "do I have anything about X", "remind me about X", "what did I save about X". Also trigger when the user asks a question that seems like it could be answered from their notes rather than general knowledge.
allowed-tools: Read, Glob, Grep, Write, Edit, Bash
---

# Obsidian Query

## Step 0: Resolve vault

Run the shared resolver (`${CLAUDE_PLUGIN_ROOT}/scripts/resolve_vault.py`; if that variable is unset use `~/.claude/plugins/marketplaces/obsidian-second-brain/scripts/resolve_vault.py`):

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/marketplaces/obsidian-second-brain}/scripts/resolve_vault.py"
```

It prints `root=`, `mode=`, `local=`, `global=`. Exit code 3 means no vault is available (exit 2 means the script itself was not found — check the path): stop and tell the user to run `obsidian-configure` (or `obsidian-init` to create one here).

- `mode=single` -> use `root`, no prompt.
- `mode=ambiguous` -> answer from the **local** vault (`root`); do not ask up front. Step 2.5 then offers the global one.

Remember whether `mode` was `ambiguous` — Step 2.5 only runs in that case.

All file operations below use `root`.

---

Answer questions using the Obsidian vault.

Always read `schema.md` first to understand the vault structure.

## Step 1: Search the vault

Use multiple strategies in parallel to find relevant content:

**Search wiki pages by keyword:**
```
Grep pattern in wiki/ directory
```

**Search by likely page location** — if the question is about a person, check `wiki/people/`; a book, check `wiki/learning/`; etc.

**Search raw notes** if wiki pages come up empty — the user may have ingested something without it being fully processed into the wiki. Raw notes live under `raw/YYYY-MM-DD/` folders; use `Grep pattern in raw/` or `Glob: raw/**/*.md` to search across all dates.

Cast a wide net at first, then narrow. A question about "my gym routine" might be in `wiki/health/`, tagged in a raw note, or mentioned on a project page.

## Step 2: Answer from vault content

Synthesize the answer from what you find. Be clear about:
- What you found and where it came from (cite the wiki page or raw file)
- What you didn't find (if the vault has no relevant content, say so — don't hallucinate from general knowledge)

If the vault has partial information and you supplement with general knowledge, make the distinction explicit: "Your vault says X. For context (not from your notes): Y."

## Step 2.5: Offer to also search the global vault

This runs ONLY when Step 0 reported `mode=ambiguous` (a local vault plus a *different* global vault). When `mode=single` — including when you are already inside the global vault — skip it: re-searching the same vault would duplicate and mislabel identical results.

Read the config flag `query_offer_global_after_local` from the same config file the resolver uses (`$OBSIDIAN_SB_CONFIG`, default `~/.claude/obsidian-second-brain-config.json`). Treat a missing key as `true` (default on). If it is `false`, skip this step.

If enabled, then — regardless of whether the local search found anything — offer to also search the global knowledge base (phrase the offer in the user's language), e.g.:

> "Also search your main knowledge base (global, at `<global_vault_path>`) for this?"

If the user accepts, read the global vault's `schema.md` first, then run the same Step 1 search strategies against the global vault root and fold the findings into the answer. Always label which vault each part came from — e.g. "From the local vault: …" and "From the global base: …" (in the user's language) — so the two sources are never conflated.

## Step 3: Offer to file the answer

If the query produced a useful answer that isn't already well-captured in a wiki page — especially if the user asked something they'll likely want to recall again — offer to file it:

> "Want me to save this to your vault? I could create/update `wiki/<category>/<page>`."

If yes, create or update the relevant wiki page and log it as:
```
- QUERY: "<question summary>" → filed to wiki/<page>
```

If the answer was already well-captured in an existing page, no need to offer — just cite the page.

## Step 4: Task-like questions and the log

Per `schema.md` Operations > Query: if the answer or the question itself is task-like (an obligation on the user's own future action; cues in `schema.md` Ingest), **propose** filing it into `tasks/` (format and duplicate rules in `conductor/task-storage-spec.md`). Never create or modify task files without the user's go-ahead; Query also never performs rollover. If approved, write the line, log a separate `TASK_ADD`, and check duplicates first. Only when `tasks/` exists.

Then append the `QUERY` line to `log.md` (schema step 4: append to `log.md` for every query; use the filed form above when something was filed, else `- QUERY: "<question summary>"`).

## What good looks like

- Answers draw clearly from vault content with citations
- The distinction between "from your notes" and "general knowledge" is always explicit
- If nothing relevant is found, the response is honest and suggests what to ingest to fill the gap
