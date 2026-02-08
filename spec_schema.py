"""
Zuup Forge Platform Specification DSL

This module defines the schema for platform specification YAML files.
Every Zuup platform is described declaratively, then compiled into
production code by the Forge compiler.

Design principles:
- Declarative over imperative
- Compliance by default
- Every field has a security/audit implication
- Domain logic is isolated from infrastructure
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Enums
# =============================================================================

class DataClassification(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    CUI = "CUI"                    # Controlled Unclassified Information
    SECRET = "secret"              # Requires GovCloud
    TOP_SECRET = "top_secret"      # Requires air-gapped


class ComplianceFramework(str, Enum):
    FEDRAMP_LOW = "FedRAMP_Low"
    FEDRAMP_MOD = "FedRAMP_Moderate"
    FEDRAMP_HIGH = "FedRAMP_High"
    CMMC_L1 = "CMMC_L1"
    CMMC_L2 = "CMMC_L2"
    CMMC_L3 = "CMMC_L3"
    HIPAA = "HIPAA"
    CJIS = "CJIS"
    FAR = "FAR"
    DFARS = "DFARS"
    SOC2 = "SOC2"
    ISO27001 = "ISO27001"
    HALAL_JAKIM = "HALAL_JAKIM"
    HALAL_MUI = "HALAL_MUI"
    HALAL_GCC = "HALAL_GCC"
    FDA_510K = "FDA_510K"
    FDA_PMA = "FDA_PMA"
    IRB = "IRB"


class FieldType(str, Enum):
    STRING = "string"
    TEXT = "text"
    INTEGER = "integer"
    FLOAT = "float"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    DATE = "date"
    JSON = "json"
    UUID = "uuid"
    STRING_ARRAY = "string[]"
    INT_ARRAY = "int[]"
    FLOAT_ARRAY = "float[]"
    VECTOR = "vector"              # pgvector embedding
    BINARY = "binary"


class RelationType(str, Enum):
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_MANY = "many_to_many"


class AuthMethod(str, Enum):
    API_KEY = "api_key"
    JWT = "jwt"
    OIDC = "oidc"
    MTLS = "mtls"
    NONE = "none"


class ModelType(str, Enum):
    CLASSIFIER = "classifier"
    GENERATOR = "generator"
    EMBEDDER = "embedder"
    RANKER = "ranker"
    EXTRACTOR = "extractor"
    AGENT = "agent"


class DeployTarget(str, Enum):
    LOCAL = "local"
    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"
    GOVCLOUD = "govcloud"
    AIRGAPPED = "airgapped"


# =============================================================================
# Field & Entity Definitions
# =============================================================================

class EntityField(BaseModel):
    """A single field on a domain entity."""
    name: str
    type: FieldType
    description: str = ""
    required: bool = True
    indexed: bool = False
    unique: bool = False
    searchable: bool = False       # Full-text search
    vectorize: bool = False        # Auto-generate embeddings
    pii: bool = False              # Marks personally identifiable information
    encrypted_at_rest: bool = False
    default: Any = None
    min_length: int | None = None
    max_length: int | None = None
    regex: str | None = None
    vector_dimensions: int = 768   # For vector fields

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v.isidentifier():
            raise ValueError(f"Field name must be a valid identifier: {v}")
        return v


class EntityRelation(BaseModel):
    """A relationship between two entities."""
    target: str                    # Target entity name
    type: RelationType
    via: str | None = None         # Junction table for many_to_many
    cascade_delete: bool = False
    description: str = ""


class Entity(BaseModel):
    """A domain entity (maps to a DB table + API resource)."""
    name: str
    description: str = ""
    fields: list[EntityField]
    relations: list[EntityRelation] = []
    soft_delete: bool = True       # Never hard-delete by default
    versioned: bool = False        # Track all changes
    audit_all: bool = True         # Log every CRUD operation
    retention_days: int | None = None


# =============================================================================
# AI Configuration
# =============================================================================

class Guardrail(BaseModel):
    """A safety guardrail for AI model I/O."""
    name: str
    type: Literal["input", "output", "both"] = "both"
    description: str = ""
    rule: str                      # Python expression or regex
    action: Literal["block", "warn", "log"] = "block"


class EvalMetric(BaseModel):
    """An evaluation metric for a model."""
    name: str
    type: Literal["accuracy", "f1", "precision", "recall", "bleu", "rouge",
                   "latency_ms", "cost_per_call", "custom"]
    target: float
    weight: float = 1.0
    custom_fn: str | None = None   # Python function path for custom metrics


class AIModel(BaseModel):
    """An AI model used by the platform."""
    name: str
    type: ModelType
    description: str = ""
    input: list[str]               # Input field names
    output: str                    # Output field/type
    base_model: str = "claude-sonnet-4-20250514"
    guardrails: list[str] = []     # References to guardrail names
    eval_suite: str | None = None
    eval_metrics: list[EvalMetric] = []
    max_latency_ms: int = 5000
    fallback_model: str | None = None
    preference_enabled: bool = True


class AITool(BaseModel):
    """An external tool the AI can invoke."""
    name: str
    type: Literal["api_integration", "database_query", "file_operation",
                   "computation", "human_in_loop"]
    description: str = ""
    endpoint: str | None = None
    auth: AuthMethod = AuthMethod.NONE
    rate_limit: str | None = None  # e.g., "100/min"
    timeout_ms: int = 10000
    requires_approval: bool = False  # Human-in-the-loop gate
    idempotent: bool = False


class PreferenceDomain(BaseModel):
    """A domain for preference/feedback collection."""
    domain: str
    categories: list[str]
    min_quality_score: float = 0.7
    target_count: int = 500


class AIConfig(BaseModel):
    """AI configuration for a platform."""
    models: list[AIModel] = []
    tools: list[AITool] = []
    guardrails: list[Guardrail] = []
    preference_domains: list[PreferenceDomain] = []


# =============================================================================
# API Configuration
# =============================================================================

class APIRoute(BaseModel):
    """An API route definition."""
    path: str
    methods: list[Literal["GET", "POST", "PUT", "PATCH", "DELETE"]]
    auth: Literal["required", "optional", "none"] = "required"
    rate_limit: str | None = None
    description: str = ""
    request_schema: str | None = None   # Entity name
    response_schema: str | None = None  # Entity name
    pagination: bool = True
    cache_ttl_seconds: int = 0


class APIConfig(BaseModel):
    """API configuration for a platform."""
    version: str = "v1"
    base_path: str = "/api"
    routes: list[APIRoute] = []
    global_rate_limit: str = "1000/min"
    cors_origins: list[str] = ["*"]
    docs_enabled: bool = True


# =============================================================================
# Compliance Configuration
# =============================================================================

class ComplianceConfig(BaseModel):
    """Compliance requirements for a platform."""
    frameworks: list[ComplianceFramework] = []
    data_classification: DataClassification = DataClassification.INTERNAL
    audit_retention_days: int = 365
    pii_fields_encrypted: bool = True
    data_residency: list[str] = ["US"]  # ISO country codes
    breach_notification_hours: int = 72
    evidence_auto_collect: bool = True


# =============================================================================
# Platform Specification (Top-Level)
# =============================================================================

class PlatformMetadata(BaseModel):
    """Core platform metadata."""
    name: str                      # Machine name (lowercase, no spaces)
    display_name: str
    domain: str                    # Business domain
    description: str = ""
    version: str = "0.1.0"
    icon: str = "🔧"
    owners: list[str] = []        # GitHub usernames
    tags: list[str] = []


class PlatformSpec(BaseModel):
    """
    Complete platform specification.

    This is the root schema that defines everything about a Zuup platform.
    The Forge compiler reads this spec and generates production code.
    """
    platform: PlatformMetadata
    compliance: ComplianceConfig = ComplianceConfig()
    entities: list[Entity] = []
    ai: AIConfig = AIConfig()
    api: APIConfig = APIConfig()

    # Deployment overrides
    deploy_targets: list[DeployTarget] = [DeployTarget.DEV, DeployTarget.STAGING]
    resource_limits: dict[str, Any] = {
        "cpu": "1000m",
        "memory": "2Gi",
        "gpu": None,
    }

    # Feature flags
    features: dict[str, bool] = {
        "audit_chain": True,
        "preference_collection": True,
        "compliance_hooks": True,
        "observability": True,
        "api_versioning": True,
        "rate_limiting": True,
        "caching": True,
    }

    @field_validator("platform")
    @classmethod
    def validate_platform_name(cls, v: PlatformMetadata) -> PlatformMetadata:
        if not v.name.isidentifier():
            raise ValueError(f"Platform name must be a valid identifier: {v.name}")
        return v

    def get_pii_fields(self) -> list[tuple[str, str]]:
        """Returns (entity_name, field_name) pairs for all PII fields."""
        result = []
        for entity in self.entities:
            for field in entity.fields:
                if field.pii:
                    result.append((entity.name, field.name))
        return result

    def get_searchable_fields(self) -> list[tuple[str, str]]:
        """Returns (entity_name, field_name) pairs for all searchable fields."""
        result = []
        for entity in self.entities:
            for field in entity.fields:
                if field.searchable:
                    result.append((entity.name, field.name))
        return result

    def requires_govcloud(self) -> bool:
        """Determine if this platform must run in GovCloud."""
        high_compliance = {
            ComplianceFramework.FEDRAMP_HIGH,
            ComplianceFramework.CMMC_L3,
            ComplianceFramework.CJIS,
        }
        high_classification = {
            DataClassification.CUI,
            DataClassification.SECRET,
            DataClassification.TOP_SECRET,
        }
        return (
            bool(set(self.compliance.frameworks) & high_compliance)
            or self.compliance.data_classification in high_classification
        )
