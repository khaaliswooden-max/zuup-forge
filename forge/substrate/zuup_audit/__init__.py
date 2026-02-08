"""
Zuup Audit Substrate - Hash-chain attestation system.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AuditEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    platform: str
    action: str
    principal_id: str
    entity_type: str
    entity_id: str
    payload_hash: str
    prev_hash: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    entry_hash: str = ""

    def compute_hash(self) -> str:
        data = {
            "id": self.id, "timestamp": self.timestamp.isoformat(),
            "platform": self.platform, "action": self.action,
            "principal_id": self.principal_id, "entity_type": self.entity_type,
            "entity_id": self.entity_id, "payload_hash": self.payload_hash,
            "prev_hash": self.prev_hash or "",
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def finalize(self) -> AuditEntry:
        self.entry_hash = self.compute_hash()
        return self

class AuditQuery(BaseModel):
    platform: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    principal_id: str | None = None
    action: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    limit: int = 100
    offset: int = 0

class ChainVerificationResult(BaseModel):
    valid: bool
    entries_checked: int
    first_invalid_id: str | None = None
    error: str | None = None

class SQLiteAuditStore:
    def __init__(self, db_path: str | Path = "audit.db"):
        self.db_path = str(db_path)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_chain (
                id TEXT PRIMARY KEY, timestamp TEXT NOT NULL,
                platform TEXT NOT NULL, action TEXT NOT NULL,
                principal_id TEXT NOT NULL, entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL, payload_hash TEXT NOT NULL,
                prev_hash TEXT, metadata TEXT DEFAULT '{}',
                entry_hash TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_pt ON audit_chain(platform, timestamp DESC)")
        conn.commit()
        conn.close()

    def append(self, entry: AuditEntry) -> str:
        prev_hash = self.get_last_hash(entry.platform)
        entry.prev_hash = prev_hash
        entry.finalize()
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO audit_chain (id,timestamp,platform,action,principal_id,"
            "entity_type,entity_id,payload_hash,prev_hash,metadata,entry_hash) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (entry.id, entry.timestamp.isoformat(), entry.platform, entry.action,
             entry.principal_id, entry.entity_type, entry.entity_id, entry.payload_hash,
             entry.prev_hash, json.dumps(entry.metadata), entry.entry_hash))
        conn.commit()
        conn.close()
        return entry.id

    def get_last_hash(self, platform: str) -> str | None:
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT entry_hash FROM audit_chain WHERE platform=? ORDER BY timestamp DESC LIMIT 1",
            (platform,),
        ).fetchone()
        conn.close()
        return row[0] if row else None

    def query(self, q: AuditQuery) -> list[AuditEntry]:
        conds, params = [], []
        if q.platform:
            conds.append("platform=?")
            params.append(q.platform)
        if q.entity_type:
            conds.append("entity_type=?")
            params.append(q.entity_type)
        if q.entity_id:
            conds.append("entity_id=?")
            params.append(q.entity_id)
        where = " AND ".join(conds) if conds else "1=1"
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        sql = f"SELECT * FROM audit_chain WHERE {where} ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        rows = conn.execute(sql, params + [q.limit, q.offset]).fetchall()
        conn.close()
        out = []
        for r in rows:
            out.append(AuditEntry(
                id=r["id"],
                timestamp=datetime.fromisoformat(r["timestamp"]),
                platform=r["platform"],
                action=r["action"],
                principal_id=r["principal_id"],
                entity_type=r["entity_type"],
                entity_id=r["entity_id"],
                payload_hash=r["payload_hash"],
                prev_hash=r["prev_hash"],
                metadata=json.loads(r["metadata"]),
                entry_hash=r["entry_hash"],
            ))
        return out

    def verify_chain(self, platform: str, limit: int = 1000) -> ChainVerificationResult:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM audit_chain WHERE platform=? ORDER BY timestamp ASC LIMIT ?",
            (platform, limit),
        ).fetchall()
        conn.close()
        if not rows:
            return ChainVerificationResult(valid=True, entries_checked=0)
        prev_hash = None
        for row in rows:
            entry = AuditEntry(
                id=row["id"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                platform=row["platform"],
                action=row["action"],
                principal_id=row["principal_id"],
                entity_type=row["entity_type"],
                entity_id=row["entity_id"],
                payload_hash=row["payload_hash"],
                prev_hash=row["prev_hash"],
                metadata=json.loads(row["metadata"]),
                entry_hash=row["entry_hash"],
            )

            # Verify prev_hash linkage
            if entry.prev_hash != prev_hash:
                return ChainVerificationResult(
                    valid=False,
                    entries_checked=rows.index(row),
                    first_invalid_id=entry.id,
                    error=f"Chain break: expected prev_hash={prev_hash}, got={entry.prev_hash}",
                )

            # Verify entry hash
            computed = entry.compute_hash()
            if computed != entry.entry_hash:
                return ChainVerificationResult(
                    valid=False,
                    entries_checked=rows.index(row),
                    first_invalid_id=entry.id,
                    error=f"Hash mismatch: computed={computed}, stored={entry.entry_hash}",
                )

            prev_hash = entry.entry_hash

        return ChainVerificationResult(valid=True, entries_checked=len(rows))


def hash_payload(payload: Any) -> str:
    """Hash an arbitrary payload for audit recording."""
    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


# Re-export for generated routes and tests
from .middleware import (
    get_audit_store,
    init_audit_store,
    log_audit_event,
)
