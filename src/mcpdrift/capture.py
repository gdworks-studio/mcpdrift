from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
import os

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.shared.exceptions import McpError

from .config import ServerConfig
from .snapshot import SNAPSHOT_SCHEMA_VERSION, sort_json

METHOD_NOT_FOUND = -32601


async def capture_contract(config: ServerConfig) -> dict[str, Any]:
    params = StdioServerParameters(
        command=config.command,
        args=config.args,
        env=config.env,
        cwd=config.cwd,
    )

    with open(os.devnull, "w") as errlog:
        async with stdio_client(params, errlog=errlog) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                initialize_result = await session.initialize()
                tools = await _list_all(session.list_tools, "tools")
                resources = await _list_all_optional(session.list_resources, "resources")
                prompts = await _list_all_optional(session.list_prompts, "prompts")

    return sort_json(
        {
            "snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
            "mcp_protocol_version": str(initialize_result.protocolVersion),
            "tools": sorted((_tool(tool) for tool in tools), key=lambda item: item["name"]),
            "resources": sorted((_resource(resource) for resource in resources), key=lambda item: (item["uri"], item["name"])),
            "prompts": sorted((_prompt(prompt) for prompt in prompts), key=lambda item: item["name"]),
        }
    )


async def _list_all(
    method: Callable[..., Awaitable[Any]],
    result_field: str,
) -> list[Any]:
    items: list[Any] = []
    cursor: str | None = None
    while True:
        result = await method(cursor=cursor)
        items.extend(getattr(result, result_field))
        cursor = getattr(result, "nextCursor", None)
        if not cursor:
            return items


async def _list_all_optional(method: Callable[..., Awaitable[Any]], result_field: str) -> list[Any]:
    try:
        return await _list_all(method, result_field)
    except McpError as exc:
        if exc.error.code == METHOD_NOT_FOUND:
            return []
        raise


def _model(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=True, exclude_none=True)
    return dict(value)


def _tool(tool: Any) -> dict[str, Any]:
    data = _model(tool)
    result = {
        "name": data["name"],
        "description": data.get("description"),
        "inputSchema": data.get("inputSchema", {"type": "object"}),
    }
    if "outputSchema" in data:
        result["outputSchema"] = data["outputSchema"]
    return sort_json(result)


def _resource(resource: Any) -> dict[str, Any]:
    data = _model(resource)
    return sort_json(
        {
            "uri": str(data["uri"]),
            "name": data.get("name"),
            "description": data.get("description"),
        }
    )


def _prompt(prompt: Any) -> dict[str, Any]:
    data = _model(prompt)
    return sort_json(
        {
            "name": data["name"],
            "description": data.get("description"),
            "arguments": data.get("arguments", []),
        }
    )
