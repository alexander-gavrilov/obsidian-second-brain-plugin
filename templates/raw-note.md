---
date: <% tp.date.now("YYYY-MM-DD", 0, tp.file.title, "YYYY-MM-DD") %>
source: personal
tags: []
---

## 📅 Agenda

<!--
Events come from the Obsidian "ics" community plugin (requires the "dataview"
plugin too). Configure your calendar feed in Obsidian: Settings → ICS → add a
calendar URL. Any iCal/.ics feed works — published calendar, Google
Calendar "Secret address in iCal format", Fastmail, etc. The source is an
Obsidian setting, not part of this template. With no ICS plugin installed this
block simply shows "ICS plugin not enabled."
-->

```dataviewjs
const ics = app.plugins.getPlugin("ics");
const date = dv.current().date?.toFormat("yyyy-MM-dd");
// Meeting-platform detection for the "online" badge — NOT work coupling; safe to keep in the neutral default.
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
