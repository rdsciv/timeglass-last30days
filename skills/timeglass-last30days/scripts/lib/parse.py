"""Parse Timeglass MCP / fixture payloads into a normalized MonthBundle."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any


def try_parse_json(text: str) -> Any:
    trimmed = (text or "").strip()
    if not trimmed:
        return None
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", trimmed, re.I)
    candidate = fence.group(1).strip() if fence else trimmed
    for blob in (candidate,):
        if blob.startswith("{") or blob.startswith("["):
            try:
                return json.loads(blob)
            except json.JSONDecodeError:
                pass
    m = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", candidate)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            return None
    return None


def as_array(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in (
            "items",
            "data",
            "results",
            "rows",
            "records",
            "entries",
            "projects",
            "teams",
            "workspaces",
            "users",
            "activities",
            "activity_items",
            "activityItems",
            "minutes",
            "meetings",
            "summaries",
            "project_daily_summary",
            "user_daily_summary",
        ):
            if isinstance(value.get(key), list):
                return value[key]
        if isinstance(value.get("data"), dict):
            return as_array(value["data"])
    return []


def sfield(obj: dict[str, Any], keys: list[str], default: str = "") -> str:
    for k in keys:
        v = obj.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return str(v)
        if isinstance(v, dict):
            for nk in ("name", "title", "label"):
                if isinstance(v.get(nk), str) and v[nk].strip():
                    return v[nk].strip()
    return default


def nfield(obj: dict[str, Any], keys: list[str]) -> float | None:
    for k in keys:
        v = obj.get(k)
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str) and v.strip():
            try:
                return float(v.strip().replace(",", ""))
            except ValueError:
                continue
    return None


def minutes_from(obj: dict[str, Any]) -> int:
    m = nfield(
        obj,
        [
            "minutes",
            "duration_minutes",
            "durationMinutes",
            "mins",
            "total_minutes",
            "totalMinutes",
            "tracked_minutes",
            "trackedMinutes",
            "used_minutes",
            "usedMinutes",
            "logged_minutes",
            "loggedMinutes",
            "billable_minutes",
            "billableMinutes",
        ],
    )
    if m is not None:
        return int(round(m))
    h = nfield(obj, ["hours", "duration_hours", "durationHours", "total_hours", "totalHours", "logged_hours"])
    if h is not None:
        # Heuristic: huge numbers are likely minutes mislabeled
        if h > 500:
            return int(round(h))
        return int(round(h * 60))
    sec = nfield(obj, ["seconds", "duration_seconds", "durationSeconds", "duration"])
    if sec is not None:
        return int(round(sec / 60)) if sec > 180 else int(round(sec))
    return 0


def extract_team_ids(raw: str | Any) -> list[dict[str, str]]:
    data = try_parse_json(raw) if isinstance(raw, str) else raw
    out: list[dict[str, str]] = []
    seen: set[str] = set()

    def walk(node: Any, parent_workspace: str = "") -> None:
        if not isinstance(node, dict):
            if isinstance(node, list):
                for x in node:
                    walk(x, parent_workspace)
            return
        wid = sfield(node, ["workspace_id", "workspaceId"]) or parent_workspace
        tid = sfield(node, ["team_id", "teamId"])
        # Never treat workspace_id as team
        if tid and tid not in seen and tid != sfield(node, ["workspace_id", "workspaceId"]):
            seen.add(tid)
            out.append(
                {
                    "team_id": tid,
                    "name": sfield(node, ["name", "title"], tid),
                    "workspace_id": wid,
                }
            )
        for key in ("children", "team_tree", "teamTree", "teams"):
            if isinstance(node.get(key), list):
                for c in node[key]:
                    walk(c, wid)
        if isinstance(node.get("workspaces"), list):
            for ws in node["workspaces"]:
                walk(ws, sfield(ws, ["workspace_id", "workspaceId"]) or wid)
        if isinstance(node.get("items"), list):
            for it in node["items"]:
                walk(it, wid)

    walk(data)
    return out


def extract_workspace_ids(raw: str | Any) -> list[dict[str, str]]:
    """Return workspace_id entries (never confuse with team_id)."""
    data = try_parse_json(raw) if isinstance(raw, str) else raw
    out: list[dict[str, str]] = []
    seen: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, list):
            for x in node:
                walk(x)
            return
        if not isinstance(node, dict):
            return
        wid = sfield(node, ["workspace_id", "workspaceId"])
        if wid and wid not in seen:
            # Don't pick up nested team-only nodes that only have team_id
            seen.add(wid)
            out.append({"workspace_id": wid, "name": sfield(node, ["name", "title"], wid)})
        for key in ("workspaces", "items", "data", "results"):
            if isinstance(node.get(key), list):
                for c in node[key]:
                    walk(c)

    walk(data)
    return out


@dataclass
class ProjectRow:
    project_id: str
    name: str
    client: str
    minutes: int
    budget_hours: float | None
    billable: bool
    budget_used_pct: float | None = None


@dataclass
class DayRow:
    date: str
    minutes: int
    billable_minutes: int = 0
    meeting_minutes: int = 0


@dataclass
class ActivityRow:
    date: str
    project_id: str
    project_name: str
    title: str
    minutes: int
    app: str = ""


@dataclass
class MeetingRow:
    date: str
    title: str
    project_id: str
    client: str
    minutes: int
    attendees: int = 0


@dataclass
class MonthBundle:
    window_start: str
    window_end: str
    timezone: str = "UTC"
    user: str = ""
    workspace: str = ""
    source: str = "unknown"
    projects: list[ProjectRow] = field(default_factory=list)
    days: list[DayRow] = field(default_factory=list)
    activities: list[ActivityRow] = field(default_factory=list)
    meetings: list[MeetingRow] = field(default_factory=list)
    project_daily: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def total_minutes(self) -> int:
        if self.days:
            return sum(d.minutes for d in self.days)
        return sum(p.minutes for p in self.projects)

    @property
    def total_hours(self) -> float:
        return round(self.total_minutes / 60.0, 1)


def window_bounds(days: int = 30, end: date | None = None) -> tuple[date, date]:
    end = end or date.today()
    start = end - timedelta(days=max(days - 1, 0))
    return start, end


def iso_day_bounds(d: date) -> tuple[str, str]:
    start = datetime(d.year, d.month, d.day, 0, 0, 0)
    end = datetime(d.year, d.month, d.day, 23, 59, 59)
    return start.isoformat() + "Z", end.isoformat() + "Z"


def bundle_from_fixture(data: dict[str, Any]) -> MonthBundle:
    meta = data.get("meta") or {}
    projects: list[ProjectRow] = []
    for p in data.get("projects") or []:
        if not isinstance(p, dict):
            continue
        mins = int(p.get("minutes") or minutes_from(p))
        budget = nfield(p, ["budget_hours", "budgetHours"])
        pct = nfield(p, ["budget_used_pct", "budgetUsedPct"])
        if pct is None and budget:
            pct = round(100.0 * (mins / 60.0) / budget, 1)
        projects.append(
            ProjectRow(
                project_id=sfield(p, ["project_id", "projectId", "id"], sfield(p, ["name"])),
                name=sfield(p, ["name", "project_name", "title"], "Untitled"),
                client=sfield(p, ["client", "client_name", "clientName"], ""),
                minutes=mins,
                budget_hours=budget,
                billable=bool(p.get("billable")) if "billable" in p else False,
                budget_used_pct=pct,
            )
        )

    days: list[DayRow] = []
    for d in data.get("user_daily_summary") or []:
        if not isinstance(d, dict):
            continue
        days.append(
            DayRow(
                date=sfield(d, ["date", "day", "work_date"])[:10],
                minutes=int(d.get("minutes") or minutes_from(d)),
                billable_minutes=int(d.get("billable_minutes") or d.get("billableMinutes") or 0),
                meeting_minutes=int(d.get("meeting_minutes") or d.get("meetingMinutes") or 0),
            )
        )

    activities: list[ActivityRow] = []
    for a in data.get("activities") or []:
        if not isinstance(a, dict):
            continue
        activities.append(
            ActivityRow(
                date=sfield(a, ["date", "day"])[:10],
                project_id=sfield(a, ["project_id", "projectId"]),
                project_name=sfield(a, ["project_name", "projectName", "project"]),
                title=sfield(a, ["title", "name", "summary", "description"], "Activity"),
                minutes=int(a.get("minutes") or minutes_from(a)),
                app=sfield(a, ["app", "application", "source_app"]),
            )
        )

    meetings: list[MeetingRow] = []
    for m in data.get("meetings") or []:
        if not isinstance(m, dict):
            continue
        meetings.append(
            MeetingRow(
                date=sfield(m, ["date", "day", "started_at", "start"])[:10],
                title=sfield(m, ["title", "name", "summary"], "Meeting"),
                project_id=sfield(m, ["project_id", "projectId"]),
                client=sfield(m, ["client", "client_name"]),
                minutes=int(m.get("minutes") or minutes_from(m)),
                attendees=int(nfield(m, ["attendees", "attendee_count", "participant_count"]) or 0),
            )
        )

    return MonthBundle(
        window_start=sfield(meta, ["window_start", "start"], ""),
        window_end=sfield(meta, ["window_end", "end"], ""),
        timezone=sfield(meta, ["timezone", "tz"], "UTC"),
        user=sfield(meta, ["user", "user_name", "name"], ""),
        workspace=sfield(meta, ["workspace", "workspace_name"], ""),
        source=sfield(meta, ["source"], "fixture"),
        projects=projects,
        days=days,
        activities=activities,
        meetings=meetings,
        project_daily=[x for x in (data.get("project_daily_summary") or []) if isinstance(x, dict)],
    )


def _parse_projects(raw: str) -> list[ProjectRow]:
    data = try_parse_json(raw)
    rows: list[ProjectRow] = []
    for p in as_array(data):
        if not isinstance(p, dict):
            continue
        mins = minutes_from(p)
        # sometimes nested totals
        if mins == 0:
            mins = minutes_from(p.get("totals") or {}) if isinstance(p.get("totals"), dict) else 0
        budget = nfield(p, ["budget_hours", "budgetHours", "budget"])
        name = sfield(p, ["name", "project_name", "title"], "Untitled")
        rows.append(
            ProjectRow(
                project_id=sfield(p, ["project_id", "projectId", "id"], name),
                name=name,
                client=sfield(p, ["client", "client_name", "clientName", "account"], ""),
                minutes=mins,
                budget_hours=budget,
                billable=bool(p.get("billable")) if "billable" in p else False,
                budget_used_pct=nfield(p, ["budget_used_pct", "budgetUsedPct", "percent_used"]),
            )
        )
    return rows


def _parse_user_daily(raw: str) -> list[DayRow]:
    data = try_parse_json(raw)
    out: list[DayRow] = []
    for d in as_array(data):
        if not isinstance(d, dict):
            continue
        day = sfield(
            d,
            [
                "date",
                "day",
                "work_date",
                "summary_date",
                "start_date",
                "startDate",
                "start",
            ],
        )[:10]
        if not day:
            continue
        out.append(
            DayRow(
                date=day,
                minutes=minutes_from(d),
                billable_minutes=int(nfield(d, ["billable_minutes", "billableMinutes"]) or 0),
                meeting_minutes=int(nfield(d, ["meeting_minutes", "meetingMinutes"]) or 0),
            )
        )
    out.sort(key=lambda x: x.date)
    return out


def _parse_activities(raw: str) -> list[ActivityRow]:
    data = try_parse_json(raw)
    out: list[ActivityRow] = []
    for a in as_array(data):
        if not isinstance(a, dict):
            continue
        day = sfield(
            a,
            [
                "date",
                "day",
                "started_at",
                "start",
                "start_timestamp",
                "start_time_absolute",
                "startTimeAbsolute",
            ],
        )[:10]
        out.append(
            ActivityRow(
                date=day,
                project_id=sfield(a, ["project_id", "projectId"]),
                project_name=sfield(a, ["project_name", "projectName", "project"]),
                title=sfield(
                    a,
                    [
                        "objective",
                        "title",
                        "name",
                        "summary",
                        "description",
                        "reason",
                    ],
                    "Activity",
                ),
                minutes=minutes_from(a),
                app=sfield(a, ["app", "application", "source_app", "window_app"]),
            )
        )
    return out


def _parse_meetings(raw: str) -> list[MeetingRow]:
    data = try_parse_json(raw)
    out: list[MeetingRow] = []
    for m in as_array(data):
        if not isinstance(m, dict):
            continue
        out.append(
            MeetingRow(
                date=sfield(m, ["date", "day", "started_at", "start"])[:10],
                title=sfield(m, ["title", "name", "summary"], "Meeting"),
                project_id=sfield(m, ["project_id", "projectId"]),
                client=sfield(m, ["client", "client_name"]),
                minutes=minutes_from(m),
                attendees=int(nfield(m, ["attendees", "attendee_count", "participant_count"]) or 0),
            )
        )
    return out


def _parse_project_daily(raw: str) -> list[dict[str, Any]]:
    data = try_parse_json(raw)
    out: list[dict[str, Any]] = []
    for row in as_array(data):
        if not isinstance(row, dict):
            continue
        out.append(
            {
                "date": sfield(row, ["date", "day"])[:10],
                "project_id": sfield(row, ["project_id", "projectId"]),
                "project_name": sfield(row, ["project_name", "projectName", "name"]),
                "client": sfield(row, ["client", "client_name"]),
                "minutes": minutes_from(row),
                "billable": bool(row.get("billable")) if "billable" in row else False,
            }
        )
    return out


def merge_mcp_entities(
    *,
    window_start: str,
    window_end: str,
    projects_raw: str = "",
    user_daily_raw: str = "",
    activities_raw: str = "",
    meetings_raw: str = "",
    project_daily_raw: str = "",
    user: str = "",
    workspace: str = "",
    timezone: str = "UTC",
    warnings: list[str] | None = None,
) -> MonthBundle:
    projects = _parse_projects(projects_raw) if projects_raw else []
    days = _parse_user_daily(user_daily_raw) if user_daily_raw else []
    activities = _parse_activities(activities_raw) if activities_raw else []
    meetings = _parse_meetings(meetings_raw) if meetings_raw else []
    project_daily = _parse_project_daily(project_daily_raw) if project_daily_raw else []

    # If projects empty but project_daily present, roll up
    if not projects and project_daily:
        roll: dict[str, ProjectRow] = {}
        for row in project_daily:
            pid = row.get("project_id") or row.get("project_name") or "unknown"
            if pid not in roll:
                roll[pid] = ProjectRow(
                    project_id=str(pid),
                    name=str(row.get("project_name") or pid),
                    client=str(row.get("client") or ""),
                    minutes=0,
                    budget_hours=None,
                    billable=bool(row.get("billable")) if "billable" in row else False,
                )
            roll[pid].minutes += int(row.get("minutes") or 0)
        projects = list(roll.values())

    # If days empty, synthesize from project_daily
    if not days and project_daily:
        by_day: dict[str, int] = {}
        for row in project_daily:
            d = str(row.get("date") or "")[:10]
            if not d:
                continue
            by_day[d] = by_day.get(d, 0) + int(row.get("minutes") or 0)
        days = [DayRow(date=d, minutes=m) for d, m in sorted(by_day.items())]

    return MonthBundle(
        window_start=window_start,
        window_end=window_end,
        timezone=timezone,
        user=user,
        workspace=workspace,
        source="mcp",
        projects=sorted(projects, key=lambda p: p.minutes, reverse=True),
        days=days,
        activities=activities,
        meetings=meetings,
        project_daily=project_daily,
        warnings=list(warnings or []),
    )
