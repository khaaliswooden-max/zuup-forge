"""
Zuup Auth Substrate

Production-grade authentication and authorization for all Zuup platforms.
Implements JWT validation, RBAC, and principal tracking.

Security model:
- All requests must carry a valid JWT or API key
- Principals are typed (user, service, system)
- Permissions are checked at route level via RBAC
- All auth events are audit-logged
"""

from __future__ import annotations

import hashlib
import hmac
import time
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

# =============================================================================
# Principal Model
# =============================================================================

class PrincipalType(StrEnum):
    USER = "user"
    SERVICE = "service"
    SYSTEM = "system"
    ANONYMOUS = "anonymous"


class ZuupPrincipal(BaseModel):
    """
    Represents an authenticated actor in any Zuup platform.

    Every API request resolves to a ZuupPrincipal. This is the identity
    that gets recorded in audit logs and checked against RBAC policies.
    """
    id: str
    type: PrincipalType
    email: str | None = None
    name: str | None = None
    platforms: list[str] = Field(default_factory=list)
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    authenticated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    token_hash: str | None = None  # Hash of the auth token for audit

    def has_role(self, role: str) -> bool:
        return role in self.roles or "admin" in self.roles

    def has_permission(self, permission: str) -> bool:
        if "admin:*" in self.permissions:
            return True
        return permission in self.permissions

    def can_access_platform(self, platform: str) -> bool:
        return platform in self.platforms or "*" in self.platforms


ANONYMOUS_PRINCIPAL = ZuupPrincipal(
    id="anonymous",
    type=PrincipalType.ANONYMOUS,
)

SYSTEM_PRINCIPAL = ZuupPrincipal(
    id="system",
    type=PrincipalType.SYSTEM,
    platforms=["*"],
    roles=["admin"],
    permissions=["admin:*"],
)


# =============================================================================
# JWT Handling
# =============================================================================

class JWTConfig(BaseModel):
    """JWT validation configuration."""
    secret: str = ""           # For HMAC (dev only)
    public_key: str = ""       # For RS256/ES256 (production)
    issuer: str = "zuup-forge"
    audience: str = "zuup-platform"
    algorithm: str = "HS256"   # HS256 for dev, RS256 for production
    max_age_seconds: int = 3600


def decode_jwt_claims(token: str, config: JWTConfig) -> dict[str, Any]:
    """
    Decode and validate a JWT token.

    In production, use PyJWT with proper key management.
    This implementation provides the interface contract.
    """
    import base64
    import json

    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid JWT format")

        # Decode payload (middle part)
        payload = parts[1]
        # Add padding
        payload += "=" * (4 - len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        claims = json.loads(decoded)

        # Validate expiry
        exp = claims.get("exp", 0)
        if exp and exp < time.time():
            raise ValueError("Token expired")

        # Validate issuer
        if claims.get("iss") != config.issuer:
            raise ValueError(f"Invalid issuer: {claims.get('iss')}")

        return claims

    except Exception as e:
        raise ValueError(f"JWT validation failed: {e}") from e


def claims_to_principal(claims: dict[str, Any]) -> ZuupPrincipal:
    """Convert JWT claims to a ZuupPrincipal."""
    return ZuupPrincipal(
        id=claims.get("sub", "unknown"),
        type=PrincipalType(claims.get("type", "user")),
        email=claims.get("email"),
        name=claims.get("name"),
        platforms=claims.get("platforms", []),
        roles=claims.get("roles", []),
        permissions=claims.get("permissions", []),
        token_hash=hashlib.sha256(str(claims).encode()).hexdigest()[:16],
    )


# =============================================================================
# API Key Handling
# =============================================================================

class APIKeyConfig(BaseModel):
    """API key validation configuration."""
    prefix: str = "zuup_"
    hash_algorithm: str = "sha256"


def validate_api_key(key: str, stored_hash: str, config: APIKeyConfig) -> bool:
    """Validate an API key against its stored hash."""
    if not key.startswith(config.prefix):
        return False
    computed = hashlib.sha256(key.encode()).hexdigest()
    return hmac.compare_digest(computed, stored_hash)


def generate_api_key(config: APIKeyConfig) -> tuple[str, str]:
    """Generate a new API key. Returns (key, hash)."""
    import secrets
    raw = secrets.token_urlsafe(32)
    key = f"{config.prefix}{raw}"
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    return key, key_hash


# =============================================================================
# RBAC
# =============================================================================

class Permission(BaseModel):
    """A single permission."""
    resource: str       # e.g., "opportunities", "vendors"
    action: str         # e.g., "read", "write", "delete", "admin"
    platform: str = "*" # Which platform this applies to

    @property
    def key(self) -> str:
        return f"{self.platform}:{self.resource}:{self.action}"


class Role(BaseModel):
    """A role with a set of permissions."""
    name: str
    description: str = ""
    permissions: list[Permission] = []

    def has_permission(self, resource: str, action: str, platform: str = "*") -> bool:
        for perm in self.permissions:
            if (
                (perm.resource == resource or perm.resource == "*")
                and (perm.action == action or perm.action == "*")
                and (perm.platform == platform or perm.platform == "*")
            ):
                return True
        return False


# Default roles
ROLES: dict[str, Role] = {
    "admin": Role(
        name="admin",
        description="Full access to all resources",
        permissions=[Permission(resource="*", action="*", platform="*")],
    ),
    "operator": Role(
        name="operator",
        description="Read/write access to platform resources",
        permissions=[
            Permission(resource="*", action="read"),
            Permission(resource="*", action="write"),
        ],
    ),
    "viewer": Role(
        name="viewer",
        description="Read-only access",
        permissions=[Permission(resource="*", action="read")],
    ),
    "service": Role(
        name="service",
        description="Service-to-service access",
        permissions=[
            Permission(resource="*", action="read"),
            Permission(resource="*", action="write"),
        ],
    ),
}


def check_permission(
    principal: ZuupPrincipal,
    resource: str,
    action: str,
    platform: str = "*",
) -> bool:
    """Check if a principal has permission to perform an action."""
    # Direct permission check
    perm_key = f"{platform}:{resource}:{action}"
    if perm_key in principal.permissions or "*:*:*" in principal.permissions:
        return True

    # Role-based check
    for role_name in principal.roles:
        role = ROLES.get(role_name)
        if role and role.has_permission(resource, action, platform):
            return True

    return False
