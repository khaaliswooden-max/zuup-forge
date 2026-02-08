"""Zuup Gateway — Rate limiting, versioning, CORS."""
from __future__ import annotations
import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, rate: str = "1000/min"):
        super().__init__(app)
        parts = rate.split("/")
        self.max_tokens = int(parts[0])
        self.window = {"sec": 1, "min": 60, "hour": 3600}.get(parts[1], 60)
        self._buckets: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path.startswith("/health"):
            return await call_next(request)
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        self._buckets[ip] = [t for t in self._buckets[ip] if t > now - self.window]
        if len(self._buckets[ip]) >= self.max_tokens:
            return JSONResponse({"error": "Rate limit exceeded"}, 429, headers={"Retry-After": str(self.window)})
        self._buckets[ip].append(now)
        resp = await call_next(request)
        resp.headers["X-RateLimit-Remaining"] = str(self.max_tokens - len(self._buckets[ip]))
        return resp

class VersionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, current_version: str = "v1"):
        super().__init__(app)
        self.version = current_version

    async def dispatch(self, request: Request, call_next) -> Response:
        resp = await call_next(request)
        resp.headers["X-API-Version"] = self.version
        resp.headers["X-Powered-By"] = "Zuup Forge"
        return resp
