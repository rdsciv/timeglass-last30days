"""Derive Work Wrapped stats from a MonthBundle."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any

from .parse import MonthBundle


def _parse_date(s: str) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def _fmt_hours(minutes: int) -> str:
    h = minutes / 60.0
    if h >= 10:
        return f"{h:.0f}h"
    if h >= 1:
        return f"{h:.1f}h".replace(".0h", "h")
    return f"{minutes}m"


def _weekday_name(d: date) -> str:
    return d.strftime("%A")


@dataclass
class WrappedStats:
    version: str
    window_start: str
    window_end: str
    timezone: str
    user: str
    workspace: str
    source: str
    total_minutes: int
    total_hours: float
    active_days: int
    avg_hours_active_day: float
    billable_minutes: int
    billable_pct: float
    meeting_minutes: int
    meeting_pct: float
    deep_work_minutes: int
    top_projects: list[dict[str, Any]] = field(default_factory=list)
    top_clients: list[dict[str, Any]] = field(default_factory=list)
    top_activities: list[dict[str, Any]] = field(default_factory=list)
    top_apps: list[dict[str, Any]] = field(default_factory=list)
    busiest_day: dict[str, Any] | None = None
    quietest_active_day: dict[str, Any] | None = None
    weekday_mix: list[dict[str, Any]] = field(default_factory=list)
    daily_series: list[dict[str, Any]] = field(default_factory=list)
    meetings: list[dict[str, Any]] = field(default_factory=list)
    meeting_count: int = 0
    budget_alerts: list[dict[str, Any]] = field(default_factory=list)
    identity_cards: list[dict[str, str]] = field(default_factory=list)
    headline: str = ""
    one_liner: str = ""
    shoutouts: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_stats(bundle: MonthBundle, version: str = "1.0.0") -> WrappedStats:
    total = bundle.total_minutes
    active_days = sum(1 for d in bundle.days if d.minutes > 0)
    if active_days == 0 and bundle.project_daily:
        active_days = len({r.get("date") for r in bundle.project_daily if r.get("minutes")})

    billable = 0
    if bundle.days and any(d.billable_minutes for d in bundle.days):
        billable = sum(d.billable_minutes for d in bundle.days)
    else:
        billable = sum(p.minutes for p in bundle.projects if p.billable)

    meeting_minutes = sum(m.minutes for m in bundle.meetings)
    if meeting_minutes == 0 and bundle.days:
        meeting_minutes = sum(d.meeting_minutes for d in bundle.days)

    deep_work = max(total - meeting_minutes, 0)
    billable_pct = round(100.0 * billable / total, 1) if total else 0.0
    meeting_pct = round(100.0 * meeting_minutes / total, 1) if total else 0.0
    avg = round((total / 60.0) / active_days, 2) if active_days else 0.0

    # Projects
    top_projects = []
    for p in sorted(bundle.projects, key=lambda x: x.minutes, reverse=True):
        if p.minutes <= 0:
            continue
        top_projects.append(
            {
                "project_id": p.project_id,
                "name": p.name,
                "client": p.client,
                "minutes": p.minutes,
                "hours": round(p.minutes / 60.0, 1),
                "share_pct": round(100.0 * p.minutes / total, 1) if total else 0.0,
                "billable": p.billable,
                "budget_hours": p.budget_hours,
                "budget_used_pct": p.budget_used_pct
                if p.budget_used_pct is not None
                else (
                    round(100.0 * (p.minutes / 60.0) / p.budget_hours, 1) if p.budget_hours else None
                ),
            }
        )

    # Clients
    client_mins: Counter[str] = Counter()
    for p in bundle.projects:
        label = p.client or p.name
        client_mins[label] += p.minutes
    top_clients = [
        {
            "name": name,
            "minutes": mins,
            "hours": round(mins / 60.0, 1),
            "share_pct": round(100.0 * mins / total, 1) if total else 0.0,
        }
        for name, mins in client_mins.most_common()
        if mins > 0
    ]

    # Activities
    act_mins: Counter[str] = Counter()
    act_meta: dict[str, str] = {}
    for a in bundle.activities:
        key = a.title.strip() or "Activity"
        act_mins[key] += a.minutes
        if a.project_name:
            act_meta[key] = a.project_name
    top_activities = [
        {
            "title": title,
            "minutes": mins,
            "hours": round(mins / 60.0, 1),
            "project": act_meta.get(title, ""),
        }
        for title, mins in act_mins.most_common(12)
        if mins > 0
    ]

    # Apps
    app_mins: Counter[str] = Counter()
    for a in bundle.activities:
        if a.app:
            app_mins[a.app] += a.minutes
    top_apps = [
        {"name": name, "minutes": mins, "hours": round(mins / 60.0, 1)}
        for name, mins in app_mins.most_common(10)
    ]

    # Days
    busiest = None
    quietest = None
    if bundle.days:
        ranked = sorted([d for d in bundle.days if d.minutes > 0], key=lambda d: d.minutes, reverse=True)
        if ranked:
            b = ranked[0]
            busiest = {"date": b.date, "minutes": b.minutes, "hours": round(b.minutes / 60.0, 1)}
            q = ranked[-1]
            quietest = {"date": q.date, "minutes": q.minutes, "hours": round(q.minutes / 60.0, 1)}

    weekday_mins: dict[str, int] = defaultdict(int)
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for d in bundle.days:
        dd = _parse_date(d.date)
        if dd:
            weekday_mins[_weekday_name(dd)] += d.minutes
    weekday_mix = [
        {
            "weekday": w,
            "minutes": weekday_mins.get(w, 0),
            "hours": round(weekday_mins.get(w, 0) / 60.0, 1),
        }
        for w in order
    ]

    daily_series = [
        {"date": d.date, "minutes": d.minutes, "hours": round(d.minutes / 60.0, 2)}
        for d in sorted(bundle.days, key=lambda x: x.date)
    ]

    meetings = [
        {
            "date": m.date,
            "title": m.title,
            "client": m.client,
            "minutes": m.minutes,
            "attendees": m.attendees,
        }
        for m in sorted(bundle.meetings, key=lambda x: (x.date, -x.minutes))
    ]

    budget_alerts = []
    for p in top_projects:
        pct = p.get("budget_used_pct")
        if pct is None:
            continue
        if pct >= 100:
            level = "over"
        elif pct >= 85:
            level = "near"
        else:
            continue
        budget_alerts.append(
            {
                "name": p["name"],
                "budget_used_pct": pct,
                "hours": p["hours"],
                "budget_hours": p.get("budget_hours"),
                "level": level,
            }
        )

    # Identity cards (Spotify-wrapped style personas)
    identity_cards: list[dict[str, str]] = []
    if meeting_pct >= 30:
        identity_cards.append(
            {
                "title": "Meeting Main Character",
                "blurb": f"{meeting_pct:.0f}% of your month was meetings. Calendar was the product.",
            }
        )
    if deep_work >= total * 0.55 and total:
        identity_cards.append(
            {
                "title": "Deep Work Resident",
                "blurb": f"{_fmt_hours(deep_work)} outside meetings. You protected focus blocks.",
            }
        )
    if top_clients and top_clients[0]["share_pct"] >= 40:
        identity_cards.append(
            {
                "title": f"{top_clients[0]['name']} Whisperer",
                "blurb": f"{top_clients[0]['share_pct']:.0f}% of the month went to one client relationship.",
            }
        )
    if active_days >= 22:
        identity_cards.append(
            {
                "title": "Consistency Machine",
                "blurb": f"{active_days} active days in the window. Showed up on repeat.",
            }
        )
    if billable_pct >= 75:
        identity_cards.append(
            {
                "title": "Billable Beast",
                "blurb": f"{billable_pct:.0f}% billable mix. Finance will send a thank-you note.",
            }
        )
    if not identity_cards:
        identity_cards.append(
            {
                "title": "Working Professional",
                "blurb": "A balanced month across projects, meetings, and the unglamorous glue work.",
            }
        )

    # Headline / one-liner
    top_name = top_projects[0]["name"] if top_projects else "your work"
    headline = f"{_fmt_hours(total)} across {active_days} days"
    one_liner = (
        f"Your last 30 days: {bundle.total_hours}h tracked"
        + (f", led by {top_name}" if top_projects else "")
        + (f", {meeting_pct:.0f}% meetings" if meeting_minutes else "")
        + "."
    )

    shoutouts: list[str] = []
    if busiest:
        shoutouts.append(f"Busiest day: {busiest['date']} · {busiest['hours']}h")
    if top_activities:
        shoutouts.append(f"Top activity: {top_activities[0]['title']} · {_fmt_hours(top_activities[0]['minutes'])}")
    if top_apps:
        shoutouts.append(f"Home app: {top_apps[0]['name']}")
    if budget_alerts:
        shoutouts.append(
            f"Budget watch: {budget_alerts[0]['name']} at {budget_alerts[0]['budget_used_pct']}%"
        )

    return WrappedStats(
        version=version,
        window_start=bundle.window_start,
        window_end=bundle.window_end,
        timezone=bundle.timezone,
        user=bundle.user,
        workspace=bundle.workspace,
        source=bundle.source,
        total_minutes=total,
        total_hours=bundle.total_hours,
        active_days=active_days,
        avg_hours_active_day=avg,
        billable_minutes=billable,
        billable_pct=billable_pct,
        meeting_minutes=meeting_minutes,
        meeting_pct=meeting_pct,
        deep_work_minutes=deep_work,
        top_projects=top_projects[:10],
        top_clients=top_clients[:10],
        top_activities=top_activities,
        top_apps=top_apps,
        busiest_day=busiest,
        quietest_active_day=quietest,
        weekday_mix=weekday_mix,
        daily_series=daily_series,
        meetings=meetings[:40],
        meeting_count=len(bundle.meetings),
        budget_alerts=budget_alerts,
        identity_cards=identity_cards[:4],
        headline=headline,
        one_liner=one_liner,
        shoutouts=shoutouts,
        warnings=list(bundle.warnings),
    )
