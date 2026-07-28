# MCP reference (skill-local)

See also repo root [docs/MCP.md](../../../docs/MCP.md).

## Minimal live sequence

1. `initialize`
2. `query_workspace_directory` `{ "entity": "teams" }` or `workspaces`
3. Extract `team_id` from `team_tree`
4. `set_team` `{ "teamId": "<team_id>" }`
5. `query_work_records` for each entity with the 30-day window

## Env

| Var | Required | Purpose |
|---|---|---|
| `TIMEGASS_MCP_TOKEN` | for live | Bearer token (MCP audience) |
| `TIMEGASS_ACCESS_TOKEN` | alt | Same |
| `TIMEGASS_MCP_URL` | no | Default `https://app.timeglass.ai/api/mcp` |
| `TIMEGASS_USER_NAME` | no | Label for Wrapped header |
| `TIMEGASS_WORKSPACE_NAME` | no | Label for Wrapped header |

## Never

- Commit tokens
- Print full bearer strings
- Use desktop upload token and retry forever
- Pass `workspace_id` as `teamId`
