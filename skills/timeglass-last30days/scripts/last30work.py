#!/usr/bin/env python3
"""timeglass-last30days — Work Wrapped from Timeglass MCP (no scraping).

Examples:
  python3 last30work.py --demo
  python3 last30work.py --demo --emit html --out ./out
  python3 last30work.py --days 30
  python3 last30work.py --fixture path/to/export.json
  python3 last30work.py --preflight
  python3 last30work.py --doctor
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
REPO_ROOT = SKILL_DIR.parents[1]
FIXTURE_DEFAULT = SKILL_DIR / "fixtures" / "sample_month.json"
VERSION = "1.0.0"

# Allow `python3 scripts/last30work.py` without installing a package
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from lib.mcp_client import DEFAULT_MCP_URL, McpConfig, McpError, TimeglassMcpClient  # noqa: E402
from lib.parse import (  # noqa: E402
    bundle_from_fixture,
    extract_team_ids,
    extract_workspace_ids,
    merge_mcp_entities,
    try_parse_json,
    window_bounds,
)
from lib.render import render_compact, render_html, render_markdown  # noqa: E402
from lib.stats import compute_stats  # noqa: E402


def _eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def load_fixture(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"Fixture must be a JSON object: {path}")
    return data


def fetch_mcp_bundle(days: int, end: date | None, team_id: str | None) -> Any:
    cfg = McpConfig.from_env()
    if not cfg:
        raise SystemExit(
            "No MCP token. Set TIMEGASS_MCP_TOKEN (Raycast/AI-connector audience),\n"
            "or run with --demo / --fixture. Desktop upload tokens will 401 — expected."
        )
    client = TimeglassMcpClient(cfg)
    warnings: list[str] = []

    try:
        client.initialize()
    except McpError as e:
        raise SystemExit(f"MCP initialize failed: {e}") from e

    # Resolve workspace + team (never confuse the two)
    resolved_team = team_id
    resolved_workspace: str | None = None
    dir_raw = ""
    try:
        dir_raw = client.query_directory("teams")
    except McpError as e:
        warnings.append(f"directory/teams: {e}")
        try:
            dir_raw = client.query_directory("workspaces")
        except McpError as e2:
            warnings.append(f"directory/workspaces: {e2}")

    if dir_raw:
        teams = extract_team_ids(dir_raw)
        workspaces = extract_workspace_ids(dir_raw)
        if not resolved_team and teams:
            resolved_team = teams[0]["team_id"]
            resolved_workspace = teams[0].get("workspace_id") or None
        if not resolved_workspace and workspaces:
            resolved_workspace = workspaces[0]["workspace_id"]
        if not resolved_workspace and teams:
            resolved_workspace = teams[0].get("workspace_id") or None

    # Current product MCP uses set_workspace(workspaceId). Fall back to legacy set_team.
    if resolved_workspace:
        try:
            client.set_workspace(resolved_workspace)
        except McpError as e:
            warnings.append(f"set_workspace({resolved_workspace}): {e}")
            if resolved_team:
                try:
                    client.set_team(resolved_team)
                except McpError as e2:
                    warnings.append(f"set_team({resolved_team}): {e2}")
    elif resolved_team:
        try:
            client.set_team(resolved_team)
        except McpError as e:
            warnings.append(f"set_team({resolved_team}): {e}")

    start_d, end_d = window_bounds(days=days, end=end)
    start_iso = datetime(start_d.year, start_d.month, start_d.day).isoformat() + "Z"
    end_iso = datetime(end_d.year, end_d.month, end_d.day, 23, 59, 59).isoformat() + "Z"

    def q(entity: str) -> str:
        try:
            return client.query_work_records(
                entity,
                start=start_iso,
                end=end_iso,
                startDate=start_d.isoformat(),
                endDate=end_d.isoformat(),
                teamId=resolved_team,
            )
        except McpError as e:
            warnings.append(f"{entity}: {e}")
            return ""

    projects_raw = q("projects")
    user_daily_raw = q("user_daily_summary")
    activities_raw = q("activities")
    meetings_raw = q("meetings")
    project_daily_raw = q("project_daily_summary")
    # optional enrichments when available
    clients_raw = q("clients")
    activity_items_raw = q("activity_items")

    user = os.environ.get("TIMEGASS_USER_NAME", "")
    workspace = os.environ.get("TIMEGASS_WORKSPACE_NAME", "")
    # Best-effort identity from directory payload
    try:
        draw = client.query_directory("workspaces")
        parsed = try_parse_json(draw)
        if isinstance(parsed, dict):
            wss = parsed.get("workspaces") or parsed.get("items") or []
            if isinstance(wss, list) and wss and isinstance(wss[0], dict):
                workspace = workspace or str(wss[0].get("name") or "")
    except McpError:
        pass

    # Prefer richer activity_items titles when activities are sparse/generic
    act_for_merge = activities_raw
    if activity_items_raw and (
        not activities_raw
        or '"title":"Activity"' in activities_raw
        or activities_raw.count('"') < 40
    ):
        act_for_merge = activity_items_raw

    return merge_mcp_entities(
        window_start=start_d.isoformat(),
        window_end=end_d.isoformat(),
        projects_raw=projects_raw,
        user_daily_raw=user_daily_raw,
        activities_raw=act_for_merge,
        meetings_raw=meetings_raw,
        project_daily_raw=project_daily_raw,
        user=user,
        workspace=workspace,
        timezone=os.environ.get("TZ", "UTC"),
        warnings=warnings,
    )


def preflight() -> int:
    cfg = McpConfig.from_env()
    print(f"timeglass-last30days v{VERSION}")
    print(f"skill_dir: {SKILL_DIR}")
    print(f"fixture:   {FIXTURE_DEFAULT} ({'ok' if FIXTURE_DEFAULT.is_file() else 'missing'})")
    print(f"mcp_url:   {os.environ.get('TIMEGASS_MCP_URL', DEFAULT_MCP_URL)}")
    if cfg:
        masked = cfg.token[:4] + "…" + cfg.token[-4:] if len(cfg.token) > 10 else "(set)"
        print(f"token:     present ({masked})")
    else:
        print("token:     missing — demo/fixture still work")
    print("writes:    only paths you pass to --out (default cwd-relative out/)")
    print("network:   only when not using --demo/--fixture")
    print("scraping:  never")
    return 0


def doctor() -> int:
    code = preflight()
    cfg = McpConfig.from_env()
    if not cfg:
        print("\nDOCTOR: no token — run --demo, or connect Timeglass AI assistant / Raycast OAuth.")
        print("  Docs: https://timeglass.ai/help/ai-assistant/connect-ai-assistant")
        return code
    client = TimeglassMcpClient(cfg)
    print("\nProbing MCP…")
    try:
        client.initialize()
        print("  initialize: ok")
    except McpError as e:
        print(f"  initialize: FAIL — {e}")
        print("  Hint: desktop upload tokens are wrong audience. Use AI connector / Raycast mcp:read.")
        return 1
    try:
        tools = client.list_tools()
        names = sorted({t.get("name") for t in tools if isinstance(t, dict)})
        print(f"  tools/list: {len(names)} tools")
        for n in names:
            print(f"    - {n}")
    except McpError as e:
        print(f"  tools/list: FAIL — {e}")
        return 1
    try:
        raw = client.query_directory("teams")
        teams = extract_team_ids(raw)
        print(f"  teams found: {len(teams)}")
        for t in teams[:5]:
            print(f"    - {t['name']} ({t['team_id']})")
        if not teams:
            raw2 = client.query_directory("workspaces")
            teams = extract_team_ids(raw2)
            print(f"  teams via workspaces: {len(teams)}")
    except McpError as e:
        print(f"  directory: FAIL — {e}")
        return 1
    print("\nDOCTOR: ready. Run without --demo to build your Work Wrapped.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="last30work",
        description="Work Wrapped: last 30 days of your work from Timeglass MCP.",
    )
    p.add_argument("--days", type=int, default=30, help="Lookback window in days (default 30)")
    p.add_argument("--end", type=str, default=None, help="Window end date YYYY-MM-DD (default today)")
    p.add_argument("--demo", action="store_true", help="Use bundled fixture (no network)")
    p.add_argument("--fixture", type=str, default=None, help="Path to JSON fixture/export")
    p.add_argument("--team-id", type=str, default=None, help="Timeglass team_id (not workspace_id)")
    p.add_argument(
        "--emit",
        choices=["compact", "markdown", "json", "html", "all"],
        default="compact",
        help="Output format (default compact)",
    )
    p.add_argument("--out", type=str, default=None, help="Directory to write artifacts")
    p.add_argument("--preflight", action="store_true", help="Show config plan; no research")
    p.add_argument("--doctor", action="store_true", help="Probe MCP auth + tools")
    p.add_argument("--version", action="store_true", help="Print version and exit")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.version:
        print(VERSION)
        return 0
    if args.preflight:
        return preflight()
    if args.doctor:
        return doctor()

    end = date.fromisoformat(args.end) if args.end else None

    if args.demo or args.fixture:
        path = Path(args.fixture) if args.fixture else FIXTURE_DEFAULT
        if not path.is_file():
            raise SystemExit(f"Fixture not found: {path}")
        data = load_fixture(path)
        bundle = bundle_from_fixture(data)
        # Optionally shift window labels if user passed --end/--days on demo
        if args.end or args.days != 30:
            s, e = window_bounds(days=args.days, end=end)
            bundle.window_start = bundle.window_start or s.isoformat()
            bundle.window_end = bundle.window_end or e.isoformat()
    else:
        bundle = fetch_mcp_bundle(days=args.days, end=end, team_id=args.team_id)

    if bundle.total_minutes == 0:
        _eprint("Warning: zero minutes in window. Is capture running? Are drafts approved for MCP?")

    stats = compute_stats(bundle, version=VERSION)
    emit = args.emit

    out_dir = Path(args.out).expanduser() if args.out else None
    if emit in ("html", "all", "markdown", "json") and out_dir is None:
        out_dir = Path("out")
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []

    if emit in ("json", "all") and out_dir is not None:
        jp = out_dir / "work-wrapped.json"
        jp.write_text(json.dumps(stats.to_dict(), indent=2), encoding="utf-8")
        written.append(jp)

    md_text = render_markdown(stats)
    if emit in ("markdown", "all") and out_dir is not None:
        mp = out_dir / "work-wrapped.md"
        mp.write_text(md_text, encoding="utf-8")
        written.append(mp)

    if emit in ("html", "all") and out_dir is not None:
        tpl = SKILL_DIR / "templates" / "wrapped.html"
        hp = out_dir / "work-wrapped.html"
        hp.write_text(render_html(stats, tpl if tpl.is_file() else None), encoding="utf-8")
        written.append(hp)

    if emit == "compact":
        print(render_compact(stats))
    elif emit == "markdown":
        print(md_text)
    elif emit == "json":
        print(json.dumps(stats.to_dict(), indent=2))
    elif emit == "html":
        # Still print compact summary; HTML is on disk
        print(render_compact(stats))
        if written:
            print(f"\nHTML: {written[-1].resolve()}")
    elif emit == "all":
        print(render_compact(stats))
        if written:
            print("\nWrote:")
            for w in written:
                print(f"  {w.resolve()}")

    if emit not in ("compact",) and written and emit != "all":
        # already handled
        pass
    elif emit == "markdown" and out_dir is None:
        pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
