"""
API Route Generator

Compiles PlatformSpec API configuration into FastAPI route handlers.
Generated code is STANDALONE: no forge imports, only stdlib + fastapi + pydantic + sqlite3.
"""

from __future__ import annotations

import json

from forge.compiler.schema_gen import _entity_table_name
from forge.compiler.spec_schema import (
    APIRoute,
    Entity,
    EntityField,
    FieldType,
    PlatformSpec,
)


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
    first_segment = route.path.strip("/").split("/")[0]
    for entity in entities:
        if entity.name.lower() == first_segment.lower():
            return entity
        if entity.name.lower() + "s" == first_segment.lower():
            return entity
    return None


def _field_serialize_for_db(field: EntityField, value: object) -> object:
    """Serialize a field value for SQLite (JSON for lists, ISO for datetime)."""
    if value is None:
        return None
    if field.type in (FieldType.STRING_ARRAY, FieldType.INT_ARRAY, FieldType.FLOAT_ARRAY):
        return json.dumps(value) if isinstance(value, (list, tuple)) else value
    if field.type in (FieldType.DATETIME, FieldType.DATE):
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return value
    return value


def _generate_list_handler(spec: PlatformSpec, entity: Entity, route: APIRoute) -> list[str]:
    """Generate GET list handler (no path params)."""
    table = _entity_table_name(entity)
    soft = " WHERE deleted_at IS NULL" if entity.soft_delete else ""
    return [
        f'@router.get("{route.path}")',
        f"async def {_route_function_name(route, 'GET')}(limit: int = 50, offset: int = 0):",
        f'    """List {entity.name} resources."""',
        "    conn = get_db()",
        "    rows = conn.execute(",
        f'        "SELECT * FROM {table}{soft} LIMIT ? OFFSET ?",',
        "        (limit, offset)",
        "    ).fetchall()",
        f'    total = conn.execute("SELECT COUNT(*) FROM {table}{soft}").fetchone()[0]',
        "    conn.close()",
        '    return {"items": [dict(r) for r in rows], "total": total}',
        "",
        "",
    ]


def _generate_stub_list_handler(route: APIRoute, method: str, path_params: list[str]) -> list[str]:
    """Generate stub for nested GET (e.g. /opportunities/{id}/matches)."""
    params = ", ".join(f"{p}: str" for p in path_params) + ", limit: int = 50, offset: int = 0" if path_params else "limit: int = 50, offset: int = 0"
    return [
        f'@router.get("{route.path}")',
        f"async def {_route_function_name(route, method)}({params}):",
        '    return {"items": [], "total": 0}',
        "",
        "",
    ]


def _generate_get_by_id_handler(spec: PlatformSpec, entity: Entity, route: APIRoute) -> list[str]:
    """Generate GET by id handler."""
    table = _entity_table_name(entity)
    soft = " AND deleted_at IS NULL" if entity.soft_delete else ""
    return [
        f'@router.get("{route.path}")',
        f"async def {_route_function_name(route, 'GET')}(id: str):",
        f'    """Get {entity.name} by ID."""',
        "    conn = get_db()",
        f'    row = conn.execute("SELECT * FROM {table} WHERE id = ?{soft}", (id,)).fetchone()',
        "    conn.close()",
        "    if row is None:",
        "        raise HTTPException(404, detail='Not found')",
        "    return dict(row)",
        "",
        "",
    ]


def _generate_create_handler(spec: PlatformSpec, entity: Entity, route: APIRoute) -> list[str]:
    """Generate POST create handler with audit logging."""
    platform_name = spec.platform.name
    table = _entity_table_name(entity)
    entity_upper = entity.name.upper()
    entity_lower = entity.name.lower()
    cols = ["id", "created_at", "updated_at"]
    if entity.soft_delete:
        cols.append("deleted_at")
    cols.extend([f.name for f in entity.fields])
    placeholders = ", ".join("?" for _ in cols)
    col_str = ", ".join(cols)
    lines = [
        f'@router.post("{route.path}", status_code=201)',
        f"async def {_route_function_name(route, 'POST')}(body: {entity.name}Create, principal: ZuupPrincipal = Depends(get_principal)):",
        f'    """Create {entity.name}."""',
        "    conn = get_db()",
        "    now = datetime.now(timezone.utc).isoformat()",
        "    row_id = str(__import__('uuid').uuid4())",
        "    data = body.model_dump()",
        "    values = [row_id, now, now]",
    ]
    if entity.soft_delete:
        lines.append("    values.append(None)")
    for f in entity.fields:
        lines.append(f"    values.append(_field_val(data.get('{f.name}'), {f.type.value!r}))")
    lines.extend([
        f'    conn.execute("INSERT INTO {table} ({col_str}) VALUES ({placeholders})", values)',
        "    conn.commit()",
        "    conn.close()",
        f'    log_audit_event(platform="{platform_name}", action="CREATE_{entity_upper}", principal_id=principal.id, entity_type="{entity_lower}", entity_id=row_id, payload=body.model_dump())',
        "    return {'id': row_id, 'created_at': now}",
        "",
        "",
    ])
    return lines


def _generate_update_handler(spec: PlatformSpec, entity: Entity, route: APIRoute) -> list[str]:
    """Generate PUT update handler (only set provided fields) with audit logging."""
    platform_name = spec.platform.name
    entity_upper = entity.name.upper()
    entity_lower = entity.name.lower()
    table = _entity_table_name(entity)
    lines = [
        f'@router.put("{route.path}")',
        f"async def {_route_function_name(route, 'PUT')}(id: str, body: {entity.name}Update, principal: ZuupPrincipal = Depends(get_principal)):",
        f'    """Update {entity.name}."""',
        "    conn = get_db()",
        "    data = body.model_dump(exclude_unset=True)",
        "    if not data:",
        "        conn.close()",
        "        raise HTTPException(400, detail='No fields to update')",
        "    now = datetime.now(timezone.utc).isoformat()",
        "    data['updated_at'] = now",
        "    set_str = ', '.join(f'{k} = ?' for k in data)",
        "    values = [_field_val(data[k]) for k in data]",
        "    values.append(id)",
        f'    conn.execute(f"UPDATE {table} SET {{set_str}} WHERE id = ?", values)',
        "    conn.commit()",
        "    conn.close()",
        f'    log_audit_event(platform="{platform_name}", action="UPDATE_{entity_upper}", principal_id=principal.id, entity_type="{entity_lower}", entity_id=id, payload=body.model_dump(exclude_unset=True))',
        "    return {'status': 'updated'}",
        "",
        "",
    ]
    return lines


def _generate_delete_handler(spec: PlatformSpec, entity: Entity, route: APIRoute) -> list[str]:
    """Generate DELETE (soft) handler with audit logging."""
    platform_name = spec.platform.name
    entity_upper = entity.name.upper()
    entity_lower = entity.name.lower()
    table = _entity_table_name(entity)
    if not entity.soft_delete:
        return [
            f'@router.delete("{route.path}", status_code=204)',
            f"async def {_route_function_name(route, 'DELETE')}(id: str, principal: ZuupPrincipal = Depends(get_principal)):",
            "    raise HTTPException(501, detail='Hard delete not implemented')",
            "",
            "",
        ]
    return [
        f'@router.delete("{route.path}", status_code=204)',
        f"async def {_route_function_name(route, 'DELETE')}(id: str, principal: ZuupPrincipal = Depends(get_principal)):",
        f'    """Soft delete {entity.name}."""',
        "    conn = get_db()",
        "    now = datetime.now(timezone.utc).isoformat()",
        f'    conn.execute("UPDATE {table} SET deleted_at = ? WHERE id = ?", (now, id))',
        "    conn.commit()",
        "    conn.close()",
        f'    log_audit_event(platform="{platform_name}", action="DELETE_{entity_upper}", principal_id=principal.id, entity_type="{entity_lower}", entity_id=id, payload={{}})',
        "",
        "",
    ]


def generate_fastapi_routes(spec: PlatformSpec) -> str:
    """Generate FastAPI route handlers with SQLite CRUD, audit chain, and optional auth."""
    platform_name = spec.platform.name
    db_path = f'"{platform_name}.db"'
    display_name = spec.platform.display_name.encode("ascii", "replace").decode("ascii")
    lines = [
        "# -*- coding: utf-8 -*-",
        '"""',
        f"Auto-generated API routes for {display_name}",
        f"Platform: {platform_name} v{spec.platform.version}",
        "Audit + optional auth from forge.substrate. Regenerate with `forge compile`.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "import json",
        "import sqlite3",
        "from datetime import datetime, timezone",
        "",
        "from fastapi import APIRouter, Depends, HTTPException",
        "",
        "from forge.substrate.zuup_audit import log_audit_event",
        "from forge.substrate.zuup_auth import ZuupPrincipal",
        "from forge.substrate.zuup_auth.middleware import get_principal",
        "",
        "from ..models import *",
        "",
        "router = APIRouter()",
        f"DB_PATH = {db_path}",
        "",
        "def get_db():",
        "    conn = sqlite3.connect(DB_PATH)",
        "    conn.row_factory = sqlite3.Row",
        "    return conn",
        "",
        "def _field_val(v, ft=None):",
        "    if v is None: return None",
        '    if ft and ft in ("string[]", "int[]", "float[]"): return json.dumps(v) if isinstance(v, (list, tuple)) else v',
        '    if ft and ft in ("datetime", "date"): return v.isoformat() if hasattr(v, "isoformat") else v',
        "    if isinstance(v, (list, tuple)): return json.dumps(v)",
        "    if hasattr(v, \"isoformat\"): return v.isoformat()",
        "    return v",
        "",
        "",
    ]

    for route in spec.api.routes:
        entity = _find_entity_for_route(route, spec.entities)
        path_params = []
        path = route.path
        while "{" in path:
            start = path.index("{")
            end = path.index("}")
            path_params.append(path[start + 1 : end])
            path = path[end + 1 :]

        if not entity:
            # e.g. /search
            func_name = _route_function_name(route, "POST" if "POST" in route.methods else "GET")
            lines.extend([
                f'@router.post("{route.path}")' if "POST" in route.methods else f'@router.get("{route.path}")',
                f"async def {func_name}():",
                '    return {"status": "not_implemented", "message": "Custom route"}',
                "",
                "",
            ])
            continue

        for method in route.methods:
            # Nested resource e.g. /opportunities/{id}/matches -> stub
            path_segments = route.path.strip("/").split("/")
            if method == "GET" and not path_params:
                lines.extend(_generate_list_handler(spec, entity, route))
            elif method == "GET" and path_params and len(path_segments) > 2:
                lines.extend(_generate_stub_list_handler(route, method, path_params))
            elif method == "GET" and path_params:
                lines.extend(_generate_get_by_id_handler(spec, entity, route))
            elif method == "POST":
                lines.extend(_generate_create_handler(spec, entity, route))
            elif method == "PUT":
                lines.extend(_generate_update_handler(spec, entity, route))
            elif method == "DELETE":
                lines.extend(_generate_delete_handler(spec, entity, route))
            elif method == "PATCH":
                lines.extend(_generate_update_handler(spec, entity, route))

    return "\n".join(lines)


def generate_fastapi_app(spec: PlatformSpec) -> str:
    """Generate FastAPI app: CORS, health, ready, startup migration + audit store init."""
    platform_name = spec.platform.name
    # Use ASCII-safe display name for generated docstring (avoid encoding issues on Windows)
    display_name = spec.platform.display_name.encode("ascii", "replace").decode("ascii")
    return f'''# -*- coding: utf-8 -*-
"""
{display_name} - Auto-generated by Zuup Forge v0.1.0
Audit + optional auth from forge.substrate. Regenerate with `forge compile`.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from forge.substrate.zuup_audit import init_audit_store

from .routes import router

app = FastAPI(
    title="{display_name}",
    version="{spec.platform.version}",
    description="{spec.platform.description}",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
async def startup():
    migration_path = Path(__file__).parent / "migrations" / "001_initial_sqlite.sql"
    if migration_path.exists():
        conn = sqlite3.connect("{platform_name}.db")
        conn.executescript(migration_path.read_text())
        conn.close()
    init_audit_store("{platform_name}.audit.db")


@app.get("/health")
async def health():
    return {{"status": "ok", "platform": "{platform_name}", "version": "{spec.platform.version}"}}


@app.get("/ready")
async def ready():
    return {{"status": "ready"}}


app.include_router(router, prefix="/api/v1")
'''