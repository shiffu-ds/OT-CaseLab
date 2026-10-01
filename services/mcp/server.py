"""Real SDK tools; all identities originate in signed internal service scopes."""

from __future__ import annotations

import hmac
import os
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings

from .auth import verify_token

server = MCPServer("OTCaseLab internal educational tools")


def dispatch(tool: str, scope_token: str, arguments: dict, permission: str = "read") -> dict:
    try:
        scope = verify_token(scope_token, permission)
        from services.api.mcp_bridge import gateway

        # The bridge checks live database ownership, cohort, role, and attempt state.
        return gateway(tool, scope, arguments)
    except ValueError:
        # Expected access/schema rejections have no stack traces or learner text.
        raise ToolError(
            "Scoped tool request rejected: check identity, permissions, frozen input and educator approval."
        ) from None


@server.tool()
def get_case_context(scope_token: str) -> dict:
    """Return versioned case context for the authenticated attempt, server-side only."""
    return dispatch("get_case_context", scope_token, {})


@server.tool()
def search_approved_evidence(scope_token: str, query: str, k: int = 3) -> dict:
    """Retrieve only educator-approved passages scoped to this attempt's case/cohort."""
    if len(query) > 12000 or not 1 <= k <= 10:
        raise ValueError("Evidence query exceeds allowed bounds")
    return dispatch("search_approved_evidence", scope_token, {"query": query, "k": k})


@server.tool()
def extract_profile(scope_token: str, text: str) -> dict:
    """Extract unvalidated span-preserving lexical mentions; text is untrusted data."""
    if len(text) > 30000:
        raise ValueError("Profile exceeds allowed bounds")
    return dispatch("extract_profile", scope_token, {"text": text}, "analyze")


@server.tool()
def analyze_case_asset(scope_token: str, asset_id: str) -> dict:
    """Analyze only the attempt's assigned asset. Detector predictions are provisional."""
    if len(asset_id) > 128:
        raise ValueError("Invalid asset identifier")
    return dispatch("analyze_case_asset", scope_token, {"asset_id": asset_id}, "analyze")


@server.tool()
def get_learner_history(scope_token: str) -> dict:
    """Return only this scoped learner's previous eligible attempts."""
    return dispatch("get_learner_history", scope_token, {})


@server.tool()
def get_evaluation_rubric(scope_token: str) -> dict:
    """Fetch the versioned original rubric for internal formative evaluation."""
    return dispatch("get_evaluation_rubric", scope_token, {})


@server.tool()
def assess_rubric(scope_token: str) -> dict:
    """Evaluate the frozen database submission with traceable provisional coverage."""
    return dispatch("assess_rubric", scope_token, {}, "analyze")


@server.tool()
def save_feedback(scope_token: str, report: dict[str, Any], idempotency_key: str) -> dict:
    """Persist provisional feedback once. Retries use the same attempt-bound key."""
    if len(idempotency_key) > 128 or not idempotency_key:
        raise ValueError("Invalid idempotency key")
    return dispatch(
        "save_feedback",
        scope_token,
        {"report": report, "idempotency_key": idempotency_key},
        "write",
    )


@server.tool()
def recommend_next_case(scope_token: str) -> dict:
    """Recommend an eligible published/demo case using a transparent baseline rule."""
    return dispatch("recommend_next_case", scope_token, {})


class BearerGuard:
    """Reject unauthenticated HTTP transport before any MCP protocol message."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            from services.api.config import get_settings

            expected = get_settings().mcp_http_bearer_token
            headers = dict(scope.get("headers", []))
            value = headers.get(b"authorization", b"").decode()
            if len(expected) < 32 or not hmac.compare_digest(value, "Bearer " + expected):
                await send(
                    {
                        "type": "http.response.start",
                        "status": 401,
                        "headers": [(b"content-type", b"application/json")],
                    }
                )
                await send(
                    {
                        "type": "http.response.body",
                        "body": b'{"error":"unauthorized internal transport"}',
                    }
                )
                return
        await self.app(scope, receive, send)


def http_app():
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=os.environ.get("MCP_ALLOWED_HOSTS", "127.0.0.1:*,localhost:*,mcp:9000").split(
            ","
        ),
        allowed_origins=["http://127.0.0.1:*", "http://localhost:*", "http://mcp:9000"],
    )
    return BearerGuard(
        server.streamable_http_app(
            json_response=True, stateless_http=True, transport_security=security
        )
    )


def main():
    from services.api.config import get_settings

    if get_settings().mcp_transport == "http":
        import uvicorn

        uvicorn.run(http_app(), host="0.0.0.0", port=int(os.environ.get("MCP_PORT", "9000")))
    else:
        server.run(transport="stdio")


if __name__ == "__main__":
    main()
