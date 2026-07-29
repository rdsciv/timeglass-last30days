"""Minimal Timeglass MCP client (streamable HTTP / JSON-RPC style).

Endpoint (product): https://app.timeglass.ai/api/mcp

Auth: Bearer token with MCP audience (Raycast OAuth / AI connector).
Desktop upload tokens are the wrong audience and will 401 — expected.

This client is intentionally small. It does not scrape. It only calls the
official MCP tools your Timeglass role is allowed to see.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


DEFAULT_MCP_URL = "https://app.timeglass.ai/api/mcp"

TOOL = {
    "work_records": "query_work_records",
    "directory": "query_workspace_directory",
    "set_team": "set_team",  # legacy; product MCP now uses set_workspace
    "set_workspace": "set_workspace",
    "screenshots": "get_minute_screenshots",
    "transcript": "get_meeting_transcript",
}

WORK_ENTITIES = (
    "projects",
    "project_daily_summary",
    "user_daily_summary",
    "activities",
    "activity_items",
    "minutes",
    "meetings",
)


@dataclass
class McpConfig:
    url: str
    token: str
    timeout: float = 60.0

    @classmethod
    def from_env(cls) -> "McpConfig | None":
        token = (
            os.environ.get("TIMEGASS_MCP_TOKEN")
            or os.environ.get("TIMEGASS_ACCESS_TOKEN")
            or os.environ.get("TIMEGASS_TOKEN")
            or ""
        ).strip()
        if not token:
            return None
        url = (
            os.environ.get("TIMEGASS_MCP_URL")
            or os.environ.get("TIMEGASS_MCP_ENDPOINT")
            or DEFAULT_MCP_URL
        ).strip()
        return cls(url=url, token=token)


class McpError(RuntimeError):
    pass


class TimeglassMcpClient:
    """Best-effort JSON-RPC client for Timeglass product MCP."""

    def __init__(self, config: McpConfig):
        self.config = config
        self._id = 0
        self._session_id: str | None = None

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    def _headers(self) -> dict[str, str]:
        h = {
            "Authorization": f"Bearer {self.config.token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id:
            h["Mcp-Session-Id"] = self._session_id
        return h

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.config.url,
            data=data,
            headers=self._headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                sid = resp.headers.get("Mcp-Session-Id") or resp.headers.get("mcp-session-id")
                if sid:
                    self._session_id = sid
                body = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:800]
            raise McpError(f"HTTP {e.code}: {detail}") from e
        except urllib.error.URLError as e:
            raise McpError(f"Network error: {e.reason}") from e

        # Handle SSE-ish multi-line responses: take last data: JSON object
        text = body.strip()
        if "data:" in text and text.lstrip().startswith("event:") or "\ndata:" in text:
            objs: list[dict[str, Any]] = []
            for line in text.splitlines():
                if line.startswith("data:"):
                    chunk = line[5:].strip()
                    if not chunk or chunk == "[DONE]":
                        continue
                    try:
                        objs.append(json.loads(chunk))
                    except json.JSONDecodeError:
                        continue
            if not objs:
                raise McpError(f"Could not parse SSE MCP response: {text[:400]}")
            return objs[-1]

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise McpError(f"Invalid JSON from MCP: {text[:400]}") from e

    def initialize(self) -> dict[str, Any]:
        resp = self._post(
            {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "timeglass-last30days", "version": "1.0.0"},
                },
            }
        )
        # notifications/initialized (best effort)
        try:
            self._post(
                {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                    "params": {},
                }
            )
        except McpError:
            pass
        return resp

    def list_tools(self) -> list[dict[str, Any]]:
        resp = self._post(
            {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/list",
                "params": {},
            }
        )
        result = resp.get("result") or {}
        tools = result.get("tools") or []
        if not isinstance(tools, list):
            return []
        return tools

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> str:
        resp = self._post(
            {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments or {}},
            }
        )
        if "error" in resp and resp["error"]:
            err = resp["error"]
            raise McpError(f"Tool {name} error: {err}")
        result = resp.get("result") or {}
        # MCP content blocks
        content = result.get("content")
        if isinstance(content, list):
            parts: list[str] = []
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text" and isinstance(block.get("text"), str):
                    parts.append(block["text"])
                elif "text" in block:
                    parts.append(str(block["text"]))
            if parts:
                return "\n".join(parts)
        if isinstance(result, (dict, list)) and content is None:
            return json.dumps(result)
        return json.dumps(result)

    def query_work_records(self, entity: str, **kwargs: Any) -> str:
        args: dict[str, Any] = {"entity": entity}
        args.update({k: v for k, v in kwargs.items() if v is not None})
        return self.call_tool(TOOL["work_records"], args)

    def query_directory(self, entity: str = "teams", query: str | None = None) -> str:
        args: dict[str, Any] = {"entity": entity}
        if query:
            args["query"] = query
        return self.call_tool(TOOL["directory"], args)

    def set_team(self, team_id: str) -> str:
        """Legacy helper — prefer set_workspace(workspace_id) on current product MCP."""
        # Prefer camelCase; some servers accept team_id
        try:
            return self.call_tool(TOOL["set_team"], {"teamId": team_id})
        except McpError:
            return self.call_tool(TOOL["set_team"], {"team_id": team_id})

    def set_workspace(self, workspace_id: str) -> str:
        """Activate workspace scope (current Timeglass product MCP tool)."""
        try:
            return self.call_tool(TOOL["set_workspace"], {"workspaceId": workspace_id})
        except McpError:
            return self.call_tool(TOOL["set_workspace"], {"workspace_id": workspace_id})
