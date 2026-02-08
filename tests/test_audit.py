"""Audit substrate: hash-chain attestation and verification."""

import tempfile

import pytest

from forge.substrate.zuup_audit import AuditEntry, SQLiteAuditStore


def test_audit_chain_integrity(tmp_path):
    """Append entries and verify hash linkage is intact."""
    db = tmp_path / "audit.db"
    store = SQLiteAuditStore(str(db))
    for i in range(10):
        store.append(
            AuditEntry(
                platform="test",
                action=f"action_{i}",
                principal_id="tester",
                entity_type="test",
                entity_id=str(i),
                payload_hash=f"hash_{i}",
            )
        )
    result = store.verify_chain("test", limit=20)
    assert result.valid
    assert result.entries_checked == 10


def test_audit_chain_detects_tampering(tmp_path):
    """Verification fails when entry_hash is wrong."""
    db = tmp_path / "audit_tamper.db"
    store = SQLiteAuditStore(str(db))
    store.append(
        AuditEntry(
            platform="tamper",
            action="ok",
            principal_id="u",
            entity_type="e",
            entity_id="1",
            payload_hash="h",
        )
    )
    # Corrupt stored hash (would require direct DB write in real scenario)
    import sqlite3

    conn = sqlite3.connect(store.db_path)
    conn.execute("UPDATE audit_chain SET entry_hash = ? WHERE platform = ?", ("bad", "tamper"))
    conn.commit()
    conn.close()
    result = store.verify_chain("tamper")
    assert not result.valid
    assert result.error is not None
