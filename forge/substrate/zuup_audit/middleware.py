"""
Audit Middleware

Automatically logs API operations to the audit chain.
Provides both middleware (global) and decorator (per-route) approaches.
"""

from __future__ import annotations

import functools
import time
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from forge.substrate.zuup_audit import AuditEntry, SQLiteAuditStore, hash_payload

_audit_store: SQLiteAuditStore | None = None


def init_audit_store(db_path: str = "audit.db") -> SQLiteAuditStore:
    global _audit_store
    _audit_store = SQLiteAuditStore(db_path)
    return _audit_store


def get_audit_store() -> SQLiteAuditStore:
    if _audit_store is None:
        return init_audit_store()
    return _audit_store


def log_audit_event(
    *,
    platform: str,
    action: str,
    principal_id: str,
    entity_type: str,
    entity_id: str,
    payload: dict,
) -> str:
    """Append a write-operation event to the audit hash chain. Used by generated routes."""
    store = get_audit_store()
    entry = AuditEntry(
        platform=platform,
        action=action,
        principal_id=principal_id,
        entity_type=entity_type,
        entity_id=entity_id,
        payload_hash=hash_payload(payload),
    )
    return store.append(entry)


class AuditMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, platform: str = "unknown"):
        super().__init__(app)
        self.platform = platform

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start) * 1000

        principal = getattr(request.state, "principal", None)
        principal_id = principal.id if principal else "anonymous"

        store = get_audit_store()
        store.append(AuditEntry(
            platform=self.platform,
            action=f"{request.method} {request.url.path}",
            principal_id=principal_id,
            entity_type="http_request",
            entity_id=str(request.url),
            payload_hash=hash_payload({
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
            }),
            metadata={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "client_ip": request.client.host if request.client else "unknown",
            },
        ))
        return response


def audit_action(platform: str, action: str):
    """Decorator for auditing specific route actions."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request") or (args[0] if args else None)
            principal = getattr(request.state, "principal", None) if request else None
            principal_id = principal.id if principal else "anonymous"

            result = await func(*args, **kwargs)

            store = get_audit_store()
            store.append(AuditEntry(
                platform=platform,
                action=action,
                principal_id=principal_id,
                entity_type=action.split("_")[-1] if "_" in action else "unknown",
                entity_id=str(kwargs.get("id", "batch")),
                payload_hash=hash_payload(result if isinstance(result, dict) else {"result": str(result)}),
            ))
            return result
        return wrapper
    return decorator
