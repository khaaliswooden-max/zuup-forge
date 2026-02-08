-- Zuup Forge: SQLite migration for Aureon™
-- Platform: aureon v0.1.0

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS aureon_audit (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    platform TEXT NOT NULL,
    action TEXT NOT NULL,
    principal_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    prev_hash TEXT,
    metadata TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS aureon_opportunity (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at TEXT,
    notice_id TEXT NOT NULL,
    title TEXT NOT NULL,
    agency TEXT NOT NULL,
    sub_agency TEXT,
    naics_codes TEXT NOT NULL,
    set_asides TEXT NOT NULL,
    response_deadline TEXT DEFAULT (datetime('now')),
    estimated_value REAL NOT NULL,
    place_of_performance TEXT,
    solicitation_type TEXT NOT NULL,
    full_text TEXT NOT NULL,
    embedding TEXT NOT NULL,
    source_url TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS aureon_vendor (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    cage_code TEXT UNIQUE NOT NULL,
    uei TEXT UNIQUE NOT NULL,
    legal_name TEXT NOT NULL,
    dba_name TEXT,
    capabilities TEXT NOT NULL,
    naics_codes TEXT NOT NULL,
    certifications TEXT NOT NULL,
    past_performance_score REAL,
    sam_status TEXT NOT NULL,
    contact_email TEXT NOT NULL,
    hubzone_qualified INTEGER DEFAULT 0,
    capability_embedding TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS aureon_opportunitymatch (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at TEXT,
    match_score REAL NOT NULL,
    capability_score REAL NOT NULL,
    compliance_score REAL NOT NULL,
    past_performance_score REAL NOT NULL,
    set_aside_eligible INTEGER DEFAULT 0,
    explanation TEXT NOT NULL,
    model_version TEXT NOT NULL,
    confidence REAL NOT NULL
);
