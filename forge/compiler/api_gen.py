"""
API Route Generator

Compiles PlatformSpec API configuration into FastAPI route handlers,
middleware setup, and OpenAPI documentation.
"""

from __future__ import annotations

from forge.compiler.spec_schema import APIRoute, Entity, PlatformSpec


def _route_function_name(route: APIRoute, method: str) -> str:
    """Generate a Python function name from route path + method."""
    path_parts = route.path.strip("/").replace("{", "").replace("}", "").split("/")
    return f"{method.lower()}_{'_'.join(path_parts)}"


def _find_entity_for_route(route: APIRoute, entities: list[Entity]) -> Entity | None:
    """Infer which entity a route operates on."""
    schema_name = route.response_schema or route.request_schema
    if schema_name:
        for entity in entities:
            if entity.name == schema_name:
                return entity
    # Fallback: match by first path segment
    first_segment = route.path.strip("/").split("/")[0]
    for entity in entities:
        if entity.name.lower() == first_segment.lower():
            return entity
        if entity.name.lower() + "s" == first_segment.lower():
            return entity
    return None


def generate_fastapi_routes(spec: PlatformSpec) -> str:
    """Generate FastAPI route handlers from platform spec."""
    lines = [
        '"""',
        f"Auto-generated API routes for {spec.platform.display_name}",
        f"Platform: {spec.platform.name} v{spec.platform.version}",
        "",
        "DO NOT EDIT DIRECTLY — regenerate with `forge generate`.",
        "Add domain logic in the services/ directory.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "from typing import Any",
        "from uuid import UUID",
        "",
        "from fastapi import APIRouter, Depends, HTTPException, Query, Request",
        "from pydantic import BaseModel",
        "",
        "from forge.substrate.zuup_auth.middleware import require_auth, ZuupPrincipal",
        "from forge.substrate.zuup_audit.middleware import audit_action",
        "from forge.substrate.zuup_observe.tracing import traced",
        "",
        f"from platforms.{spec.platform.name}.models import *",
        f"from platforms.{spec.platform.name}.services import *",
        "",
        "",
        f'router = APIRouter(prefix="/{spec.api.base_path.strip("/")}/{spec.api.version}")',
        "",
        "",
    ]

    for route in spec.api.routes:
        entity = _find_entity_for_route(route, spec.entities)
        entity_name = entity.name if entity else "Resource"

        for method in route.methods:
            func_name = _route_function_name(route, method)

            # Determine auth dependency
            auth_dep = ""
            if route.auth == "required":
                auth_dep = ", principal: ZuupPrincipal = Depends(require_auth)"
            elif route.auth == "optional":
                auth_dep = ", principal: ZuupPrincipal | None = Depends(require_auth)"

            # Detect path parameters
            path_params = []
            path = route.path
            while "{" in path:
                start = path.index("{")
                end = path.index("}")
                param = path[start + 1:end]
                path_params.append(param)
                path = path[end + 1:]

            param_str = ", ".join(f"{p}: str" for p in path_params)
            if param_str:
                param_str = ", " + param_str

            if method == "GET" and not path_params:
                # List endpoint
                lines.extend([
                    f'@router.get("{route.path}")',
                    "@traced",
                    f"@audit_action(platform=\"{spec.platform.name}\", action=\"list_{entity_name.lower()}\")",
                    f"async def {func_name}(",
                    f"    request: Request{auth_dep},",
                    "    offset: int = Query(0, ge=0),",
                    "    limit: int = Query(50, ge=1, le=200),",
                    ") -> dict[str, Any]:",
                    f'    """List {entity_name} resources."""',
                    f"    # TODO: Implement in services/{entity_name.lower()}_service.py",
                    "    return {",
                    '        "items": [],',
                    '        "total": 0,',
                    '        "offset": offset,',
                    '        "limit": limit,',
                    "    }",
                    "",
                    "",
                ])

            elif method == "GET" and path_params:
                # Get by ID endpoint
                lines.extend([
                    f'@router.get("{route.path}")',
                    "@traced",
                    f"@audit_action(platform=\"{spec.platform.name}\", action=\"get_{entity_name.lower()}\")",
                    f"async def {func_name}(",
                    f"    request: Request{param_str}{auth_dep},",
                    ") -> dict[str, Any]:",
                    f'    """Get {entity_name} by ID."""',
                    "    # TODO: Implement lookup",
                    "    raise HTTPException(404, detail=\"Not found\")",
                    "",
                    "",
                ])

            elif method == "POST":
                # Create endpoint
                lines.extend([
                    f'@router.post("{route.path}", status_code=201)',
                    "@traced",
                    f"@audit_action(platform=\"{spec.platform.name}\", action=\"create_{entity_name.lower()}\")",
                    f"async def {func_name}(",
                    "    request: Request,",
                    f"    body: {entity_name}Create{auth_dep},",
                    ") -> dict[str, Any]:",
                    f'    """Create {entity_name}."""',
                    "    # TODO: Implement creation",
                    "    return {\"id\": \"placeholder\", \"status\": \"created\"}",
                    "",
                    "",
                ])

            elif method in ("PUT", "PATCH"):
                # Update endpoint
                lines.extend([
                    f'@router.{method.lower()}("{route.path}")',
                    "@traced",
                    f"@audit_action(platform=\"{spec.platform.name}\", action=\"update_{entity_name.lower()}\")",
                    f"async def {func_name}(",
                    f"    request: Request{param_str},",
                    f"    body: {entity_name}Update{auth_dep},",
                    ") -> dict[str, Any]:",
                    f'    """Update {entity_name}."""',
                    "    # TODO: Implement update",
                    "    return {\"status\": \"updated\"}",
                    "",
                    "",
                ])

            elif method == "DELETE":
                # Delete endpoint (soft by default)
                lines.extend([
                    f'@router.delete("{route.path}", status_code=204)',
                    "@traced",
                    f"@audit_action(platform=\"{spec.platform.name}\", action=\"delete_{entity_name.lower()}\")",
                    f"async def {func_name}(",
                    f"    request: Request{param_str}{auth_dep},",
                    ") -> None:",
                    f'    """Delete {entity_name} (soft delete)."""',
                    "    # TODO: Implement soft delete",
                    "    pass",
                    "",
                    "",
                ])

    return "\n".join(lines)


def generate_fastapi_app(spec: PlatformSpec) -> str:
    """Generate the main FastAPI application file."""
    return f'''"""
{spec.platform.display_name} — FastAPI Application
Platform: {spec.platform.name} v{spec.platform.version}
Domain: {spec.platform.domain}

Auto-generated by Zuup Forge. Domain logic goes in services/.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from forge.substrate.zuup_audit.middleware import AuditMiddleware
from forge.substrate.zuup_observe.tracing import setup_tracing
from forge.substrate.zuup_observe.health import health_router
from forge.substrate.zuup_gateway.rate_limit import RateLimitMiddleware
from forge.substrate.zuup_gateway.versioning import VersionMiddleware

from platforms.{spec.platform.name}.routes import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup and shutdown."""
    # Startup
    setup_tracing(service_name="{spec.platform.name}")
    # TODO: Initialize database connections, caches, model loading
    yield
    # Shutdown
    # TODO: Clean up connections


app = FastAPI(
    title="{spec.platform.display_name}",
    description="{spec.platform.description}",
    version="{spec.platform.version}",
    lifespan=lifespan,
    docs_url="/docs" if {spec.api.docs_enabled} else None,
    redoc_url="/redoc" if {spec.api.docs_enabled} else None,
)

# Middleware (order matters: outermost first)
app.add_middleware(
    CORSMiddleware,
    allow_origins={spec.api.cors_origins},
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware, rate="{spec.api.global_rate_limit}")
app.add_middleware(AuditMiddleware, platform="{spec.platform.name}")
app.add_middleware(VersionMiddleware, current_version="{spec.api.version}")

# Routes
app.include_router(api_router)
app.include_router(health_router)
'''
