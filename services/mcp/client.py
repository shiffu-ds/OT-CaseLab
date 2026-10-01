"""Official SDK stdio/Streamable HTTP client with initialized protocol discovery."""

from __future__ import annotations

import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client


class ToolError(RuntimeError):
    pass


class ToolClient:
    def __init__(self, session, token: str, initialization: dict, tools: list[str]):
        self.session, self.token = session, token
        self.initialization, self.tools = initialization, tools

    async def call(self, name: str, **arguments) -> dict:
        if name not in self.tools:
            raise ToolError("Tool was not discovered by the initialized MCP client")
        result = await self.session.call_tool(name, {"scope_token": self.token, **arguments})
        if getattr(result, "is_error", getattr(result, "isError", False)):
            raise ToolError("MCP tool rejected the request; no successful result was substituted")
        structured = getattr(
            result, "structured_content", getattr(result, "structuredContent", None)
        )
        if structured is not None:
            # SDK wraps primitive returns but dictionary tools preserve their keys.
            return structured
        blocks = [b.text for b in result.content if getattr(b, "type", None) == "text"]
        try:
            return json.loads(blocks[0])
        except (ValueError, IndexError) as exc:
            raise ToolError("MCP tool returned invalid structured content") from exc


@asynccontextmanager
async def connect(token: str):
    from services.api.config import get_settings

    settings = get_settings()
    transport = settings.mcp_transport
    if transport == "http":
        import httpx2

        bearer = settings.mcp_http_bearer_token
        if len(bearer) < 32:
            raise ToolError("HTTP MCP mode requires a distinct internal bearer token")
        async with httpx2.AsyncClient(
            headers={"Authorization": "Bearer " + bearer}, timeout=httpx2.Timeout(20, read=60)
        ) as http_client:
            async with streamable_http_client(settings.mcp_url, http_client=http_client) as streams:
                async with ClientSession(*streams, read_timeout_seconds=30) as session:
                    init = await session.initialize()
                    listing = await session.list_tools()
                    yield ToolClient(
                        session,
                        token,
                        init.model_dump(mode="json"),
                        [t.name for t in listing.tools],
                    )
    elif transport == "stdio":
        root = str(Path(__file__).resolve().parents[2])
        env = {
            key: value
            for key, value in os.environ.items()
            if key
            in {
                "DATABASE_URL",
                "MCP_SERVICE_SECRET",
                "ASSET_STORAGE_PATH",
                "APP_SECRET",
                "PROVIDER_MODE",
                "CV_MODE",
                "NLP_MODE",
                "HF_HOME",
                "OMP_NUM_THREADS",
            }
        }
        if not env.get("MCP_SERVICE_SECRET"):
            from services.api.config import get_settings

            env["MCP_SERVICE_SECRET"] = get_settings().mcp_service_secret
        env.update({"PYTHONPATH": root, "MCP_TRANSPORT": "stdio"})
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "services.mcp.server"], env=env, cwd=root
        )
        async with stdio_client(params) as streams:
            async with ClientSession(*streams, read_timeout_seconds=30) as session:
                init = await session.initialize()
                listing = await session.list_tools()
                yield ToolClient(
                    session, token, init.model_dump(mode="json"), [t.name for t in listing.tools]
                )
    else:
        raise ToolError("MCP_TRANSPORT must be stdio or http")
