"""Short-lived HMAC scopes; the HTTP bearer key is a distinct transport credential."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time


class ScopeError(ValueError):
    pass


def _secret() -> bytes:
    secret = os.environ.get("MCP_SERVICE_SECRET", "")
    if not secret:
        from services.api.config import get_settings

        secret = get_settings().mcp_service_secret
    if len(secret) < 32:
        raise ScopeError("MCP_SERVICE_SECRET must contain at least 32 characters")
    return secret.encode()


def issue_token(scope: dict) -> str:
    claims = dict(scope)
    claims.setdefault("exp", int(time.time()) + 120)
    claims.setdefault("iat", int(time.time()))
    claims.setdefault("aud", "otcaselab-internal-mcp")
    payload = base64.urlsafe_b64encode(
        json.dumps(claims, sort_keys=True, separators=(",", ":")).encode()
    ).rstrip(b"=")
    signature = hmac.new(_secret(), payload, hashlib.sha256).hexdigest()
    return payload.decode() + "." + signature


def verify_token(token: str, permission: str) -> dict:
    if not isinstance(token, str) or len(token) > 4000:
        raise ScopeError("Invalid service scope")
    try:
        payload, signature = token.split(".", 1)
        expected = hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ScopeError("Invalid service signature")
        scope = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if not isinstance(scope, dict) or scope.get("aud") != "otcaselab-internal-mcp":
            raise ScopeError("Invalid service token audience")
        now = int(time.time())
        if (
            not isinstance(scope.get("exp"), int)
            or not isinstance(scope.get("iat"), int)
            or scope["exp"] <= now
            or scope["exp"] > now + 300
            or scope["iat"] > now + 5
            or scope["exp"] - scope["iat"] > 300
        ):
            raise ScopeError("Expired or overlong service scope")
        for field in ("user_id", "attempt_id", "cohort_id"):
            if not isinstance(scope.get(field), str) or not scope[field] or len(scope[field]) > 128:
                raise ScopeError("Invalid service identity")
        permissions = scope.get("permissions")
        if not isinstance(permissions, list) or any(
            p not in {"read", "analyze", "write"} for p in permissions
        ):
            raise ScopeError("Malformed service permissions")
        if permission not in permissions:
            raise ScopeError("Missing service permission")
        return scope
    except ScopeError:
        raise
    except (ValueError, TypeError, KeyError) as exc:
        raise ScopeError("Malformed service scope") from exc
