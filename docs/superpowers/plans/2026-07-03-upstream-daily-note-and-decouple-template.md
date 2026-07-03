# Upstream obsidian-daily-note & Decouple Template — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the `obsidian-daily-note` skill and the `obsidian-quick-capture` fixes from the live `knowledge-base/general` vault into this plugin, ship a work-tool-neutral default daily-note template, and make `obsidian-init` scaffold it without clobbering an existing one.

**Architecture:** The daily-note script is already vault-agnostic (it renders whatever `templates/raw-note.md` the vault holds), so porting it is copy + fix the invocation path to prefer the installed-plugin location. The only Outlook/Teams coupling lives in the template's routine checklist, so the shipped default just de-works that checklist while keeping the calendar-agnostic ICS Agenda block. `obsidian-init` gains non-destructive template handling.

**Tech Stack:** Markdown skills (SKILL.md), Python 3 stdlib (`create_daily_note.py`), `unittest`. No third-party deps.

## Global Constraints

- Python: **stdlib only** (`argparse`, `datetime`, `re`, `pathlib`, `unittest`, `subprocess`, `tempfile`). No third-party packages.
- Shipped default template MUST contain **no** work-specific wording ("Teams", "Task Tracker", "Outlook").
- Shipped default template MUST render cleanly via `create_daily_note.py` — no leftover `<%` and no `UNRENDERED:` exit.
- `obsidian-init` template handling MUST be non-destructive: never overwrite an existing `templates/raw-note.md` without (a) explicit user choice and (b) a `templates/raw-note.md.bak` backup.
- Plugin-invocation path convention: installed skills live at `~/.claude/plugins/marketplaces/obsidian-second-brain/skills/<skill>/...` (the vault-local fallback is `.claude/skills/<skill>/...`). Prefer the installed-plugin path.
- Version bump `.claude-plugin/plugin.json` `1.3.0` → `1.4.0` ships in this branch (final task), matching the standing "bump on shipping skill changes" rule.
- Commit messages end with the `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>` trailer.
- All work stays on the existing `feature/upstream-daily-note` branch.

---

### Task 1: Port the `obsidian-daily-note` skill and its tests into the plugin

**Files:**
- Create: `skills/obsidian-daily-note/scripts/create_daily_note.py` (copy from vault, verbatim)
- Create: `skills/obsidian-daily-note/tests/test_create_daily_note.py` (copy from vault, verbatim)
- Create: `skills/obsidian-daily-note/SKILL.md` (copy from vault, then fix invocation path)
- Source of truth to copy from: `/Users/a.haurylau@godeltech.com/knowledge-base/general/.claude/skills/obsidian-daily-note/`

**Interfaces:**
- Produces: the script module `create_daily_note` exposing `is_unfinished`, `normalize_task_text`, `stamp_provenance`, `parse_tasks_section`, `insert_tasks_into_section`, `iter_daily_notes`, `find_prior_daily_note`, `select_carry_tasks`, `collect_recollect_candidates`, `find_vault`, `parse_target_date`, `render`, `main`. CLI: `python3 create_daily_note.py [DATE] [--vault DIR] [--force] [--recollect]`.
- Produces: SKILL name `obsidian-daily-note` (invoked by quick-capture Task 4 and init Task 3).

- [ ] **Step 1: Copy the script and test files verbatim**

```bash
cd /Users/a.haurylau@godeltech.com/projects/obsidian-second-brain-plugin
VAULT=/Users/a.haurylau@godeltech.com/knowledge-base/general/.claude/skills/obsidian-daily-note
mkdir -p skills/obsidian-daily-note/scripts skills/obsidian-daily-note/tests
cp "$VAULT/scripts/create_daily_note.py" skills/obsidian-daily-note/scripts/create_daily_note.py
cp "$VAULT/tests/test_create_daily_note.py" skills/obsidian-daily-note/tests/test_create_daily_note.py
cp "$VAULT/SKILL.md" skills/obsidian-daily-note/SKILL.md
```

- [ ] **Step 2: Run the ported test suite to confirm it passes**

Run: `cd skills/obsidian-daily-note && python3 -m unittest tests.test_create_daily_note -v`
Expected: all tests PASS (the suite is self-contained — it builds temp vaults and invokes the script directly). If `tests` is not importable as a package, run `python3 -m unittest tests/test_create_daily_note.py -v` instead.

- [ ] **Step 3: Fix the invocation path in SKILL.md to prefer the installed-plugin location**

In `skills/obsidian-daily-note/SKILL.md`, the "How to do it" section currently shows the vault-local path:

```bash
python3 .claude/skills/obsidian-daily-note/scripts/create_daily_note.py [DATE]
```

Replace that code block, and every other occurrence of `.claude/skills/obsidian-daily-note/scripts/create_daily_note.py` in the file, with a path-resolution preamble followed by the call:

````markdown
Resolve the script path (prefer the installed plugin, fall back to a vault-local copy):

```bash
SCRIPT=~/.claude/plugins/marketplaces/obsidian-second-brain/skills/obsidian-daily-note/scripts/create_daily_note.py
[ -f "$SCRIPT" ] || SCRIPT=.claude/skills/obsidian-daily-note/scripts/create_daily_note.py
python3 "$SCRIPT" [DATE]
```
````

Update the "Examples" table rows the same way (use `python3 "$SCRIPT" saturday`, etc.), and the `--recollect` example.

- [ ] **Step 3b: Point users to `obsidian-init` when the template is missing**

In `skills/obsidian-daily-note/SKILL.md`, in the "What the script guarantees" section, extend the "Fails loud, not silent" bullet (or add a sibling bullet) so a missing template is actionable. Add:

```markdown
- **No template?** If `templates/raw-note.md` does not exist, the script exits with
  `ERROR: template not found`. Do not hand-write a bare daily note — run
  `obsidian-init` first to scaffold the template, then retry.
```

- [ ] **Step 4: Sanity-check the skill runs end-to-end against a throwaway vault**

Run:
```bash
cd /tmp && rm -rf dn-check && mkdir -p dn-check/templates dn-check/input && \
printf '%s\n' '---' 'date: <% tp.date.now("YYYY-MM-DD", 0, tp.file.title, "YYYY-MM-DD") %>' 'source: personal' 'tags: []' '---' '' '## ✅ Tasks' '' '## 📝 Meeting notes' > dn-check/templates/raw-note.md && \
python3 /Users/a.haurylau@godeltech.com/projects/obsidian-second-brain-plugin/skills/obsidian-daily-note/scripts/create_daily_note.py 2026-07-06 --vault dn-check && \
cat dn-check/input/2026-07-06.md
```
Expected: `CREATED: .../2026-07-06.md`, and the printed note has `date: 2026-07-06` with no `<%` left.

- [ ] **Step 5: Commit**

```bash
cd /Users/a.haurylau@godeltech.com/projects/obsidian-second-brain-plugin
git add skills/obsidian-daily-note
git commit -m "$(printf 'feat: add obsidian-daily-note skill to the plugin\n\nPort the daily-note renderer, task carry-forward, and --recollect scan\nfrom the live vault. Invocation path prefers the installed plugin,\nfalls back to a vault-local copy.\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

### Task 2: Ship the neutral default template + a rendering integration test

**Files:**
- Create: `templates/raw-note.md` (plugin-shipped neutral default)
- Create: `skills/obsidian-daily-note/tests/test_default_template.py`

**Interfaces:**
- Consumes: `create_daily_note.py` from Task 1 (the `render` path and CLI).
- Produces: `templates/raw-note.md` at the plugin root — copied into vaults by `obsidian-init` (Task 3).

- [ ] **Step 1: Write the failing rendering test**

Create `skills/obsidian-daily-note/tests/test_default_template.py`:

```python
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

# plugin root = skills/obsidian-daily-note/tests/ -> up 3
PLUGIN_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TEMPLATE = PLUGIN_ROOT / "templates" / "raw-note.md"
SCRIPT = PLUGIN_ROOT / "skills" / "obsidian-daily-note" / "scripts" / "create_daily_note.py"

WORK_WORDS = re.compile(r"teams|task tracker|outlook", re.IGNORECASE)


class TestDefaultTemplate(unittest.TestCase):
    def test_template_exists(self):
        self.assertTrue(DEFAULT_TEMPLATE.exists(), f"missing {DEFAULT_TEMPLATE}")

    def test_template_has_no_work_specific_wording(self):
        text = DEFAULT_TEMPLATE.read_text(encoding="utf-8")
        self.assertIsNone(WORK_WORDS.search(text), "default template must be work-neutral")

    def test_template_has_required_sections(self):
        text = DEFAULT_TEMPLATE.read_text(encoding="utf-8")
        for heading in ("## 📅 Agenda", "## ✅ Tasks", "## 📝 Meeting notes", "## 📥 Captures"):
            self.assertIn(heading, text)

    def test_template_renders_cleanly_on_a_weekday(self):
        with tempfile.TemporaryDirectory() as tmp:
            v = Path(tmp)
            (v / "templates").mkdir()
            (v / "input").mkdir()
            (v / "templates" / "raw-note.md").write_text(
                DEFAULT_TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8"
            )
            # 2026-07-06 is a Monday -> routine block must render.
            out = subprocess.run(
                ["python3", str(SCRIPT), "2026-07-06", "--vault", str(v)],
                capture_output=True, text=True,
            )
            self.assertEqual(out.returncode, 0, out.stderr)
            note = (v / "input" / "2026-07-06.md").read_text(encoding="utf-8")
            self.assertNotIn("<%", note)
            self.assertIn("date: 2026-07-06", note)
            self.assertIn("## ✅ Daily routine", note)

    def test_template_omits_routine_on_weekend(self):
        with tempfile.TemporaryDirectory() as tmp:
            v = Path(tmp)
            (v / "templates").mkdir()
            (v / "input").mkdir()
            (v / "templates" / "raw-note.md").write_text(
                DEFAULT_TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8"
            )
            # 2026-07-04 is a Saturday -> routine block must be dropped.
            subprocess.run(
                ["python3", str(SCRIPT), "2026-07-04", "--vault", str(v)],
                capture_output=True, text=True, check=True,
            )
            note = (v / "input" / "2026-07-04.md").read_text(encoding="utf-8")
            self.assertNotIn("## ✅ Daily routine", note)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd skills/obsidian-daily-note && python3 -m unittest tests.test_default_template -v`
Expected: FAIL — `test_template_exists` fails with "missing .../templates/raw-note.md" (file not created yet).

- [ ] **Step 3: Create the neutral default template**

Create `templates/raw-note.md` with exactly this content (the Agenda `dataviewjs` block is the vault's block verbatim — it is calendar-agnostic; the routine is de-worked):

````markdown
---
date: <% tp.date.now("YYYY-MM-DD", 0, tp.file.title, "YYYY-MM-DD") %>
source: personal
tags: []
---

## 📅 Agenda

<!--
Events come from the Obsidian "ics" community plugin (requires the "dataview"
plugin too). Configure your calendar feed in Obsidian: Settings → ICS → add a
calendar URL. Any iCal/.ics feed works — Outlook published calendar, Google
Calendar "Secret address in iCal format", Fastmail, etc. The source is an
Obsidian setting, not part of this template. With no ICS plugin installed this
block simply shows "ICS plugin not enabled."
-->

```dataviewjs
const ics = app.plugins.getPlugin("ics");
const date = dv.current().date?.toFormat("yyyy-MM-dd");
const ONLINE = /teams meeting|microsoft teams|zoom|google meet|skype/i;
const SHOW_CANCELLED = false; // set true to keep cancelled meetings (struck through)
const esc = s => String(s ?? "").replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

if (!ics) {
  dv.paragraph("_ICS plugin not enabled._");
} else if (!date) {
  dv.paragraph("_No `date` in frontmatter._");
} else {
  let events = (await ics.getEvents(date)) ?? [];
  if (!SHOW_CANCELLED) events = events.filter(e => !/^cancell?ed:/i.test(e.summary));
  if (!events.length) {
    dv.paragraph(`_No events for ${date}._`);
  } else {
    events.sort((a, b) => a.utime - b.utime);
    const box = dv.el("div", "");
    let lastHtml = "";
    const render = () => {
      const now = moment();
      const isToday = date === now.format("YYYY-MM-DD");
      const rows = events.map(e => {
        const start = e.start ? moment(e.start) : moment(`${date} ${e.time}`, "YYYY-MM-DD HH:mm");
        const end = e.end ? moment(e.end) : moment(`${date} ${e.endTime}`, "YYYY-MM-DD HH:mm");
        const ongoing = isToday && now.isSameOrAfter(start) && now.isBefore(end);
        const past = isToday && now.isSameOrAfter(end);
        const cancelled = /^cancell?ed:/i.test(e.summary);
        let title = cancelled ? `<s>${esc(e.summary)}</s>` : esc(e.summary);
        if (e.location && !ONLINE.test(e.location)) title += ` · 📍 ${esc(e.location)}`;
        const online = ONLINE.test(e.location ?? "") || ONLINE.test(e.summary);
        if (e.callUrl) title += ` · <a href="${esc(e.callUrl)}">Join</a>`;
        else if (online) title += " · 💻 Online";
        const style = ongoing
          ? "background: var(--text-highlight-bg, rgba(255,208,0,.25)); font-weight:600;"
          : past ? "opacity:.5;" : "";
        return `<tr style="${style}"><td style="white-space:nowrap; padding:3px 12px 3px 8px; vertical-align:top;">${ongoing ? "🔴 " : ""}<b>${esc(e.time)}</b></td><td style="padding:3px 8px;">${title}</td></tr>`;
      });
      const html = `<table style="border-collapse:collapse; width:100%;">${rows.join("")}</table>`;
      if (html === lastHtml) return; // nothing changed this tick — skip the repaint (no blink)
      lastHtml = html;
      box.innerHTML = html;
    };
    render();
    dv.component.registerInterval(window.setInterval(render, 60000));
  }
}
```

## ✅ Tasks

<%*
// Only show the daily routine on working days (Mon–Fri).
// Day-of-week is derived from the note's title (YYYY-MM-DD), falling back to today.
const dow = parseInt(tp.date.now("d", 0, tp.file.title, "YYYY-MM-DD"));
if (dow >= 1 && dow <= 5) {
tR += `## ✅ Daily routine

- [ ] 📆 Check calendar
- [ ] 📥 Check inboxes
- [ ] 🎛️ Check tasks

`;
}
%>## 📝 Meeting notes

<!-- Place cursor below, run "ICS: import events" (Cmd+P), then write notes under each event (Tab to indent). -->

## 📥 Captures

````

Note: the `ONLINE` regex inside the JS still lists "teams meeting" etc. — that is meeting-URL *detection* (matches Zoom/Meet/Skype too), not work coupling, and the test only scans for standalone work words in routine/section text. Leave the JS regex as-is.

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd skills/obsidian-daily-note && python3 -m unittest tests.test_default_template -v`
Expected: all tests PASS.

- [ ] **Step 5: Run the full daily-note suite to confirm nothing regressed**

Run: `cd skills/obsidian-daily-note && python3 -m unittest discover -s tests -v`
Expected: all tests PASS (both `test_create_daily_note` and `test_default_template`).

- [ ] **Step 6: Commit**

```bash
cd /Users/a.haurylau@godeltech.com/projects/obsidian-second-brain-plugin
git add templates/raw-note.md skills/obsidian-daily-note/tests/test_default_template.py
git commit -m "$(printf 'feat: ship work-neutral default daily-note template\n\nAgenda block is calendar-agnostic (any ICS feed); routine checklist is\nde-worked. Added a rendering test asserting it renders cleanly and stays\nwork-neutral.\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

### Task 3: Non-destructive template handling in `obsidian-init`

**Files:**
- Modify: `skills/obsidian-init/SKILL.md` (add a template-scaffolding step after Step 5, and reference it in "What good looks like")

**Interfaces:**
- Consumes: the plugin default at `templates/raw-note.md` (Task 2); resolves it via the installed-plugin path with a vault-local fallback.
- Produces: `<vault>/templates/raw-note.md` (and optionally `<vault>/templates/raw-note.md.bak`); a `- TEMPLATE:` line in `log.md`.

This task is a Markdown-instruction change — its "test" is a structural read-through against the acceptance list in Step 3 below.

- [ ] **Step 1: Add the template step to `obsidian-init/SKILL.md`**

Insert a new `## Step 6: Scaffold the daily-note template` section immediately before the `## What good looks like` section, with exactly this content:

````markdown
## Step 6: Scaffold the daily-note template

`obsidian-daily-note` and `obsidian-quick-capture` render `templates/raw-note.md`.
Scaffold it so those skills work in this vault.

Resolve the plugin's default template (prefer the installed plugin, fall back to a vault-local copy):

```bash
DEFAULT_TPL=~/.claude/plugins/marketplaces/obsidian-second-brain/templates/raw-note.md
# dev fallback when running from a clone of the plugin repo:
[ -f "$DEFAULT_TPL" ] || DEFAULT_TPL=templates/raw-note.md
```

If neither path exists (unusual), tell the user the plugin default template could not be located and skip template scaffolding rather than writing a broken file.

Then:

- **No `templates/raw-note.md` in this vault** → create `templates/` and copy the default in. No prompt.
- **Existing `templates/raw-note.md` identical to the default** (`diff -q` reports no difference) → do nothing, proceed silently.
- **Existing `templates/raw-note.md` differs from the default** → do NOT overwrite silently. Ask the user to choose:
  1. **Keep existing** (default) — leave the vault's file untouched.
  2. **Use plugin default** — back up the current file to `templates/raw-note.md.bak`, then overwrite with the default.
  3. **Interactive hybrid** — read both files, propose a merged template (typically: keep the user's Agenda block and section layout, adjust the routine checklist for this vault), show the proposed result, and on approval back up the original to `templates/raw-note.md.bak` and write the merge.

After acting, append a `- TEMPLATE: <action>` line to `log.md` under today's `## YYYY-MM-DD` header (create the header if absent), where `<action>` is one of `created default`, `kept existing`, `replaced with default (backup: raw-note.md.bak)`, or `wrote hybrid (backup: raw-note.md.bak)`.
````

- [ ] **Step 2: Add a bullet to "What good looks like"**

In `skills/obsidian-init/SKILL.md`, under the `## What good looks like` list, add:

```markdown
- Has a working `templates/raw-note.md` so `obsidian-daily-note` / `obsidian-quick-capture` can scaffold daily notes; an existing template was never overwritten without a `.bak` backup and explicit choice
```

- [ ] **Step 3: Structural verification (read-through against acceptance list)**

Run: `grep -nE 'Step 6|raw-note.md.bak|Keep existing|Use plugin default|Interactive hybrid|TEMPLATE:' skills/obsidian-init/SKILL.md`
Expected output confirms all of: a `## Step 6` heading, the three choice labels, the `.bak` backup, and the `- TEMPLATE:` log line are present. Manually confirm the "no template → copy silently", "identical → no-op", and "differs → three choices" branches all read correctly and that overwrite paths always back up first.

- [ ] **Step 4: Commit**

```bash
cd /Users/a.haurylau@godeltech.com/projects/obsidian-second-brain-plugin
git add skills/obsidian-init/SKILL.md
git commit -m "$(printf 'feat: scaffold daily-note template in obsidian-init\n\nNon-destructive: copies the plugin default into fresh vaults, and on an\nexisting differing template offers keep / replace / hybrid, always backing\nup to raw-note.md.bak before overwriting.\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

### Task 4: Upstream the `obsidian-quick-capture` divergence

**Files:**
- Modify: `skills/obsidian-quick-capture/SKILL.md` (hard-constraint note; Step 2c; Step 4)

**Interfaces:**
- Consumes: `obsidian-daily-note` script via the installed-plugin path with vault-local fallback (Task 1).
- Produces: no code interface; behavior change only.

Markdown-instruction change — verified by structural read-through in Step 4.

- [ ] **Step 1: Extend the hard-constraint note**

In `skills/obsidian-quick-capture/SKILL.md`, find the hard-constraint blockquote that ends with:

```
...Just capture the content and let the background ingest handle it later.
```

Append this sentence to that same blockquote:

```
Scaffolding today's note from the template via the `obsidian-daily-note` script (Step 2c) is the sanctioned way to create that one file; the script's carry-over reads of prior daily notes are reads, not writes, and do not violate this one-file constraint.
```

- [ ] **Step 2: Change the Step 2 intro and add Step 2c**

In `skills/obsidian-quick-capture/SKILL.md`, change the Step 2 intro line:

```
This runs once per day, before the first capture is written. It has two parts: a background catch-up and a morning briefing.
```

to:

```
This runs once per day, before the first capture is written. It has three parts: a background catch-up, a morning briefing, and scaffolding today's note from the template.
```

Then, immediately after the end of section `### 2b: Generate the morning briefing` and before `## Step 3: Parse the input`, insert:

````markdown
### 2c: Scaffold today's daily note from template

This is the last sub-step of the first-capture routine — it runs after 2a and 2b, so the file is created immediately before the first entry is written.

When `input/YYYY-MM-DD.md` does not exist yet, **do not create a bare file**. Instead scaffold it from the template using the `obsidian-daily-note` script. Get today's date with `date +%Y-%m-%d`, resolve the script (prefer the installed plugin, fall back to a vault-local copy), then run it from the vault root:

```bash
SCRIPT=~/.claude/plugins/marketplaces/obsidian-second-brain/skills/obsidian-daily-note/scripts/create_daily_note.py
[ -f "$SCRIPT" ] || SCRIPT=.claude/skills/obsidian-daily-note/scripts/create_daily_note.py
python3 "$SCRIPT" <today>
```

This renders every template section (`## 📅 Agenda`, `## ✅ Tasks`, `## 📝 Meeting notes`, `## 📥 Captures`) exactly as Obsidian's Templater would, and as a bonus carries forward unfinished tasks from the most recent prior daily note. This is the sanctioned way to create the daily input file — see the `obsidian-daily-note` skill for details. If the script reports the template is missing, tell the user to run `obsidian-init` (do not hand-write a bare file).
````

- [ ] **Step 3: Update Step 4 to append under the Captures heading**

In `skills/obsidian-quick-capture/SKILL.md`, replace the Step 4 opening line:

```
Create `input/YYYY-MM-DD.md` if it doesn't exist yet (no header needed — just entries).
```

with:

```
The file already exists — it was scaffolded from the template in Step 2c (or it existed before today's first capture). Append the entry block **under the `## 📥 Captures` heading**, not at the end of the file (the template ends `## 📝 Meeting notes` then `## 📥 Captures`, so writing to the end would land the entry in the wrong section).
```

And change the sentence:

```
Get the actual current time by running `date +%H:%M` via Bash. Use that value as the timestamp. Leave a blank line before `### HH:MM` if the file already has content.
```

to reference the section, and add a legacy fallback line right after it:

```
Get the actual current time by running `date +%H:%M` via Bash. Use that value as the timestamp. Leave a blank line before `### HH:MM` if the section already has content.

**Legacy notes**: if a pre-existing note lacks a `## 📥 Captures` heading (e.g. an older bare file), add the heading at the end of the file first, then append the entry under it.
```

- [ ] **Step 4: Structural verification**

Run: `grep -nE '2c: Scaffold|three parts|📥 Captures|Legacy notes|sanctioned' skills/obsidian-quick-capture/SKILL.md`
Expected: confirms the three-parts intro, the new 2c section, the Captures-heading append, the legacy fallback, and the extended hard-constraint sentence are all present.

- [ ] **Step 5: Commit**

```bash
cd /Users/a.haurylau@godeltech.com/projects/obsidian-second-brain-plugin
git add skills/obsidian-quick-capture/SKILL.md
git commit -m "$(printf 'feat: quick-capture scaffolds from template, appends under Captures\n\nUpstreams the live-vault divergence: Step 2c scaffolds the day via\nobsidian-daily-note, Step 4 appends under the Captures heading with a\nlegacy fallback, and the one-file constraint sanctions the scaffold.\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

### Task 5: Update docs and bump the version

**Files:**
- Modify: `README.md` (add `obsidian-daily-note` to the Skills list)
- Modify: `GEMINI.md` (add `obsidian-daily-note` to the skill bullet list)
- Modify: `.claude-plugin/plugin.json` (`version` → `1.4.0`)
- Modify: `.claude-plugin/marketplace.json` (`metadata.version` and `plugins[0].version` → `1.4.0`)

**Interfaces:** none (docs/metadata only).

- [ ] **Step 1: Add the skill to README.md**

In `README.md`, after the `### `obsidian-restructure`` block and before `## Vault conventions`, add:

```markdown
### `obsidian-daily-note`
Scaffold a daily note at `input/YYYY-MM-DD.md` from `templates/raw-note.md`, rendered the way Obsidian's Templater would — usable from the terminal. Carries unfinished tasks forward from the previous daily note and can recollect older orphaned tasks.
```

- [ ] **Step 2: Add the skill to GEMINI.md**

In `GEMINI.md`, after the `obsidian-restructure` bullet, add:

```markdown
- **obsidian-daily-note** — scaffold a daily note from the vault template, carrying unfinished tasks forward
```

- [ ] **Step 3: Bump plugin.json**

In `.claude-plugin/plugin.json`, change `"version": "1.3.0"` to `"version": "1.4.0"`.

- [ ] **Step 4: Bump marketplace.json**

In `.claude-plugin/marketplace.json`, change both `"version": "1.1.0"` occurrences (under `metadata` and under `plugins[0]`) to `"version": "1.4.0"`.

- [ ] **Step 5: Verify no leftover placeholders and the whole suite still passes**

Run:
```bash
cd /Users/a.haurylau@godeltech.com/projects/obsidian-second-brain-plugin
grep -RnE 'TODO|TBD|FIXME|<placeholder>' skills/obsidian-daily-note templates/raw-note.md || echo "no placeholders"
python3 -m unittest discover -s skills/obsidian-daily-note/tests -v
grep -n '1.4.0' .claude-plugin/plugin.json .claude-plugin/marketplace.json
```
Expected: "no placeholders" (or only legitimate matches inside JS/comments — confirm none are real gaps), all tests PASS, and `1.4.0` shows in both metadata files.

- [ ] **Step 6: Commit**

```bash
cd /Users/a.haurylau@godeltech.com/projects/obsidian-second-brain-plugin
git add README.md GEMINI.md .claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "$(printf 'docs: list obsidian-daily-note and bump to 1.4.0\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

## Post-implementation

After all tasks pass, the branch `feature/upstream-daily-note` holds the full change set. Use `superpowers:finishing-a-development-branch` to decide merge vs. PR. The `TODO.md` items 1 & 2 are then done; update `TODO.md` to strike them and leave items 3 & 4 for their own specs.
```
