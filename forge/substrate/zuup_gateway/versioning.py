"""Zuup Gateway: API versioning middleware."""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class VersionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, current_version: str = "v1"):
        super().__init__(app)
        self.current_version = current_version

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-API-Version"] = self.current_version
        return response
