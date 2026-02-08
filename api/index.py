"""
Vercel serverless handler: forwards all traffic to the FastAPI app.
Use with vercel.json rewrites: "/(.*)" -> "/api"
When the request is rewritten to /api, Vercel may pass path as /api or /api/...;
we strip the /api prefix so the FastAPI app sees / and /...
"""
import sys
from pathlib import Path

# api/index.py lives at <deploy_root>/api/index.py; forge package is at <deploy_root>/forge or <deploy_root>/zuup-forge/forge
_api_dir = Path(__file__).resolve().parent
_root = _api_dir.parent
_deploy_root = _root / "zuup-forge" if (_root / "zuup-forge" / "forge").exists() else _root
if str(_deploy_root) not in sys.path:
    sys.path.insert(0, str(_deploy_root))

from forge.ui.app import app as _raw_app


async def app(scope, receive, send):
    """ASGI app: strip /api prefix when present, then forward to FastAPI."""
    path = scope.get("path", "") or "/"
    if path.startswith("/api"):
        path = path[4:] or "/"
        scope = dict(scope)
        scope["path"] = path
    await _raw_app(scope, receive, send)


__all__ = ["app"]
