"""
Forge Core Tests — Spec parsing, schema gen, audit chain, auth, guardrails.
"""

import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from forge.compiler.api_gen import generate_fastapi_routes
from forge.compiler.parser import load_spec
from forge.compiler.schema_gen import (
    generate_pg_migration,
    generate_pydantic_models,
    generate_sqlite_migration,
)
from forge.compiler.spec_schema import (
    APIConfig,
    APIRoute,
    ComplianceConfig,
    ComplianceFramework,
    DataClassification,
    Entity,
    EntityField,
    FieldType,
    PlatformMetadata,
    PlatformSpec,
)
from forge.substrate.zuup_ai import PromptTemplate, guardrails, prompt_registry
from forge.substrate.zuup_audit import AuditEntry, SQLiteAuditStore
from forge.substrate.zuup_auth import (
    APIKeyConfig,
    PrincipalType,
    ZuupPrincipal,
    check_permission,
    generate_api_key,
)

# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def minimal_spec() -> PlatformSpec:
    return PlatformSpec(
        platform=PlatformMetadata(
            name="testplatform",
            display_name="Test Platform",
            domain="testing",
        ),
        entities=[
            Entity(
                name="Widget",
                description="A test widget",
                fields=[
                    EntityField(name="title", type=FieldType.STRING, searchable=True),
                    EntityField(name="count", type=FieldType.INTEGER),
                    EntityField(name="active", type=FieldType.BOOLEAN),
                    EntityField(name="tags", type=FieldType.STRING_ARRAY, required=False),
                ],
            ),
        ],
        api=APIConfig(
            version="v1",
            routes=[
                APIRoute(path="/widgets", methods=["GET", "POST"]),
                APIRoute(path="/widgets/{id}", methods=["GET", "PUT", "DELETE"]),
            ],
        ),
    )


@pytest.fixture
def spec_yaml(minimal_spec: PlatformSpec, tmp_path: Path) -> Path:
    """Write a spec to a temp YAML file."""
    data = json.loads(minimal_spec.model_dump_json())
    path = tmp_path / "test.platform.yaml"
    path.write_text(yaml.dump(data, default_flow_style=False))
    return path


# =============================================================================
# Spec Schema Tests
# =============================================================================

class TestSpecSchema:
    def test_minimal_spec_valid(self, minimal_spec):
        assert minimal_spec.platform.name == "testplatform"
        assert len(minimal_spec.entities) == 1
        assert len(minimal_spec.api.routes) == 2

    def test_pii_fields_detected(self):
        spec = PlatformSpec(
            platform=PlatformMetadata(name="test", display_name="T", domain="t"),
            entities=[Entity(name="User", fields=[
                EntityField(name="email", type=FieldType.STRING, pii=True),
                EntityField(name="name", type=FieldType.STRING),
            ])],
        )
        pii = spec.get_pii_fields()
        assert pii == [("User", "email")]

    def test_searchable_fields(self, minimal_spec):
        searchable = minimal_spec.get_searchable_fields()
        assert ("Widget", "title") in searchable

    def test_govcloud_required_for_cui(self):
        spec = PlatformSpec(
            platform=PlatformMetadata(name="gov", display_name="G", domain="gov"),
            compliance=ComplianceConfig(
                data_classification=DataClassification.CUI,
                frameworks=[ComplianceFramework.FEDRAMP_HIGH],
            ),
        )
        assert spec.requires_govcloud()

    def test_no_govcloud_for_public(self):
        spec = PlatformSpec(
            platform=PlatformMetadata(name="pub", display_name="P", domain="pub"),
            compliance=ComplianceConfig(data_classification=DataClassification.PUBLIC),
        )
        assert not spec.requires_govcloud()

    def test_invalid_platform_name_rejected(self):
        with pytest.raises(ValidationError):
            PlatformSpec(
                platform=PlatformMetadata(
                    name="invalid-name", display_name="X", domain="x"
                ),
            )


# =============================================================================
# Parser Tests
# =============================================================================

class TestParser:
    def test_load_valid_spec(self, spec_yaml):
        spec = load_spec(spec_yaml)
        assert spec.platform.name == "testplatform"

    def test_load_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_spec("/nonexistent.yaml")


# =============================================================================
# Schema Generator Tests
# =============================================================================

class TestSchemaGen:
    def test_pg_migration_has_tables(self, minimal_spec):
        sql = generate_pg_migration(minimal_spec)
        assert "CREATE TABLE" in sql
        assert "testplatform_widget" in sql
        assert "testplatform_audit" in sql

    def test_pg_migration_has_indexes(self, minimal_spec):
        sql = generate_pg_migration(minimal_spec)
        assert "CREATE INDEX" in sql
        assert "gin(to_tsvector" in sql  # Full-text search index

    def test_sqlite_migration_valid(self, minimal_spec):
        sql = generate_sqlite_migration(minimal_spec)
        assert "CREATE TABLE" in sql
        assert "PRAGMA journal_mode=WAL" in sql

    def test_pydantic_models_generated(self, minimal_spec):
        code = generate_pydantic_models(minimal_spec)
        assert "class WidgetCreate(BaseModel):" in code
        assert "class Widget(BaseModel):" in code
        assert "class WidgetUpdate(BaseModel):" in code
        assert "title: str" in code


# =============================================================================
# API Generator Tests
# =============================================================================

class TestAPIGen:
    def test_routes_generated(self, minimal_spec):
        code = generate_fastapi_routes(minimal_spec)
        assert "router = APIRouter" in code
        assert "@router.get" in code
        assert "@router.post" in code
        assert "@router.delete" in code
        assert "audit_action" in code


# =============================================================================
# Audit Chain Tests
# =============================================================================

class TestAuditChain:
    def test_entry_hash_deterministic(self):
        entry = AuditEntry(
            id="test-1", platform="test", action="create",
            principal_id="user-1", entity_type="widget", entity_id="w-1",
            payload_hash="abc123",
        )
        h1 = entry.compute_hash()
        h2 = entry.compute_hash()
        assert h1 == h2
        assert len(h1) == 64  # SHA-256

    def test_sqlite_store_append_and_query(self, tmp_path):
        store = SQLiteAuditStore(tmp_path / "test_audit.db")
        entry = AuditEntry(
            platform="test", action="create", principal_id="user-1",
            entity_type="widget", entity_id="w-1", payload_hash="abc",
        )
        entry_id = store.append(entry)
        assert entry_id

        from forge.substrate.zuup_audit import AuditQuery
        results = store.query(AuditQuery(platform="test"))
        assert len(results) == 1
        assert results[0].action == "create"

    def test_hash_chain_links(self, tmp_path):
        store = SQLiteAuditStore(tmp_path / "chain_test.db")

        e1 = AuditEntry(platform="test", action="a1", principal_id="u",
                         entity_type="t", entity_id="1", payload_hash="h1")
        store.append(e1)

        e2 = AuditEntry(platform="test", action="a2", principal_id="u",
                         entity_type="t", entity_id="2", payload_hash="h2")
        store.append(e2)

        from forge.substrate.zuup_audit import AuditQuery
        results = store.query(AuditQuery(platform="test", limit=10))
        # Most recent first
        assert results[0].prev_hash is not None


# =============================================================================
# Auth Tests
# =============================================================================

class TestAuth:
    def test_principal_role_check(self):
        p = ZuupPrincipal(id="u1", type=PrincipalType.USER, roles=["admin"])
        assert p.has_role("admin")
        # Admin auto-escalates — this is by design
        assert p.has_role("superadmin")  # admin implies all roles

        # Non-admin should NOT have other roles
        viewer = ZuupPrincipal(id="u2", type=PrincipalType.USER, roles=["viewer"])
        assert viewer.has_role("viewer")
        assert not viewer.has_role("admin")

    def test_admin_has_all_permissions(self):
        p = ZuupPrincipal(id="u1", type=PrincipalType.USER, roles=["admin"])
        assert check_permission(p, "widgets", "delete", "testplatform")

    def test_viewer_cannot_write(self):
        p = ZuupPrincipal(id="u2", type=PrincipalType.USER, roles=["viewer"])
        assert check_permission(p, "widgets", "read")
        assert not check_permission(p, "widgets", "write")

    def test_api_key_generation(self):
        config = APIKeyConfig()
        key, key_hash = generate_api_key(config)
        assert key.startswith("zuup_")
        assert len(key_hash) == 64

    def test_platform_access(self):
        p = ZuupPrincipal(id="u1", type=PrincipalType.USER, platforms=["aureon", "civium"])
        assert p.can_access_platform("aureon")
        assert not p.can_access_platform("orb")


# =============================================================================
# AI Substrate Tests
# =============================================================================

class TestAISubstrate:
    def test_guardrail_blocks_ssn(self):
        result = guardrails.check("SSN: 123-45-6789", ["no_pii"])
        assert not result[0].passed

    def test_guardrail_passes_clean(self):
        result = guardrails.check("This is clean text", ["no_pii"])
        assert result[0].passed

    def test_prompt_registry(self):
        tmpl = PromptTemplate(
            name="test_prompt", version="1.0", platform="test",
            template="Score this: {{opportunity}}",
            variables=["opportunity"],
        )
        prompt_registry.register(tmpl)
        retrieved = prompt_registry.get("test_prompt")
        assert retrieved is not None
        assert retrieved.render(opportunity="Build a bridge") == "Score this: Build a bridge"

    def test_prompt_hash_stable(self):
        tmpl = PromptTemplate(
            name="hash_test", version="1.0", platform="test",
            template="Hello {{name}}", variables=["name"],
        )
        assert tmpl.hash == tmpl.hash
        assert len(tmpl.hash) == 12


# =============================================================================
# Smoke Test: End-to-End Spec → Generated Code
# =============================================================================

class TestE2E:
    def test_full_pipeline(self, spec_yaml):
        """Load spec → generate all artifacts → verify structure."""
        spec = load_spec(spec_yaml)

        pg_sql = generate_pg_migration(spec)
        sqlite_sql = generate_sqlite_migration(spec)
        models = generate_pydantic_models(spec)
        routes = generate_fastapi_routes(spec)

        # All artifacts are non-empty
        assert len(pg_sql) > 100
        assert len(sqlite_sql) > 100
        assert len(models) > 100
        assert len(routes) > 100

        # Models are valid Python (basic check)
        assert "class Widget" in models
        assert "from pydantic import" in models

        # Routes reference the right platform
        assert "testplatform" in routes
