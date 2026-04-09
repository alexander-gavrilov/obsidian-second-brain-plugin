---
name: obsidian-query
description: Query an Obsidian knowledge vault to answer questions from stored knowledge. Use this skill when the user asks about something they might have saved, wants to recall information, or asks "what do I know about X", "find my notes on X", "do I have anything about X", "remind me about X", "what did I save about X". Also trigger when the user asks a question that seems like it could be answered from their notes rather than general knowledge.
tools: Read, Glob, Grep, Write, Edit
---

# Obsidian Query

Answer questions using the Obsidian vault rooted at the current working directory.

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
