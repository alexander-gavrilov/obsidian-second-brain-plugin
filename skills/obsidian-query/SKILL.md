---
name: obsidian-query
description: Query an Obsidian knowledge vault to answer questions from stored knowledge. Use this skill when the user asks about something they might have saved, wants to recall information, or asks "what do I know about X", "find my notes on X", "do I have anything about X", "remind me about X", "what did I save about X". Also trigger when the user asks a question that seems like it could be answered from their notes rather than general knowledge.
tools: Read, Glob, Grep, Write, Edit
---

# Obsidian Query

## Step 0: Resolve vault

1. Check if a local vault exists: does `schema.md` exist in the current working directory?
2. Read `~/.claude/obsidian-second-brain-config.json` (if it exists) to get `global_vault_path`.

**Decision:**
- Local present + global configured → use the **local** vault to answer, then after answering offer to also search the global vault (see Step 2.5). Do not ask up front.
- Local present + no global configured → use local, no prompt
- No local + global configured → use global path silently
- No local + no global → stop: *"No vault found here and no global vault is configured. Run `obsidian-configure` to set one up."*

All file operations below use the resolved vault root.
Remember whether the resolved vault was the **local** one (a local `schema.md` was present) — Step 2.5 depends on it.

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

This runs ONLY when Step 0 resolved the **local** vault (a local schema.md was present) and a `global_vault_path` is configured. It does NOT run when the query already used the global vault directly.

Read the config flag `query_offer_global_after_local` from `~/.claude/obsidian-second-brain-config.json`. Treat a missing key as `true` (default on). If it is `false`, skip this step.

If enabled, then — regardless of whether the local search found anything — offer:

> "Поискать это же в основной базе знаний (global, at `<global_vault_path>`)?"

If the user accepts, run the same Step 1 search strategies against the global vault root and fold the findings into the answer. Always label which vault each part came from — e.g. "Из локального vault: …" and "Из основной базы (global): …" — so the two sources are never conflated.

## Step 3: Offer to file the answer

If the query produced a useful answer that isn't already well-captured in a wiki page — especially if the user asked something they'll likely want to recall again — offer to file it:

> "Want me to save this to your vault? I could create/update `wiki/<category>/<page>`."

If yes, create or update the relevant wiki page and append to `log.md`:
```
- QUERY: "<question summary>" → filed to wiki/<page>
```

If the answer was already well-captured in an existing page, no need to offer — just cite the page.

## What good looks like

- Answers draw clearly from vault content with citations
- The distinction between "from your notes" and "general knowledge" is always explicit
- If nothing relevant is found, the response is honest and suggests what to ingest to fill the gap
