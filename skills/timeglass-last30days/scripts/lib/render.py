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
    lines.append(
        f"| Meetings | **{stats.meeting_pct}%** ({_fmt_hours(stats.meeting_minutes)} · {stats.meeting_count} meetings) |"
    )
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
            lines.append(f"| {p['name']} | {p['hours']}h | {p['share_pct']}% | {budget} |")
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
        lines.append(
            f"  {_bar(p['share_pct'])}  {p['share_pct']:5.1f}%  {p['hours']:5.1f}h  {p['name']}"
        )
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
        # Prefer sibling templates/wrapped.html when engine is run from skill tree
        candidate = Path(__file__).resolve().parents[2] / "templates" / "wrapped.html"
        if candidate.is_file():
            tpl = candidate.read_text(encoding="utf-8")
        else:
            tpl = DEFAULT_HTML_TEMPLATE

    payload = json.dumps(stats.to_dict(), ensure_ascii=False)
    payload = payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    title = html.escape(f"Work Wrapped — {stats.user or 'Last 30 Days'}")
    return (
        tpl.replace("{{TITLE}}", title)
        .replace("{{WINDOW}}", html.escape(f"{stats.window_start} → {stats.window_end}"))
        .replace("{{STATS_JSON}}", payload)
    )


# Fallback only if templates/wrapped.html is missing at runtime.
DEFAULT_HTML_TEMPLATE = "<!DOCTYPE html><html><head><meta charset='utf-8'><title>{{TITLE}}</title></head><body><pre id='s'></pre><script>document.getElementById('s').textContent=document.getElementById('stats').textContent;</script><script id='stats' type='application/json'>{{STATS_JSON}}</script></body></html>"
