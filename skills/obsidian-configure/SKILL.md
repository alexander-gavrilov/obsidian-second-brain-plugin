---
name: obsidian-configure
description: Configure the global Obsidian vault path for the second-brain plugin. Use this skill when the user wants to set up or change their global vault, says "configure obsidian", "set my global vault", "change vault path", "set up obsidian", or when another obsidian skill reports that no global vault is configured and the user needs to fix it.
tools: Read, Write, Bash
---

# Obsidian Configure

Set the global vault path used by all obsidian-second-brain skills when no local vault is present in the current project.

Config is stored at `~/.claude/obsidian-second-brain-config.json`.

Config keys:
- `global_vault_path` — absolute path to the global vault used when no local vault is present.
- `query_offer_global_after_local` — controls whether `obsidian-query`, after answering from a local vault, offers to also search the global vault. Default `true`.

## Step 1: Check current config

```bash
cat ~/.claude/obsidian-second-brain-config.json 2>/dev/null || echo "not configured"
```

If already configured, show the current path and ask: *"Your global vault is currently at `<path>`. Change it?"* If they say no, confirm and stop.

## Step 2: Ask for the vault path

Ask:

> "What's the absolute path to your global Obsidian vault?"

## Step 3: Validate the path

Check that the directory exists and contains `schema.md`:

```bash
ls <path>/schema.md
```

- If the directory doesn't exist: "That path doesn't exist. Create a new vault there with `obsidian-init`, then run `obsidian-configure` again."
- If the directory exists but has no `schema.md`: "This directory doesn't look like an initialized vault (no `schema.md`). Run `obsidian-init` there first, or double-check the path."

## Step 4: Save the config

Write `~/.claude/obsidian-second-brain-config.json`:

```json
{
  "global_vault_path": "/absolute/path/to/vault",
  "query_offer_global_after_local": true
}
```

Use the exact absolute path the user provided (resolve `~` to the actual home directory).

Include `"query_offer_global_after_local": true` by default. The `true` shown in the block above is only the value for a **new** config — if the config already exists (e.g. a re-run that only changes the vault path), carry over the user's existing `query_offer_global_after_local` value instead of resetting it to `true`.

Confirm: *"Global vault set to `<path>`. All obsidian skills will default to this vault when no local vault is found in the current project."*

## Step 5: Toggle the cross-vault query offer

If the user asks to turn the cross-vault query offer on or off (e.g. "turn off cross-vault query offer", "always ask before searching global", "stop offering to search my global vault after local queries"), update only the `query_offer_global_after_local` flag:

- If no config file exists yet, there is nothing to toggle — route to Step 2 to set the vault first (the flag is written with its default there).
- Read the current config, preserving `global_vault_path`.
- Set `query_offer_global_after_local` to `true` (offer enabled) or `false` (offer disabled) per the request.
- Write the config back with both keys intact.

Confirm the new state, e.g. *"After answering from a local vault, obsidian-query will no longer offer to also search your global vault."*
