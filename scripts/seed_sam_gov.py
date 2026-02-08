"""Seed Aureon database with real SAM.gov opportunities.

Run from repo root after compiling the platform:
  forge compile specs/aureon.platform.yaml
  set SAM_GOV_API_KEY=your_key   (Windows) or export SAM_GOV_API_KEY=your_key (Unix)
  python scripts/seed_sam_gov.py

Get a free API key from SAM.gov -> Account Details.
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Ensure forge is importable when run as script
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(_REPO_ROOT))

import os

from forge.integrations.sam_gov import fetch_opportunities

if not os.environ.get("SAM_GOV_API_KEY"):
    print("SAM_GOV_API_KEY is not set. Get a free key from SAM.gov Account Details.")
    print("Then: set SAM_GOV_API_KEY=your_key  (Windows)  or  export SAM_GOV_API_KEY=your_key  (Unix)")
    raise SystemExit(1)

DB_PATH = _REPO_ROOT / "platforms" / "aureon" / "aureon.db"
MIGRATION_PATH = _REPO_ROOT / "platforms" / "aureon" / "migrations" / "001_initial_sqlite.sql"


async def seed() -> None:
    """Fetch opportunities from SAM.gov and insert into Aureon SQLite DB."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH))
    if MIGRATION_PATH.exists():
        conn.executescript(MIGRATION_PATH.read_text())
    else:
        print("Run first: forge compile specs/aureon.platform.yaml")
        conn.close()
        return

    # Ensure we don't insert duplicate notice_ids
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_opportunity_notice_id ON opportunity(notice_id)"
    )

    keywords = [
        "artificial intelligence",
        "cybersecurity",
        "data analytics",
        "cloud services",
        "IT modernization",
        "software development",
        "professional services",
    ]

    inserted = 0
    for kw in keywords:
        print(f"Fetching: {kw}...")
        try:
            opps = await fetch_opportunities(keyword=kw, limit=25)
            for opp in opps:
                now = datetime.now(timezone.utc).isoformat()
                try:
                    conn.execute(
                        """INSERT OR IGNORE INTO opportunity
                           (id, notice_id, title, agency, sub_agency, naics_codes,
                            set_asides, response_deadline, estimated_value,
                            place_of_performance, solicitation_type, full_text,
                            embedding, source_url, created_at, updated_at)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            str(uuid.uuid4()),
                            opp.notice_id,
                            opp.title,
                            opp.agency or "",
                            opp.sub_agency,
                            json.dumps(opp.naics_codes),
                            json.dumps(opp.set_asides),
                            opp.response_deadline.isoformat() if opp.response_deadline else None,
                            opp.estimated_value if opp.estimated_value is not None else 0.0,
                            opp.place_of_performance,
                            opp.solicitation_type or "",
                            opp.full_text or "",
                            b"",  # embedding placeholder; vectorize later
                            opp.source_url or "",
                            now,
                            now,
                        ),
                    )
                    if conn.total_changes:
                        inserted += 1
                except sqlite3.IntegrityError:
                    pass  # Duplicate notice_id
            print(f"  -> {len(opps)} fetched")
        except Exception as e:
            print(f"  -> Error: {e}")

    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM opportunity").fetchone()[0]
    conn.close()
    print(f"\nInserted this run: {inserted}")
    print(f"Total opportunities in DB: {count}")


if __name__ == "__main__":
    asyncio.run(seed())
