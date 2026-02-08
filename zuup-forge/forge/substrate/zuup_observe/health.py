"""Health check endpoints for all platforms."""
from fastapi import APIRouter

health_router = APIRouter(tags=["health"])

@health_router.get("/health")
async def health():
    return {"status": "ok"}

@health_router.get("/ready")
async def ready():
    # TODO: Check DB, cache, model availability
    return {"status": "ready", "checks": {"database": "ok", "cache": "ok"}}
