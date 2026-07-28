"""Render markdown brief + self-contained HTML Work Wrapped page."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from .stats import WrappedStats, _fmt_hours


def render_markdown(stats: WrappedStats) -> str:
    lines: list[str] = []
    lines.append(f"⏳ timeglass-last30days v{stats.version} · {stats.window_start} → {stats.window_end}")
    lines.append("")
    who = stats.user or "you"
    ws = f" · {stats.workspace}" if stats.workspace else ""
    lines.append(f"# Work Wrapped — {who}{ws}")
    lines.append("")
    lines.append(f"**{stats.headline}**")
    lines.append("")
    lines.append(stats.one_liner)
    lines.append("")
    lines.append(f"_Source: `{stats.source}` · tz {stats.timezone}_")
    if stats.warnings:
        lines.append("")
        lines.append("### Notes")
        for w in stats.warnings:
            lines.append(f"- {w}")
    lines.append("")
    lines.append("## Your month in numbers")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Total time | **{stats.total_hours}h** ({stats.total_minutes}m) |")
    lines.append(f"| Active days | **{stats.active_days}** |")
    lines.append(f"| Avg / active day | **{stats.avg_hours_active_day}h** |")
    lines.append(f"| Billable mix | **{stats.billable_pct}%** ({_fmt_hours(stats.billable_minutes)}) |")
    lines.append(f"| Meetings | **{stats.meeting_pct}%** ({_fmt_hours(stats.meeting_minutes)} · {stats.meeting_count} meetings) |")
    lines.append(f"| Deep work (non-meeting) | **{_fmt_hours(stats.deep_work_minutes)}** |")
    lines.append("")

    if stats.identity_cards:
        lines.append("## Identity cards")
        lines.append("")
        for card in stats.identity_cards:
            lines.append(f"- **{card['title']}** — {card['blurb']}")
        lines.append("")

    if stats.top_projects:
        lines.append("## Top projects")
        lines.append("")
        lines.append("| Project | Hours | Share | Budget |")
        lines.append("|---|---:|---:|---:|")
        for p in stats.top_projects:
            budget = "—"
            if p.get("budget_used_pct") is not None:
                budget = f"{p['budget_used_pct']}%"
            lines.append(
                f"| {p['name']} | {p['hours']}h | {p['share_pct']}% | {budget} |"
            )
        lines.append("")

    if stats.top_clients:
        lines.append("## Top clients")
        lines.append("")
        for c in stats.top_clients[:5]:
            lines.append(f"- **{c['name']}** — {c['hours']}h ({c['share_pct']}%)")
        lines.append("")

    if stats.top_activities:
        lines.append("## Top activities")
        lines.append("")
        for a in stats.top_activities[:8]:
            proj = f" · {a['project']}" if a.get("project") else ""
            lines.append(f"- **{a['title']}** — {_fmt_hours(a['minutes'])}{proj}")
        lines.append("")

    if stats.top_apps:
        lines.append("## App mix")
        lines.append("")
        for a in stats.top_apps[:6]:
            lines.append(f"- {a['name']} — {_fmt_hours(a['minutes'])}")
        lines.append("")

    if stats.weekday_mix:
        lines.append("## Weekday rhythm")
        lines.append("")
        lines.append("| Day | Hours |")
        lines.append("|---|---:|")
        for w in stats.weekday_mix:
            if w["minutes"] or w["weekday"] not in ("Saturday", "Sunday"):
                lines.append(f"| {w['weekday']} | {w['hours']}h |")
        lines.append("")

    if stats.busiest_day or stats.shoutouts:
        lines.append("## Shoutouts")
        lines.append("")
        for s in stats.shoutouts:
            lines.append(f"- {s}")
        lines.append("")

    if stats.budget_alerts:
        lines.append("## Budget watch")
        lines.append("")
        for b in stats.budget_alerts:
            flag = "OVER" if b["level"] == "over" else "NEAR"
            lines.append(
                f"- **[{flag}] {b['name']}** — {b['budget_used_pct']}% of {b.get('budget_hours')}h budget ({b['hours']}h logged)"
            )
        lines.append("")

    if stats.meetings:
        lines.append("## Meetings (sample)")
        lines.append("")
        for m in stats.meetings[:12]:
            client = f" · {m['client']}" if m.get("client") else ""
            lines.append(f"- {m['date']} — **{m['title']}** ({m['minutes']}m){client}")
        lines.append("")

    lines.append("## What to do with this")
    lines.append("")
    lines.append("1. **Protect the pattern that worked** — repeat the weekday rhythm that carried deep work.")
    lines.append("2. **Name the drag** — if one client ate the month, decide if that was strategy or drift.")
    lines.append("3. **Budget honesty** — anything NEAR/OVER needs a scope or staffing conversation this week.")
    lines.append("4. **Carry 3 commitments** into next week (write them down; don't trust memory).")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("Built with [Timeglass](https://timeglass.ai) MCP · no scraping · your work record only.")
    lines.append("")
    return "\n".join(lines)


def _bar(pct: float, width: int = 24) -> str:
    filled = int(round(max(0.0, min(100.0, pct)) / 100.0 * width))
    return "█" * filled + "░" * (width - filled)


def render_compact(stats: WrappedStats) -> str:
    """Terminal-friendly compact brief for agent pass-through."""
    lines = [
        f"⏳ timeglass-last30days v{stats.version} · {stats.window_start} → {stats.window_end}",
        "",
        stats.one_liner,
        "",
        f"Total  {_fmt_hours(stats.total_minutes):>6}   active days {stats.active_days}",
        f"Billable {stats.billable_pct:>5.1f}%   meetings {stats.meeting_pct:.1f}%   deep {_fmt_hours(stats.deep_work_minutes)}",
        "",
        "Top projects:",
    ]
    for p in stats.top_projects[:5]:
        lines.append(f"  {_bar(p['share_pct'])}  {p['share_pct']:5.1f}%  {p['hours']:5.1f}h  {p['name']}")
    if stats.identity_cards:
        lines.append("")
        lines.append("Identity:")
        for c in stats.identity_cards:
            lines.append(f"  • {c['title']} — {c['blurb']}")
    if stats.budget_alerts:
        lines.append("")
        lines.append("Budget watch:")
        for b in stats.budget_alerts:
            lines.append(f"  ! {b['level'].upper():4} {b['budget_used_pct']}%  {b['name']}")
    lines.append("")
    lines.append(f"source={stats.source}")
    return "\n".join(lines)


def render_html(stats: WrappedStats, template_path: Path | None = None) -> str:
    if template_path and template_path.is_file():
        tpl = template_path.read_text(encoding="utf-8")
    else:
        tpl = DEFAULT_HTML_TEMPLATE

    payload = json.dumps(stats.to_dict(), ensure_ascii=False)
    # Prevent </script> breakouts
    payload = payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    title = html.escape(f"Work Wrapped — {stats.user or 'Last 30 Days'}")
    return (
        tpl.replace("{{TITLE}}", title)
        .replace("{{WINDOW}}", html.escape(f"{stats.window_start} → {stats.window_end}"))
        .replace("{{STATS_JSON}}", payload)
    )


DEFAULT_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{{TITLE}}</title>
<meta name="description" content="Timeglass Work Wrapped — your last 30 days of real work, from MCP." />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet" />
<style>
  :root {
    --bg: #07080c;
    --bg2: #0e1018;
    --card: #141826;
    --card2: #1a1f30;
    --text: #f4f1ea;
    --muted: #9aa3b5;
    --line: rgba(255,255,255,0.08);
    --accent: #7c5cff;
    --accent2: #3de0c5;
    --warn: #ffb020;
    --danger: #ff5d6c;
    --good: #3dd68c;
    --shadow: 0 20px 60px rgba(0,0,0,.45);
    --radius: 22px;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; background: var(--bg); color: var(--text);
    font-family: "DM Sans", ui-sans-serif, system-ui, sans-serif; }
  body {
    min-height: 100vh;
    background:
      radial-gradient(1200px 600px at 10% -10%, rgba(124,92,255,.28), transparent 55%),
      radial-gradient(900px 500px at 90% 0%, rgba(61,224,197,.18), transparent 50%),
      radial-gradient(700px 400px at 50% 100%, rgba(255,93,108,.10), transparent 55%),
      var(--bg);
  }
  .wrap { max-width: 980px; margin: 0 auto; padding: 32px 20px 80px; }
  .top {
    display: flex; justify-content: space-between; align-items: flex-start; gap: 16px;
    margin-bottom: 28px; flex-wrap: wrap;
  }
  .brand { display: flex; gap: 12px; align-items: center; }
  .logo {
    width: 42px; height: 42px; border-radius: 14px;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    display: grid; place-items: center; font-weight: 700; letter-spacing: -0.04em;
    box-shadow: 0 8px 24px rgba(124,92,255,.35);
  }
  .brand h1 { margin: 0; font-size: 1.15rem; letter-spacing: -0.03em; }
  .brand p { margin: 2px 0 0; color: var(--muted); font-size: .9rem; }
  .pill {
    font-family: "IBM Plex Mono", ui-monospace, monospace;
    font-size: .75rem; color: var(--muted);
    border: 1px solid var(--line); background: rgba(255,255,255,.03);
    padding: 8px 12px; border-radius: 999px;
  }
  .hero {
    background: linear-gradient(160deg, rgba(124,92,255,.18), rgba(20,24,38,.9) 45%, rgba(61,224,197,.08));
    border: 1px solid var(--line); border-radius: 28px; padding: 36px 28px;
    box-shadow: var(--shadow); margin-bottom: 18px; position: relative; overflow: hidden;
  }
  .hero::after {
    content: ""; position: absolute; inset: auto -20% -40% 40%; height: 220px;
    background: radial-gradient(circle, rgba(61,224,197,.25), transparent 60%);
    pointer-events: none;
  }
  .kicker {
    font-family: "IBM Plex Mono", monospace; text-transform: uppercase; letter-spacing: .14em;
    font-size: .72rem; color: var(--accent2); margin: 0 0 10px;
  }
  .hero h2 {
    margin: 0 0 10px; font-size: clamp(2rem, 5vw, 3.2rem); line-height: 1.05;
    letter-spacing: -0.045em; max-width: 16ch;
  }
  .hero .sub { color: var(--muted); font-size: 1.05rem; max-width: 46ch; margin: 0 0 22px; }
  .metrics { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 10px; }
  @media (max-width: 720px) { .metrics { grid-template-columns: repeat(2, minmax(0,1fr)); } }
  .metric {
    background: rgba(0,0,0,.22); border: 1px solid var(--line); border-radius: 16px; padding: 14px 14px 12px;
  }
  .metric .label { color: var(--muted); font-size: .78rem; margin-bottom: 6px; }
  .metric .value { font-size: 1.45rem; font-weight: 700; letter-spacing: -0.03em; }
  .grid { display: grid; grid-template-columns: 1.2fr .8fr; gap: 14px; }
  @media (max-width: 840px) { .grid { grid-template-columns: 1fr; } }
  .card {
    background: linear-gradient(180deg, var(--card), var(--card2));
    border: 1px solid var(--line); border-radius: var(--radius); padding: 20px;
    box-shadow: var(--shadow);
  }
  .card h3 { margin: 0 0 14px; font-size: 1rem; letter-spacing: -0.02em; }
  .row { display: grid; grid-template-columns: 1fr auto; gap: 10px; align-items: center; margin: 10px 0; }
  .name { font-size: .95rem; }
  .meta { color: var(--muted); font-size: .78rem; margin-top: 2px; }
  .track { height: 8px; background: rgba(255,255,255,.06); border-radius: 99px; overflow: hidden; margin-top: 8px; }
  .fill { height: 100%; border-radius: 99px; background: linear-gradient(90deg, var(--accent), var(--accent2)); }
  .hours { font-family: "IBM Plex Mono", monospace; font-size: .85rem; color: var(--muted); }
  .cards { display: grid; gap: 10px; }
  .idcard {
    border-radius: 16px; padding: 14px 16px; border: 1px solid var(--line);
    background: rgba(124,92,255,.08);
  }
  .idcard strong { display: block; margin-bottom: 4px; }
  .idcard span { color: var(--muted); font-size: .9rem; }
  .chips { display: flex; flex-wrap: wrap; gap: 8px; }
  .chip {
    border-radius: 999px; padding: 8px 12px; font-size: .82rem;
    background: rgba(255,255,255,.04); border: 1px solid var(--line); color: var(--text);
  }
  .warn { border-color: rgba(255,176,32,.35); background: rgba(255,176,32,.08); }
  .danger { border-color: rgba(255,93,108,.4); background: rgba(255,93,108,.1); }
  .chart {
    display: flex; align-items: flex-end; gap: 4px; height: 120px; margin-top: 8px;
    padding-top: 8px;
  }
  .bar {
    flex: 1; border-radius: 6px 6px 2px 2px; min-width: 0;
    background: linear-gradient(180deg, var(--accent2), rgba(124,92,255,.55));
    opacity: .9;
  }
  .bar.zero { background: rgba(255,255,255,.06); height: 4px !important; }
  .footer {
    margin-top: 22px; color: var(--muted); font-size: .85rem;
    display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap;
  }
  a { color: var(--accent2); text-decoration: none; }
  a:hover { text-decoration: underline; }
  .stack { display: grid; gap: 14px; margin-top: 14px; }
</style>
</head>
<body>
  <div class="wrap">
    <div class="top">
      <div class="brand">
        <div class="logo">TG</div>
        <div>
          <h1>Work Wrapped</h1>
          <p>Last 30 days from Timeglass MCP</p>
        </div>
      </div>
      <div class="pill" id="window">{{WINDOW}}</div>
    </div>

    <section class="hero">
      <p class="kicker" id="kicker">Your year in review energy · monthly edition</p>
      <h2 id="headline">Loading…</h2>
      <p class="sub" id="oneliner"></p>
      <div class="metrics" id="metrics"></div>
    </section>

    <div class="grid">
      <section class="card">
        <h3>Top projects</h3>
        <div id="projects"></div>
      </section>
      <section class="card">
        <h3>Identity cards</h3>
        <div class="cards" id="identity"></div>
      </section>
    </div>

    <div class="stack">
      <section class="card">
        <h3>Daily rhythm</h3>
        <div class="chart" id="chart"></div>
      </section>
      <div class="grid">
        <section class="card">
          <h3>Top activities</h3>
          <div id="activities"></div>
        </section>
        <section class="card">
          <h3>Shoutouts & budget</h3>
          <div class="chips" id="chips"></div>
        </section>
      </div>
    </div>

    <div class="footer">
      <div>Built with <a href="https://timeglass.ai" target="_blank" rel="noreferrer">Timeglass</a> · no scraping · your work record only</div>
      <div id="source"></div>
    </div>
  </div>
<script id="stats" type="application/json">{{STATS_JSON}}</script>
<script>
(function () {
  const stats = JSON.parse(document.getElementById('stats').textContent);
  const $ = (id) => document.getElementById(id);
  const fmtH = (m) => {
    const h = m / 60;
    if (h >= 10) return Math.round(h) + 'h';
    if (h >= 1) return (Math.round(h * 10) / 10) + 'h';
    return m + 'm';
  };

  $('headline').textContent = stats.headline || (stats.total_hours + 'h this month');
  $('oneliner').textContent = stats.one_liner || '';
  $('window').textContent = (stats.window_start || '') + ' → ' + (stats.window_end || '');
  $('source').textContent = 'source: ' + (stats.source || 'unknown') + (stats.user ? ' · ' + stats.user : '');

  const metrics = [
    ['Total', stats.total_hours + 'h'],
    ['Active days', String(stats.active_days ?? '—')],
    ['Billable', (stats.billable_pct ?? 0) + '%'],
    ['Meetings', (stats.meeting_pct ?? 0) + '%'],
  ];
  $('metrics').innerHTML = metrics.map(([label, value]) =>
    `<div class="metric"><div class="label">${label}</div><div class="value">${value}</div></div>`
  ).join('');

  const projects = stats.top_projects || [];
  $('projects').innerHTML = projects.slice(0, 6).map(p => `
    <div class="row">
      <div>
        <div class="name">${escapeHtml(p.name)}</div>
        <div class="meta">${escapeHtml(p.client || '')}${p.budget_used_pct != null ? ' · budget ' + p.budget_used_pct + '%' : ''}</div>
        <div class="track"><div class="fill" style="width:${Math.min(100, p.share_pct || 0)}%"></div></div>
      </div>
      <div class="hours">${p.hours}h</div>
    </div>
  `).join('') || '<div class="meta">No project rows in this window.</div>';

  const cards = stats.identity_cards || [];
  $('identity').innerHTML = cards.map(c => `
    <div class="idcard"><strong>${escapeHtml(c.title)}</strong><span>${escapeHtml(c.blurb)}</span></div>
  `).join('') || '<div class="meta">No identity cards.</div>';

  const acts = stats.top_activities || [];
  $('activities').innerHTML = acts.slice(0, 8).map(a => `
    <div class="row">
      <div>
        <div class="name">${escapeHtml(a.title)}</div>
        <div class="meta">${escapeHtml(a.project || '')}</div>
      </div>
      <div class="hours">${fmtH(a.minutes || 0)}</div>
    </div>
  `).join('') || '<div class="meta">No activities.</div>';

  const series = stats.daily_series || [];
  const maxM = Math.max(1, ...series.map(d => d.minutes || 0));
  $('chart').innerHTML = series.map(d => {
    const h = Math.max(4, Math.round(((d.minutes || 0) / maxM) * 112));
    const z = (d.minutes || 0) === 0 ? ' zero' : '';
    return `<div class="bar${z}" style="height:${h}px" title="${d.date}: ${fmtH(d.minutes || 0)}"></div>`;
  }).join('');

  const chips = [];
  (stats.shoutouts || []).forEach(s => chips.push({t: s, c: ''}));
  (stats.budget_alerts || []).forEach(b => chips.push({
    t: `${b.level === 'over' ? 'OVER' : 'NEAR'} ${b.name} · ${b.budget_used_pct}%`,
    c: b.level === 'over' ? 'danger' : 'warn'
  }));
  (stats.top_apps || []).slice(0, 4).forEach(a => chips.push({t: a.name + ' · ' + fmtH(a.minutes), c: ''}));
  $('chips').innerHTML = chips.map(c => `<span class="chip ${c.c}">${escapeHtml(c.t)}</span>`).join('')
    || '<span class="chip">No shoutouts yet</span>';

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, ch => ({
      '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
    }[ch]));
  }
})();
</script>
</body>
</html>
"""
