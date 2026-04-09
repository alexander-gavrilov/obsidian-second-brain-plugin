# Vault Raw Folder Restructure Summary

**Date:** 2026-04-09
**Vault:** /tmp/test-vault-restructure/

## Files Moved

| Old Path | New Path |
|---|---|
| raw/2024-01-15-machine-learning-basics.md | raw/2024-01-15/machine-learning-basics.md |
| raw/2024-01-15-python-tips.md | raw/2024-01-15/python-tips.md |
| raw/2024-03-20-coffee-shop-recommendations.md | raw/2024-03-20/coffee-shop-recommendations.md |

## Links Rewritten

| File | Old Link | New Link |
|---|---|---|
| wiki/learning/machine-learning.md | `[[raw/2024-01-15-machine-learning-basics]]` | `[[raw/2024-01-15/machine-learning-basics]]` |

## Final State of raw/ Directory

```
raw/
├── 2024-01-15/
│   ├── machine-learning-basics.md
│   └── python-tips.md
└── 2024-03-20/
    └── coffee-shop-recommendations.md
```

## Notes

- 3 files moved from flat naming (YYYY-MM-DD-title.md) to date-folder structure (YYYY-MM-DD/title.md)
- 1 Obsidian wikilink updated in wiki/learning/machine-learning.md
- Date-based subdirectories created: raw/2024-01-15/ and raw/2024-03-20/
- File contents were not modified, only moved
