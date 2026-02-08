"""Configuration for Aureon™."""

import os

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///aureon.db")

# Auth
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# Platform
PLATFORM_NAME = "aureon"
PLATFORM_VERSION = "0.1.0"
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Compliance
DATA_CLASSIFICATION = "CUI"
AUDIT_RETENTION_DAYS = 2555

# Rate limiting
RATE_LIMIT = "500/min"
