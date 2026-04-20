---
name: obsidian-configure
description: Configure the global Obsidian vault path for the second-brain plugin. Use this skill when the user wants to set up or change their global vault, says "configure obsidian", "set my global vault", "change vault path", "set up obsidian", or when another obsidian skill reports that no global vault is configured and the user needs to fix it.
tools: Read, Write, Bash
---

# Obsidian Configure

Set the global vault path used by all obsidian-second-brain skills when no local vault is present in the current project.

Config is stored at `~/.claude/obsidian-second-brain-config.json`.

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
  "global_vault_path": "/absolute/path/to/vault"
}
```

Use the exact absolute path the user provided (resolve `~` to the actual home directory).

Confirm: *"Global vault set to `<path>`. All obsidian skills will default to this vault when no local vault is found in the current project."*
