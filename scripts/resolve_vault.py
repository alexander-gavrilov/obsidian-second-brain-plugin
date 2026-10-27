#!/usr/bin/env python3
"""Resolve which Obsidian vault the second-brain skills should operate on.

Local vault  = nearest ancestor of the current directory (or --cwd) that holds schema.md.
Global vault = `global_vault_path` in ~/.claude/obsidian-second-brain-config.json
               (override the config file with $OBSIDIAN_SB_CONFIG).

Local and global are compared by realpath: when they are the same directory they are ONE
vault and there is nothing to choose.

Output (stdout, key=value lines):
  root=<absolute path>       the vault to use (the local vault when both exist and differ)
  mode=<single|ambiguous>    "ambiguous" only when a local AND a different global vault exist
  local=<path or empty>
  global=<path or empty>

Exit codes: 0 resolved, 3 no vault found (message on stderr). (Python itself exits 2 when
the script file is missing, so 2 is never used for "no vault".)
With --root only the root path is printed.
"""
import argparse
import json
import os
import sys

DEFAULT_CONFIG = os.path.join("~", ".claude", "obsidian-second-brain-config.json")


def find_local(start):
    cur = os.path.realpath(start)
    while True:
        if os.path.isfile(os.path.join(cur, "schema.md")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return ""
        cur = parent


def read_global(config_path):
    try:
        with open(os.path.expanduser(config_path), encoding="utf-8") as f:
            value = json.load(f).get("global_vault_path") or ""
    except (OSError, ValueError, AttributeError):
        return ""
    if not isinstance(value, str):
        return ""
    value = os.path.realpath(os.path.expanduser(value)) if value else ""
    return value if value and os.path.isdir(value) else ""


def resolve(cwd, config_path):
    local = find_local(cwd)
    glob = read_global(config_path)
    if local and glob and local == glob:
        glob_effective = glob
        mode = "single"
    elif local and glob:
        glob_effective, mode = glob, "ambiguous"
    else:
        glob_effective, mode = glob, "single"
    root = local or glob
    return root, mode, local, glob_effective


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cwd", default=os.getcwd())
    ap.add_argument("--config", default=os.environ.get("OBSIDIAN_SB_CONFIG", DEFAULT_CONFIG))
    ap.add_argument("--root", action="store_true", help="print only the root path")
    a = ap.parse_args(argv)
    root, mode, local, glob = resolve(a.cwd, a.config)
    if not root:
        print("No vault found here and no global vault is configured. "
              "Run `obsidian-configure` to set one up, or `obsidian-init` to create one here.",
              file=sys.stderr)
        return 3
    if a.root:
        print(root)
    else:
        print(f"root={root}\nmode={mode}\nlocal={local}\nglobal={glob}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
