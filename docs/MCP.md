# Timeglass MCP for timeglass-last30days

## Endpoint

```
https://app.timeglass.ai/api/mcp
```

Override with `TIMEGASS_MCP_URL` if needed.

## Auth

Set one of:

- `TIMEGASS_MCP_TOKEN`
- `TIMEGASS_ACCESS_TOKEN`

Token must be issued for the **MCP / AI assistant** audience (Raycast OAuth with `mcp:read`, or the in-app AI connector flow).

Desktop app tokens used for screenshot upload are a **different audience** and will fail with `invalid_token` / 401. That is expected — not an engine bug.

Official connect guide: https://timeglass.ai/help/ai-assistant/connect-ai-assistant

## Tools

| Tool | Why we call it |
|---|---|
| `query_workspace_directory` | List workspaces/teams/users; extract `team_id` from `team_tree` |
| `set_team` | Bind session to a real team |
| `query_work_records` | Pull entities for the date window |
| `get_minute_screenshots` | Optional deep dives (not required for Wrapped) |
| `get_meeting_transcript` | Optional deep dives |

### `query_work_records` entities

- `projects`
- `project_daily_summary`
- `user_daily_summary`
- `activities`
- `activity_items`
- `minutes`
- `meetings`

## team_id vs workspace_id

Directory payloads often look like:

```json
{
  "workspaces": [
    {
      "workspace_id": "ws-…",
      "name": "Studio",
      "team_tree": [
        { "team_id": "team-…", "name": "Core", "children": [] }
      ]
    }
  ]
}
```

**Always** pass `team_id` to `set_team` / work-record queries.  
Passing `workspace_id` commonly yields `Unauthorized access to team`.

## Engine client

`skills/timeglass-last30days/scripts/lib/mcp_client.py` speaks JSON-RPC-style `initialize`, `tools/list`, `tools/call` over HTTP with optional `Mcp-Session-Id`.

If your host already injects Timeglass MCP tools into the agent, you can skip the Python client and feed a combined export via `--fixture`.

## Doctor

```bash
python3 skills/timeglass-last30days/scripts/last30work.py --doctor
```

Prints token presence (redacted), initialize result, tool names, and team candidates.
