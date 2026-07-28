---
name: timeglass-last30days
version: "1.0.0"
description: "Use when reviewing your last 30 days of work with Timeglass. Builds a Spotify-Wrapped-style Work Wrapped from Timeglass MCP — projects, meetings, billable mix, budget risk. No scraping."
argument-hint: "last30work | work wrapped | my last 30 days | monthly review"
homepage: https://github.com/rdsciv/timeglass-last30days
repository: https://github.com/rdsciv/timeglass-last30days
license: MIT
user-invocable: true
metadata:
  openclaw:
    emoji: "⏳"
  requires:
    env: []
    optionalEnv:
      - TIMEGASS_MCP_TOKEN
      - TIMEGASS_ACCESS_TOKEN
      - TIMEGASS_MCP_URL
      - TIMEGASS_USER_NAME
      - TIMEGASS_WORKSPACE_NAME
    bins:
      - python3
  tags:
    - timeglass
    - timesheet
    - productivity
    - mcp
    - work-wrapped
    - monthly-review
    - last30days
    - ai-skill
---

# timeglass-last30days — Work Wrapped

You are running the **Timeglass last-30-days** skill. This is **not** web research and **not** scraping. It reviews **the user's own work record** for the last ~30 days via the official **Timeglass MCP**, then synthesizes a **Spotify-Wrapped-style** monthly review ("Work Wrapped").

Mirror spirit of `/last30days` (viral topic research), but inverted:

| last30days-skill | timeglass-last30days |
|---|---|
| What the internet said | What **you** actually did |
| Reddit / X / YouTube scrapes | Timeglass MCP only |
| Topic brief | Work Wrapped |

## SKILL_DIR

Resolve `SKILL_DIR` as the directory containing **this** `SKILL.md`. All engine calls use:

```bash
python3 "$SKILL_DIR/scripts/last30work.py" …
```

Do **not** invent alternate engine paths. Do **not** scrape calendars, email, or browsers.

## STEP 0 — Badge (mandatory first line of user-facing output)

Every final response starts with exactly:

```
⏳ timeglass-last30days v{VERSION} · {START} → {END}
```

Prefer **passing through** the engine's `--emit=compact` or markdown first line (it already includes the badge). Then synthesize. Never invent vanity titles like "Your incredible month" as H1 replacements for the badge.

## STEP 1 — Preflight

```bash
python3 "$SKILL_DIR/scripts/last30work.py" --preflight
```

If the user asks why MCP fails, or first-time setup:

```bash
python3 "$SKILL_DIR/scripts/last30work.py" --doctor
```

## STEP 2 — Acquire data (pick one path)

### Path A — Live MCP (preferred when connected)

Requires `TIMEGASS_MCP_TOKEN` (or `TIMEGASS_ACCESS_TOKEN`) with **MCP audience** from:

1. Timeglass **AI assistant connector** (Claude / ChatGPT) — [connect docs](https://timeglass.ai/help/ai-assistant/connect-ai-assistant)
2. Raycast Timeglass extension OAuth (`mcp:read`)
3. Any host already connected to `https://app.timeglass.ai/api/mcp`

**Critical auth law:** Desktop `config.json` upload tokens are the **wrong audience**. They will `invalid_token` / 401 against product MCP. Do not loop on them. Tell the user to connect the AI assistant or Raycast Sign In.

```bash
python3 "$SKILL_DIR/scripts/last30work.py" --days 30 --emit all --out "$HOME/Documents/TimeglassWrapped"
```

Optional: `--team-id <uuid>` (must be **team_id** from `team_tree`, never `workspace_id`).

### Path B — Demo / fixture (always works, for README & first run)

```bash
python3 "$SKILL_DIR/scripts/last30work.py" --demo --emit all --out ./out
```

### Path C — Host already has Timeglass MCP tools

If the agent host already exposes Timeglass MCP tools directly (`query_work_records`, `query_workspace_directory`, `set_team`, …), you may call them yourself **instead of** the Python MCP client:

1. `query_workspace_directory` entity `teams` or `workspaces` → extract `team_id` from `team_tree` (**never** use `workspace_id` as team).
2. `set_team` with that `team_id`.
3. `query_work_records` for the window with entities:
   - `projects`
   - `project_daily_summary`
   - `user_daily_summary`
   - `activities`
   - `meetings`
4. Save the combined JSON and run:

```bash
python3 "$SKILL_DIR/scripts/last30work.py" --fixture /path/to/combined.json --emit all --out "$HOME/Documents/TimeglassWrapped"
```

Or synthesize from the tool results using the **Output contract** below (same sections). Prefer the engine when available so numbers stay consistent.

## STEP 3 — Output contract (Work Wrapped)

After the badge line, produce:

1. **One-liner** — total hours, active days, lead project/client, meeting %.
2. **Month in numbers** — table: total, active days, avg/active day, billable %, meeting %, deep work.
3. **Identity cards** — 2–4 playful-but-true labels grounded in the numbers (e.g. "Meeting Main Character", "Billable Beast"). No empty flattery.
4. **Top projects** — hours + share % + budget used when present. Flag NEAR (≥85%) / OVER (≥100%).
5. **Top clients** — rollup.
6. **Top activities** — what the work actually was.
7. **Weekday rhythm** — which days carried the month.
8. **Shoutouts** — busiest day, home app, budget watch.
9. **What to do with this** — exactly 3–4 concrete next actions (protect pattern / name the drag / budget honesty / carry commitments).
10. **Invite** — offer HTML wrapped path if generated, or follow-ups: "zoom into project X", "draft status update for client Y", "weekly review for this week only".

### Laws

- **LAW 1 — Ground every claim.** No hours, rankings, or budget claims that are not in engine output or MCP tool results.
- **LAW 2 — No scraping.** Do not use browser/web scrape as a substitute for Timeglass.
- **LAW 3 — Trust labels.** If data is fixture/demo, say so. If local-only capture was used upstream, label as signal not approved timesheet.
- **LAW 4 — No trailing Sources: block.** Footer line is enough: Timeglass MCP.
- **LAW 5 — Privacy.** Never print access tokens, refresh tokens, or full auth headers. Redact bearer strings if they appear in errors.
- **LAW 6 — team_id ≠ workspace_id.** Wrong id → "Unauthorized access to team". Fix by re-reading `team_tree`.

## STEP 4 — HTML artifact

When `--emit html` or `all` wrote `work-wrapped.html`, tell the user the absolute path and offer to open it. The HTML is self-contained (no build step).

## Quick commands

```bash
# Demo (no account)
python3 "$SKILL_DIR/scripts/last30work.py" --demo --emit compact

# Full demo artifacts
python3 "$SKILL_DIR/scripts/last30work.py" --demo --emit all --out ./out

# Live
export TIMEGASS_MCP_TOKEN='…'   # never commit
python3 "$SKILL_DIR/scripts/last30work.py" --days 30 --emit all --out ~/Documents/TimeglassWrapped

# Health
python3 "$SKILL_DIR/scripts/last30work.py" --doctor
```

## When NOT to use

- User wants public web/research on a topic → use last30days-skill or web research.
- User wants morning brief from local desktop logs only → ops reporter path, not this skill's MCP core.
- User asks to exfiltrate someone else's timesheet beyond their role → refuse; MCP already enforces permissions.

## Completion criteria

You are done when:

- [ ] Badge line emitted
- [ ] Engine or MCP tools actually ran (or demo explicitly chosen)
- [ ] Numbers match engine/MCP (not invented)
- [ ] Identity cards + top projects + next actions present
- [ ] HTML path shared if generated
- [ ] No tokens printed
