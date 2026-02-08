"""
Forge Compiler

Orchestrates all code generation from a PlatformSpec.
Takes a YAML spec → produces a complete, runnable platform.
"""

from __future__ import annotations

from pathlib import Path

from forge.compiler.api_gen import generate_fastapi_app, generate_fastapi_routes
from forge.compiler.schema_gen import (
    generate_pg_migration,
    generate_pydantic_models,
    generate_sqlite_migration,
)
from forge.compiler.spec_schema import PlatformSpec


class CompileResult:
    """Result of compiling a platform spec."""

    def __init__(self, platform_name: str, output_dir: Path):
        self.platform_name = platform_name
        self.output_dir = output_dir
        self.files_generated: list[str] = []
        self.warnings: list[str] = []

    def add_file(self, path: str) -> None:
        self.files_generated.append(path)

    def summary(self) -> str:
        return (
            f"Compiled {self.platform_name}: "
            f"{len(self.files_generated)} files generated in {self.output_dir}"
        )


def compile_platform(spec: PlatformSpec, output_dir: str | Path) -> CompileResult:
    """
    Compile a PlatformSpec into a complete platform codebase.

    This is the main entry point for code generation.
    """
    output_dir = Path(output_dir)
    result = CompileResult(spec.platform.name, output_dir)

    # Create directory structure
    dirs = [
        output_dir,
        output_dir / "migrations",
        output_dir / "models",
        output_dir / "routes",
        output_dir / "services",
        output_dir / "tests",
        output_dir / "config",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    # 1. Database migrations
    pg_sql = generate_pg_migration(spec)
    pg_path = output_dir / "migrations" / "001_initial.sql"
    pg_path.write_text(pg_sql)
    result.add_file(str(pg_path))

    sqlite_sql = generate_sqlite_migration(spec)
    sqlite_path = output_dir / "migrations" / "001_initial_sqlite.sql"
    sqlite_path.write_text(sqlite_sql)
    result.add_file(str(sqlite_path))

    # 2. Pydantic models
    models_py = generate_pydantic_models(spec)
    models_path = output_dir / "models" / "__init__.py"
    models_path.write_text(models_py)
    result.add_file(str(models_path))

    # 3. API routes
    routes_py = generate_fastapi_routes(spec)
    routes_path = output_dir / "routes" / "__init__.py"
    routes_path.write_text(routes_py)
    result.add_file(str(routes_path))

    # 4. FastAPI app
    app_py = generate_fastapi_app(spec)
    app_path = output_dir / "app.py"
    app_path.write_text(app_py)
    result.add_file(str(app_path))

    # 5. Services stub
    services_init = _generate_services_stub(spec)
    services_path = output_dir / "services" / "__init__.py"
    services_path.write_text(services_init)
    result.add_file(str(services_path))

    # 6. Platform __init__.py
    init_path = output_dir / "__init__.py"
    init_path.write_text(f'"""Auto-generated platform: {spec.platform.display_name}"""\n')
    result.add_file(str(init_path))

    # 7. Config
    config_py = _generate_config(spec)
    config_path = output_dir / "config" / "__init__.py"
    config_path.write_text(config_py)
    result.add_file(str(config_path))

    # 8. Tests
    test_py = _generate_tests(spec)
    test_path = output_dir / "tests" / "test_api.py"
    test_path.write_text(test_py)
    result.add_file(str(test_path))

    # 9. Dockerfile
    dockerfile = _generate_dockerfile(spec)
    docker_path = output_dir / "Dockerfile"
    docker_path.write_text(dockerfile)
    result.add_file(str(docker_path))

    # 10. Platform spec copy (for reference)
    spec_path = output_dir / "platform.spec.json"
    spec_path.write_text(spec.model_dump_json(indent=2))
    result.add_file(str(spec_path))

    return result


def _generate_services_stub(spec: PlatformSpec) -> str:
    lines = [
        f'"""Service layer for {spec.platform.display_name}."""',
        "",
        "# Domain logic goes here.",
        "# The compiler generates route stubs that call into these services.",
        "# Implement your business rules below.",
        "",
    ]
    for entity in spec.entities:
        lines.extend([
            f"# --- {entity.name} Service ---",
            f"# TODO: Implement CRUD + domain logic for {entity.name}",
            "",
        ])
    return "\n".join(lines)


def _generate_config(spec: PlatformSpec) -> str:
    return f'''"""Configuration for {spec.platform.display_name}."""

import os

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///{spec.platform.name}.db")

# Auth
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# Platform
PLATFORM_NAME = "{spec.platform.name}"
PLATFORM_VERSION = "{spec.platform.version}"
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Compliance
DATA_CLASSIFICATION = "{spec.compliance.data_classification.value}"
AUDIT_RETENTION_DAYS = {spec.compliance.audit_retention_days}

# Rate limiting
RATE_LIMIT = "{spec.api.global_rate_limit}"
'''


def _generate_tests(spec: PlatformSpec) -> str:
    lines = [
        f'"""Auto-generated tests for {spec.platform.display_name}."""',
        "",
        "import pytest",
        "from fastapi.testclient import TestClient",
        "",
        f"from platforms.{spec.platform.name}.app import app",
        "",
        "client = TestClient(app)",
        "",
        "",
        "def test_health():",
        '    resp = client.get("/health")',
        "    assert resp.status_code == 200",
        '    assert resp.json()["status"] == "ok"',
        "",
        "",
        "def test_ready():",
        '    resp = client.get("/ready")',
        "    assert resp.status_code == 200",
        "",
    ]

    for route in spec.api.routes:
        for method in route.methods:
            path_slug = route.path.strip("/").replace("/", "_").replace("{", "").replace("}", "")
            test_name = f"test_{method.lower()}_{path_slug}"
            if method == "GET":
                path = route.path.replace("{id}", "test-id")
                base = spec.api.base_path.strip("/")
                url_path = f'"/{base}/{spec.api.version}{path}"'
                lines.extend([
                    f"def {test_name}():",
                    f"    resp = client.get({url_path})",
                    "    assert resp.status_code in (200, 401, 404)",
                    "",
                ])

    return "\n".join(lines)


def _generate_dockerfile(spec: PlatformSpec) -> str:
    return f'''FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[prod]"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "platforms.{spec.platform.name}.app:app", "--host", "0.0.0.0", "--port", "8000"]
'''
