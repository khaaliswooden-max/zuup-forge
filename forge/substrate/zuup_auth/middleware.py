"""
FastAPI Authentication Middleware

Extracts and validates credentials from incoming requests,
resolving them to ZuupPrincipal objects.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from forge.substrate.zuup_auth import (
    ANONYMOUS_PRINCIPAL,
    JWTConfig,
    ZuupPrincipal,
    claims_to_principal,
    decode_jwt_claims,
)

# Security scheme
bearer_scheme = HTTPBearer(auto_error=False)

# Default config — override via environment
_jwt_config = JWTConfig()


def configure_auth(config: JWTConfig) -> None:
    """Configure JWT validation at startup."""
    global _jwt_config
    _jwt_config = config


async def get_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> ZuupPrincipal:
    """
    Extract principal from request.

    Checks (in order):
    1. Bearer token (JWT)
    2. X-API-Key header
    3. Falls back to anonymous
    """
    # Try Bearer token
    if credentials and credentials.credentials:
        try:
            claims = decode_jwt_claims(credentials.credentials, _jwt_config)
            principal = claims_to_principal(claims)
            request.state.principal = principal
            return principal
        except ValueError:
            raise HTTPException(401, detail="Invalid or expired token")

    # Try API key
    api_key = request.headers.get("X-API-Key")
    if api_key:
        # TODO: Look up API key in database
        # For now, return a service principal
        principal = ZuupPrincipal(
            id=f"apikey:{api_key[:8]}",
            type="service",
            platforms=["*"],
            roles=["service"],
        )
        request.state.principal = principal
        return principal

    # Anonymous
    request.state.principal = ANONYMOUS_PRINCIPAL
    return ANONYMOUS_PRINCIPAL


async def require_auth(
    principal: ZuupPrincipal = Depends(get_principal),
) -> ZuupPrincipal:
    """Dependency that requires authentication (rejects anonymous)."""
    if principal.type == "anonymous":
        raise HTTPException(401, detail="Authentication required")
    return principal


async def require_role(role: str):
    """Factory for role-checking dependencies."""
    async def _check(principal: ZuupPrincipal = Depends(require_auth)):
        if not principal.has_role(role):
            raise HTTPException(403, detail=f"Role '{role}' required")
        return principal
    return _check


async def require_platform(platform: str):
    """Factory for platform-access-checking dependencies."""
    async def _check(principal: ZuupPrincipal = Depends(require_auth)):
        if not principal.can_access_platform(platform):
            raise HTTPException(403, detail=f"Access to platform '{platform}' denied")
        return principal
    return _check
