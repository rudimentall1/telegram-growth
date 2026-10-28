#!/usr/bin/env python3
"""Submit the public CryptoPing channel to TGFind's open Telegram directory.

This is a free, public discovery listing. It does not buy ads or post into
third-party chats. The script is idempotent: it checks before submitting and
re-checks after submission.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

MCP_URL = os.getenv("TG_DIRECTORY_MCP_URL", "https://tgfind.net/api/mcp")
HANDLE = os.getenv("DISTRIBUTION_TELEGRAM_HANDLE", "cryptoping_ru")
PROTOCOL_VERSION = "2025-03-26"


class MCPError(RuntimeError):
    pass


class MCPClient:
    def __init__(self, url: str) -> None:
        self.url = url
        self.session_id: str | None = None
        self.next_id = 1

    def _request(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "User-Agent": "telegram-growth-directory-distributor/1.0",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
            headers["MCP-Protocol-Version"] = PROTOCOL_VERSION

        request = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                self.session_id = (
                    response.headers.get("Mcp-Session-Id")
                    or response.headers.get("mcp-session-id")
                    or self.session_id
                )
                body = response.read().decode("utf-8", "replace")
                content_type = response.headers.get("Content-Type", "")
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", "replace")[:1000]
            raise MCPError(f"HTTP {exc.code}: {details}") from exc
        except urllib.error.URLError as exc:
            raise MCPError(f"Network error: {exc.reason}") from exc

        if not body.strip():
            return None
        if "text/event-stream" in content_type or body.lstrip().startswith("event:"):
            messages = []
            data_lines: list[str] = []
            for line in body.splitlines() + [""]:
                if line.startswith("data:"):
                    data_lines.append(line[5:].strip())
                elif not line.strip() and data_lines:
                    data = "\n".join(data_lines)
                    if data and data != "[DONE]":
                        try:
                            messages.append(json.loads(data))
                        except json.JSONDecodeError:
                            pass
                    data_lines = []
            for message in reversed(messages):
                if isinstance(message, dict) and (
                    "result" in message or "error" in message
                ):
                    return message
            raise MCPError("MCP returned an event stream without a JSON-RPC result")

        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise MCPError(f"Unexpected response: {body[:500]}") from exc
        if not isinstance(data, dict):
            raise MCPError("MCP response was not a JSON object")
        return data

    def initialize(self) -> None:
        result = self._request(
            {
                "jsonrpc": "2.0",
                "id": self.next_id,
                "method": "initialize",
                "params": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {
                        "name": "telegram-growth-directory-distributor",
                        "version": "1.0.0",
                    },
                },
            }
        )
        self.next_id += 1
        if not result:
            raise MCPError("MCP initialization returned an empty response")
        if "error" in result:
            raise MCPError(f"MCP initialization failed: {result['error']}")
        self._request({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        response = self._request(
            {
                "jsonrpc": "2.0",
                "id": self.next_id,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }
        )
        self.next_id += 1
        if not response:
            raise MCPError(f"{name}: empty response")
        if "error" in response:
            raise MCPError(f"{name}: {response['error']}")
        result = response.get("result")
        if not isinstance(result, dict):
            raise MCPError(f"{name}: missing tool result")
        return result


def is_tool_error(result: dict[str, Any]) -> bool:
    return bool(result.get("isError"))


def result_text(result: dict[str, Any]) -> str:
    parts = []
    for item in result.get("content", []):
        if isinstance(item, dict) and item.get("text"):
            parts.append(str(item["text"]))
    return "\n".join(parts)


def main() -> int:
    client = MCPClient(MCP_URL)
    try:
        client.initialize()
        current = client.call_tool("get_resource", {"handle": HANDLE})
        if not is_tool_error(current):
            print(f"DISCOVERABLE: https://t.me/{HANDLE} is already in TGFind.")
            return 0

        submitted = client.call_tool(
            "submit_listing", {"handle": HANDLE, "type": "channel"}
        )
        submit_text = result_text(submitted)
        print(f"Directory submission response: {submit_text or '(no text returned)'}")

        # Verify via the directory's own lookup rather than trusting a submit
        # acknowledgement alone.
        verified = client.call_tool("get_resource", {"handle": HANDLE})
        if not is_tool_error(verified):
            print(f"VERIFIED: https://t.me/{HANDLE} is discoverable in TGFind.")
            return 0

        print(
            "NOT YET VERIFIED: the listing was not returned by immediate lookup. "
            "The scheduled retry will check again.",
            file=sys.stderr,
        )
        return 1
    except MCPError as exc:
        print(f"Distribution failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
