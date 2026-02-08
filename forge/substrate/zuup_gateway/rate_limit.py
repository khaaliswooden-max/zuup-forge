"""Zuup Gateway: Rate limiting middleware."""
from __future__ import annotations
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, rate: str = "1000/min"):
        super().__init__(app)
        parts = rate.split("/")
        self.max_requests = int(parts[0])
        self.window_seconds = {"sec": 1, "min": 60, "hour": 3600}.get(parts[1], 60)
        self._buckets: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next) -> Response:
        key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        bucket = self._buckets.setdefault(key, [])
        bucket[:] = [t for t in bucket if now - t < self.window_seconds]
        if len(bucket) >= self.max_requests:
            return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)
        bucket.append(now)
        return await call_next(request)
