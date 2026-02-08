# ZUUP FORGE — Cursor Execution Plan v2

## Remediate All Blockers → Build to Desired State

**Date**: 2026-02-08
**Prerequisite**: Clone `khaaliswooden-max/zuup-forge` and open in Cursor
**Reference**: ZUUP_FORGE_DESIRED_STATE.md, .cursorrules

---

## PHASE 0: EMERGENCY TRIAGE (30 min)

**Goal**: Repo compiles and installs. Zero functionality required yet.

### Step 0.1 — Nuke flat file dump, restore package hierarchy

The repo currently has Python modules dumped at root alongside a
nested `zuup-forge/` subdirectory that contains the actual package.
This must be fixed first. Everything else depends on it.

```bash
cd zuup-forge  # repo root

# --- Preserve the real package from the nested subdir ---
# Check what's inside the nested copy
ls zuup-forge/forge/

# Move the actual forge package to repo root
# (if forge/ already exists at root from prior partial fix, remove it first)
rm -rf forge/
cp -r zuup-forge/forge ./forge

# Move specs if they exist in the nested dir
mkdir -p specs
cp zuup-forge/specs/aureon.platform.yaml specs/ 2>/dev/null || true

# --- Remove ALL flat-file duplicates from root ---
rm -f api_gen.py parser.py schema_gen.py spec_schema.py
rm -f models.py routes.py middleware.py rate_limit.py versioning.py
rm -f main.py app.py index.py
rm -f test_api.py test_forge_compiler.py test_forge_core.py
rm -f 001_initial.sql 001_initial_sqlite.sql
rm -f aureon.platform.yaml forge.config.json platform.spec.json project.json
rm -f README.txt
rm -f forge.css forge.js  # old dashboard assets

# --- Remove build artifacts ---
rm -rf zuup_forge.egg-info/
rm -rf zuup-forge/  # the nested copy (we already extracted forge/)

# --- Move CI to correct location ---
mkdir -p .github/workflows
mv ci.yml .github/workflows/ci.yml 2>/dev/null || true

# --- Verify ---
ls forge/           # Should show: __init__.py, cli/, compiler/, substrate/
ls forge/compiler/  # Should show: __init__.py, parser.py, spec_schema.py, etc.
ls specs/           # Should show: aureon.platform.yaml
```

**Smoke test**: After this step, the directory should match the structure
in `.cursorrules`.

### Step 0.2 — Create .gitignore

```bash
cat > .gitignore << 'GITIGNORE'
# Python
__pycache__/
*.pyc
*.pyo
*.egg-info/
dist/
build/
.eggs/

# Generated platforms (re-generate from specs)
platforms/

# Environment
.env
.env.local
*.db

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Testing
.pytest_cache/
.coverage
htmlcov/
.mypy_cache/
.ruff_cache/

# Lock files (keep pyproject.toml as source of truth)
uv.lock
GITIGNORE
```

### Step 0.3 — Fix pyproject.toml

Replace the entire `pyproject.toml` with this minimal, correct version:

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "zuup-forge"
version = "0.1.0"
description = "Declarative platform compiler for compliance-ready AI systems"
requires-python = ">=3.11"
license = {text = "Apache-2.0"}
authors = [{name = "Aldrich K. Wooden, Sr."}]

dependencies = [
    "pydantic>=2.0",
    "pyyaml>=6.0",
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "jinja2>=3.1.0",
    "httpx>=0.25.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "ruff>=0.1.0",
    "black>=23.0",
    "mypy>=1.0",
]

[project.scripts]
forge = "forge.cli.main:main"

[tool.setuptools.packages.find]
include = ["forge*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.black]
line-length = 100
target-version = ["py311"]

[tool.mypy]
python_version = "3.11"
strict = false
warn_return_any = true
```

### Step 0.4 — Verify install

```bash
pip install -e ".[dev]" --break-system-packages
forge --help
# Expected: usage message from forge.cli.main:main
```

**If this fails**: The most likely cause is a missing `__init__.py` or
a broken import in one of the forge subpackages. Fix imports before
proceeding. Common fixes:

```bash
# Ensure every directory has __init__.py
touch forge/__init__.py
touch forge/cli/__init__.py
touch forge/compiler/__init__.py
touch forge/substrate/__init__.py
touch forge/substrate/zuup_auth/__init__.py
touch forge/substrate/zuup_audit/__init__.py
touch forge/substrate/zuup_observe/__init__.py
touch forge/substrate/zuup_gateway/__init__.py
```

### Step 0.5 — Commit checkpoint

```bash
git add -A
git commit -m "fix: restore package hierarchy, remove flat file dump"
git push origin main
```

**EXIT CRITERIA PHASE 0**:
- [ ] `pip install -e .` succeeds
- [ ] `forge --help` prints usage
- [ ] `python -c "from forge.compiler.spec_schema import PlatformSpec; print('OK')"` prints OK
- [ ] No files at repo root that belong in forge/ or specs/

---

## PHASE 1: COMPILER PRODUCES RUNNABLE CODE (8-16 hours)

**Goal**: `forge compile specs/aureon.platform.yaml` → directory of working Python.

### Step 1.1 — Fix forge/compiler/spec_schema.py

Audit the Pydantic schema. Ensure every field has a default or is
marked required. Key fixes:

```python
# forge/compiler/spec_schema.py
# Verify these enums exist and match the YAML spec:

from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional

class DataClassification(str, Enum):
    PUBLIC = "PUBLIC"
    CUI = "CUI"
    SECRET = "SECRET"
    TOP_SECRET = "TOP_SECRET"

class ComplianceFramework(str, Enum):
    FAR = "FAR"
    DFARS = "DFARS"
    CMMC_L1 = "CMMC_L1"
    CMMC_L2 = "CMMC_L2"
    FedRAMP_Moderate = "FedRAMP_Moderate"
    FedRAMP_High = "FedRAMP_High"
    HIPAA = "HIPAA"
    CJIS = "CJIS"

# ... rest of schema must parse aureon.platform.yaml without errors
```

**Validation test** (run after editing):

```bash
python -c "
from forge.compiler.parser import load_spec
spec = load_spec('specs/aureon.platform.yaml')
print(f'Platform: {spec.platform.name}')
print(f'Entities: {[e.name for e in spec.entities]}')
print(f'Routes: {len(spec.api.routes)}')
"
# Expected:
# Platform: aureon
# Entities: ['Opportunity', 'Vendor', 'OpportunityMatch']
# Routes: 6
```

### Step 1.2 — Fix forge/compiler/schema_gen.py

The schema generator must produce **executable** SQLite SQL.
No Postgres-only syntax (SERIAL, UUID, jsonb). SQLite-first.

Key requirements:
- `generate_sqlite_migration(spec)` → valid SQLite CREATE TABLE statements
- Every entity → one table
- `string[]` fields → TEXT (JSON array stored as string)
- `vector` fields → BLOB (placeholder, no pgvector)
- `datetime` fields → TEXT (ISO 8601)
- `decimal` fields → REAL
- `soft_delete` → adds `deleted_at TEXT` column
- `audit_all` → adds `created_at TEXT, updated_at TEXT` columns
- Includes `audit_log` table with hash-chain columns

**Validation test**:

```bash
python -c "
from forge.compiler.parser import load_spec
from forge.compiler.schema_gen import generate_sqlite_migration
spec = load_spec('specs/aureon.platform.yaml')
sql = generate_sqlite_migration(spec)
print(sql[:500])
import sqlite3
conn = sqlite3.connect(':memory:')
conn.executescript(sql)
tables = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()
print(f'Tables created: {[t[0] for t in tables]}')
conn.close()
"
# Expected: Tables created: ['opportunity', 'vendor', 'opportunity_match', 'audit_log']
```

### Step 1.3 — Fix forge/compiler/api_gen.py

The API generator must produce **runnable** FastAPI code. No TODO stubs.

Requirements:
- `generate_fastapi_app(spec)` → app.py with middleware, health routes
- `generate_fastapi_routes(spec)` → routes/__init__.py with CRUD endpoints
- Every route returns a real response (even if it's `{"status": "not_implemented"}`)
- Imports must resolve against the generated directory structure
- Generated app must import from sibling modules, NOT from forge.*

**Key**: Generated code runs standalone. It does NOT import from `forge`.
It uses only stdlib + fastapi + pydantic + sqlite3.

```python
# Example of what generate_fastapi_app(spec) should produce:
# --- platforms/aureon/app.py ---
"""Aureon™ — Auto-generated by Zuup Forge v0.1.0"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Aureon™",
    version="0.1.0",
    description="Planetary-Scale Procurement Substrate",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
async def health():
    return {"status": "ok", "platform": "aureon", "version": "0.1.0"}

@app.get("/ready")
async def ready():
    return {"status": "ready"}

# Import and include generated routes
from .routes import router
app.include_router(router, prefix="/api/v1")
```

**Validation test**:

```bash
# Generate the platform
forge compile specs/aureon.platform.yaml

# Verify files exist
ls platforms/aureon/
# Expected: app.py, models/, routes/, migrations/, services/, config/, tests/, __init__.py

# Run the generated app
cd platforms/aureon
python -m uvicorn app:app --port 8000 &
sleep 2
curl http://localhost:8000/health
# Expected: {"status":"ok","platform":"aureon","version":"0.1.0"}
curl http://localhost:8000/api/v1/opportunities
# Expected: {"items":[],"total":0} or similar
kill %1
cd ../..
```

### Step 1.4 — Generate working Pydantic models

`forge/compiler/api_gen.py` (or a separate `model_gen.py`) must produce
Pydantic models that match the spec entities:

```python
# Example output: platforms/aureon/models/__init__.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class OpportunityBase(BaseModel):
    notice_id: str
    title: str
    agency: str
    sub_agency: Optional[str] = None
    naics_codes: list[str] = Field(default_factory=list)
    set_asides: list[str] = Field(default_factory=list)
    response_deadline: Optional[datetime] = None
    estimated_value: Optional[float] = None
    place_of_performance: Optional[str] = None
    solicitation_type: str = ""
    full_text: str = ""
    source_url: str = ""

class OpportunityCreate(OpportunityBase):
    pass

class Opportunity(OpportunityBase):
    id: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True
```

### Step 1.5 — Generate working routes with SQLite CRUD

Each route must perform real SQLite operations:

```python
# Example output: platforms/aureon/routes/__init__.py
import sqlite3
import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from ..models import OpportunityCreate, Opportunity

router = APIRouter()
DB_PATH = "aureon.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@router.get("/opportunities")
async def list_opportunities(limit: int = 50, offset: int = 0):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM opportunity WHERE deleted_at IS NULL LIMIT ? OFFSET ?",
        (limit, offset)
    ).fetchall()
    total = db.execute(
        "SELECT COUNT(*) FROM opportunity WHERE deleted_at IS NULL"
    ).fetchone()[0]
    db.close()
    return {"items": [dict(r) for r in rows], "total": total}

@router.post("/opportunities", status_code=201)
async def create_opportunity(opp: OpportunityCreate):
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    opp_id = str(uuid.uuid4())
    db.execute(
        """INSERT INTO opportunity
           (id, notice_id, title, agency, sub_agency, naics_codes,
            set_asides, response_deadline, estimated_value,
            place_of_performance, solicitation_type, full_text,
            source_url, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (opp_id, opp.notice_id, opp.title, opp.agency, opp.sub_agency,
         json.dumps(opp.naics_codes), json.dumps(opp.set_asides),
         opp.response_deadline.isoformat() if opp.response_deadline else None,
         opp.estimated_value, opp.place_of_performance,
         opp.solicitation_type, opp.full_text, opp.source_url, now, now)
    )
    db.commit()
    db.close()
    return {"id": opp_id, "created_at": now}

# ... GET /opportunities/{id}, PUT, DELETE, /vendors, /vendors/{id}, /search
```

### Step 1.6 — Generate auto-initializing DB

The generated app.py must auto-create tables on startup:

```python
# In platforms/aureon/app.py, add startup event:
import sqlite3
from pathlib import Path

@app.on_event("startup")
async def startup():
    migration_path = Path(__file__).parent / "migrations" / "001_initial_sqlite.sql"
    if migration_path.exists():
        conn = sqlite3.connect("aureon.db")
        conn.executescript(migration_path.read_text())
        conn.close()
```

### Step 1.7 — Generate tests that pass

```python
# platforms/aureon/tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from ..app import app

client = TestClient(app)

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

def test_create_and_list_opportunities():
    resp = client.post("/api/v1/opportunities", json={
        "notice_id": "TEST-001",
        "title": "Test Opportunity",
        "agency": "DoD",
        "solicitation_type": "RFP",
    })
    assert resp.status_code == 201
    opp_id = resp.json()["id"]

    resp = client.get("/api/v1/opportunities")
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1
```

### Step 1.8 — Write compiler tests

```bash
# tests/test_compiler.py
mkdir -p tests
```

```python
# tests/test_compiler.py
"""End-to-end compiler tests."""
import shutil
import sqlite3
from pathlib import Path
import pytest
from forge.compiler.parser import load_spec
from forge.compiler import compile_platform

SPEC_PATH = Path("specs/aureon.platform.yaml")
OUTPUT_DIR = Path("test_output/aureon")

@pytest.fixture(autouse=True)
def clean_output():
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    yield
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

def test_spec_loads():
    spec = load_spec(SPEC_PATH)
    assert spec.platform.name == "aureon"
    assert len(spec.entities) == 3

def test_compile_produces_files():
    spec = load_spec(SPEC_PATH)
    result = compile_platform(spec, OUTPUT_DIR)
    assert len(result.files_generated) >= 8
    assert (OUTPUT_DIR / "app.py").exists()
    assert (OUTPUT_DIR / "models" / "__init__.py").exists()
    assert (OUTPUT_DIR / "routes" / "__init__.py").exists()
    assert (OUTPUT_DIR / "migrations" / "001_initial_sqlite.sql").exists()

def test_generated_sql_executes():
    spec = load_spec(SPEC_PATH)
    compile_platform(spec, OUTPUT_DIR)
    sql = (OUTPUT_DIR / "migrations" / "001_initial_sqlite.sql").read_text()
    conn = sqlite3.connect(":memory:")
    conn.executescript(sql)
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    assert "opportunity" in tables
    assert "vendor" in tables
    conn.close()

def test_generated_app_is_valid_python():
    spec = load_spec(SPEC_PATH)
    compile_platform(spec, OUTPUT_DIR)
    app_code = (OUTPUT_DIR / "app.py").read_text()
    compile(app_code, str(OUTPUT_DIR / "app.py"), "exec")  # Syntax check
```

### Step 1.9 — Run full test suite

```bash
pytest tests/ -v --tb=short
# Expected: all green
```

### Step 1.10 — Commit Phase 1

```bash
git add -A
git commit -m "feat: compiler produces runnable Aureon platform with SQLite CRUD"
git push origin main
```

**EXIT CRITERIA PHASE 1**:
- [ ] `forge compile specs/aureon.platform.yaml` produces platforms/aureon/
- [ ] Generated SQL executes against SQLite without errors
- [ ] Generated app starts with `uvicorn platforms.aureon.app:app`
- [ ] `curl /health` returns 200
- [ ] `curl /api/v1/opportunities` returns `{"items":[],"total":0}`
- [ ] POST to /api/v1/opportunities creates a record
- [ ] Generated tests pass with pytest
- [ ] Compiler tests in tests/ pass

---

## PHASE 2: CI + HONEST FRONTEND (4-6 hours)

**Goal**: Green CI badge. Honest status dashboard on Vercel.

### Step 2.1 — Fix GitHub Actions CI

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Lint
        run: ruff check forge/ tests/

      - name: Type check
        run: mypy forge/ --ignore-missing-imports
        continue-on-error: true

      - name: Test
        run: pytest tests/ -v --tb=short --cov=forge --cov-report=term-missing

      - name: Smoke test - compile Aureon
        run: |
          forge compile specs/aureon.platform.yaml
          ls platforms/aureon/app.py
          python -c "compile(open('platforms/aureon/app.py').read(), 'app.py', 'exec')"
```

### Step 2.2 — Build honest frontend

Replace the broken "retro terminal" dashboard with a simple, honest
status page. Single HTML file, no framework.

```
frontend/index.html   — status page + demo link
frontend/style.css    — minimal styling
api/index.py          — Vercel serverless: /api/health, /api/status
vercel.json           — routing config
```

**frontend/index.html** requirements:
- Show project name, one-line description, current TRL (3)
- Link to GitHub repo
- "Demo" button that shows: YAML spec → generated API (static or live)
- Status indicators that hit /api/status (real data, not "Checking...")
- Waitlist email capture (store in a simple JSON file or use Formspree free tier)
- No fake metrics, no aspirational claims

### Step 2.3 — Fix Vercel deployment

```json
// vercel.json
{
  "buildCommand": "pip install -e . && forge compile specs/aureon.platform.yaml",
  "outputDirectory": "frontend",
  "routes": [
    { "src": "/api/(.*)", "dest": "/api/index.py" },
    { "src": "/(.*)", "dest": "/frontend/$1" }
  ],
  "functions": {
    "api/index.py": {
      "runtime": "@vercel/python@4.3.1"
    }
  }
}
```

```python
# api/index.py
"""Vercel serverless function — Zuup Forge status API."""
from http.server import BaseHTTPRequestHandler
import json
from datetime import datetime, timezone

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/health":
            self._json(200, {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()})
        elif self.path == "/api/status":
            self._json(200, {
                "forge_version": "0.1.0",
                "trl": 3,
                "platforms_defined": 1,
                "platforms_functional": 0,
                "compiler_status": "operational",
                "last_compile_test": "see CI badge",
                "next_milestone": "Gate 1 — Technical Credibility",
            })
        else:
            self._json(404, {"error": "not found"})

    def _json(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
```

### Step 2.4 — Remove dead files

```bash
# Remove Render config (we're using Vercel)
rm -f render.yaml

# Remove old dashboard assets if they weren't already deleted
rm -f forge.css forge.js index.html

# Remove Dockerfile (premature)
rm -f Dockerfile

# Remove redundant files
rm -f requirements.txt  # pyproject.toml is source of truth
rm -f uv.lock          # not using uv in CI
```

### Step 2.5 — Update README.md to be honest

```markdown
# Zuup Forge — Declarative Platform Compiler

> YAML in → compliance-ready API out.

## Status: TRL 3 — Proof of Concept

[![CI](https://github.com/khaaliswooden-max/zuup-forge/actions/workflows/ci.yml/badge.svg)](https://github.com/khaaliswooden-max/zuup-forge/actions)

Zuup Forge reads a YAML platform specification and generates a complete
Python codebase: SQLite migrations, Pydantic models, FastAPI routes,
audit logging, and tests.

**Currently generating**: Aureon (federal procurement opportunity matching)

### Quick Start

    pip install -e ".[dev]"
    forge compile specs/aureon.platform.yaml
    cd platforms/aureon
    uvicorn app:app --reload

### What Works Today

- [x] YAML spec parsing with Pydantic validation
- [x] SQLite migration generation
- [x] FastAPI route generation with CRUD
- [x] Audit hash-chain substrate
- [x] Auth middleware (JWT/RBAC)
- [ ] SAM.gov API integration
- [ ] Preference collection
- [ ] DPO training loop

### License

Apache 2.0
```

### Step 2.6 — Commit + deploy

```bash
git add -A
git commit -m "feat: honest frontend, working CI, clean README"
git push origin main
# Vercel auto-deploys from main
```

**EXIT CRITERIA PHASE 2**:
- [ ] GitHub Actions CI runs and passes (green badge)
- [ ] https://zuup-forge.vercel.app loads and shows real status
- [ ] /api/health returns 200 with timestamp
- [ ] /api/status returns accurate TRL and milestone data
- [ ] README has CI badge and honest feature checklist
- [ ] No dead files (Dockerfile, render.yaml, requirements.txt)

---

## PHASE 3: REAL DATA — SAM.GOV INTEGRATION (4-8 hours)

**Goal**: Aureon has 100+ real federal opportunities in its database.

### Step 3.1 — SAM.gov API client

```python
# forge/integrations/sam_gov.py
"""SAM.gov Opportunities API client.

API docs: https://open.gsa.gov/api/get-opportunities/public/
Free tier: 10,000 requests/day, no API key required for public data.
"""
import httpx
from typing import Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

SAM_BASE = "https://api.sam.gov/opportunities/v2/search"

class SAMOpportunity(BaseModel):
    notice_id: str
    title: str
    agency: Optional[str] = None
    sub_agency: Optional[str] = None
    naics_codes: list[str] = []
    set_asides: list[str] = []
    response_deadline: Optional[datetime] = None
    estimated_value: Optional[float] = None
    place_of_performance: Optional[str] = None
    solicitation_type: Optional[str] = None
    full_text: str = ""
    source_url: str = ""

async def fetch_opportunities(
    keyword: str = "",
    posted_from: Optional[str] = None,
    posted_to: Optional[str] = None,
    limit: int = 100,
    api_key: Optional[str] = None,
) -> list[SAMOpportunity]:
    """Fetch opportunities from SAM.gov public API."""
    if not posted_from:
        posted_from = (datetime.now() - timedelta(days=30)).strftime("%m/%d/%Y")
    if not posted_to:
        posted_to = datetime.now().strftime("%m/%d/%Y")

    params = {
        "postedFrom": posted_from,
        "postedTo": posted_to,
        "limit": limit,
        "offset": 0,
    }
    if keyword:
        params["keyword"] = keyword
    if api_key:
        params["api_key"] = api_key

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(SAM_BASE, params=params)
        resp.raise_for_status()
        data = resp.json()

    results = []
    for opp in data.get("opportunitiesData", []):
        results.append(SAMOpportunity(
            notice_id=opp.get("noticeId", ""),
            title=opp.get("title", ""),
            agency=opp.get("fullParentPathName", "").split(".")[0] if opp.get("fullParentPathName") else None,
            sub_agency=opp.get("fullParentPathName", "").split(".")[-1] if opp.get("fullParentPathName") else None,
            solicitation_type=opp.get("type", ""),
            response_deadline=_parse_date(opp.get("responseDeadLine")),
            source_url=f"https://sam.gov/opp/{opp.get('noticeId', '')}/view",
            full_text=opp.get("description", "")[:10000],
        ))
    return results

def _parse_date(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
```

### Step 3.2 — Seed script

```python
# scripts/seed_sam_gov.py
"""Seed Aureon database with real SAM.gov opportunities."""
import asyncio
import sqlite3
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Ensure forge is importable
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from forge.integrations.sam_gov import fetch_opportunities

DB_PATH = "platforms/aureon/aureon.db"
MIGRATION_PATH = "platforms/aureon/migrations/001_initial_sqlite.sql"

async def seed():
    # Ensure DB exists with schema
    conn = sqlite3.connect(DB_PATH)
    if Path(MIGRATION_PATH).exists():
        conn.executescript(Path(MIGRATION_PATH).read_text())

    # Fetch from SAM.gov
    keywords = ["artificial intelligence", "cybersecurity", "data analytics",
                 "cloud services", "IT modernization"]

    total = 0
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
                            source_url, created_at, updated_at)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (str(uuid.uuid4()), opp.notice_id, opp.title,
                         opp.agency, opp.sub_agency,
                         json.dumps(opp.naics_codes), json.dumps(opp.set_asides),
                         opp.response_deadline.isoformat() if opp.response_deadline else None,
                         opp.estimated_value, opp.place_of_performance,
                         opp.solicitation_type, opp.full_text, opp.source_url,
                         now, now)
                    )
                    total += 1
                except sqlite3.IntegrityError:
                    pass  # Duplicate notice_id
            print(f"  → {len(opps)} fetched")
        except Exception as e:
            print(f"  → Error: {e}")

    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM opportunity").fetchone()[0]
    conn.close()
    print(f"\nTotal opportunities in DB: {count}")

if __name__ == "__main__":
    asyncio.run(seed())
```

### Step 3.3 — Run seed

```bash
# First, compile the platform (creates migrations)
forge compile specs/aureon.platform.yaml

# Then seed
python scripts/seed_sam_gov.py
# Expected: Total opportunities in DB: 100+

# Verify via API
cd platforms/aureon
uvicorn app:app --port 8000 &
sleep 2
curl "http://localhost:8000/api/v1/opportunities?limit=5" | python -m json.tool
kill %1
cd ../..
```

### Step 3.4 — Add SAM.gov integration test

```python
# tests/test_sam_gov.py
import pytest
from forge.integrations.sam_gov import fetch_opportunities

@pytest.mark.asyncio
async def test_sam_gov_fetch():
    """Test SAM.gov API returns results (requires network)."""
    opps = await fetch_opportunities(keyword="cybersecurity", limit=5)
    assert len(opps) > 0
    assert opps[0].notice_id != ""
    assert opps[0].title != ""
```

### Step 3.5 — Commit

```bash
git add -A
git commit -m "feat: SAM.gov integration, seed script, 100+ real opportunities"
git push origin main
```

**EXIT CRITERIA PHASE 3**:
- [ ] SAM.gov client fetches real data without API key
- [ ] Seed script populates 100+ opportunities
- [ ] API returns real opportunity data with actual titles and agencies
- [ ] Integration test passes (with network)

---

## PHASE 4: LANDING PAGE + WAITLIST (2-4 hours)

**Goal**: Public-facing page that captures interest.

### Step 4.1 — Build landing page

Replace `frontend/index.html` with a conversion-focused page:

Requirements:
- Headline: "YAML in → Government-Ready API Out"
- One-paragraph explanation (from desired state pitch variants)
- 90-second demo video embed (or animated GIF of terminal)
- Email capture form (Formspree free tier: formspree.io)
- Link to GitHub repo
- Honest TRL disclosure at bottom
- Mobile responsive, no JavaScript framework

### Step 4.2 — Set up email capture

```html
<!-- In frontend/index.html -->
<form action="https://formspree.io/f/{YOUR_FORM_ID}" method="POST">
  <input type="email" name="email" placeholder="your@email.com" required>
  <input type="hidden" name="_subject" value="Zuup Forge Waitlist">
  <button type="submit">Join Waitlist</button>
</form>
```

Sign up at formspree.io (free: 50 submissions/month).

### Step 4.3 — Record demo

```bash
# Install asciinema (free)
pip install asciinema --break-system-packages

# Record the demo
asciinema rec demo.cast -c "bash -c '
echo \"$ cat specs/aureon.platform.yaml | head -20\"
head -20 specs/aureon.platform.yaml
echo \"\"
echo \"$ forge compile specs/aureon.platform.yaml\"
forge compile specs/aureon.platform.yaml
echo \"\"
echo \"$ cd platforms/aureon && uvicorn app:app --port 8000\"
cd platforms/aureon && timeout 5 uvicorn app:app --port 8000 || true
echo \"\"
echo \"$ curl http://localhost:8000/api/v1/opportunities?limit=3\"
curl -s http://localhost:8000/api/v1/opportunities?limit=3 | python -m json.tool
'"

# Upload to asciinema.org (free, embeddable)
asciinema upload demo.cast
```

### Step 4.4 — Commit

```bash
git add -A
git commit -m "feat: landing page with waitlist, demo recording"
git push origin main
```

**EXIT CRITERIA PHASE 4**:
- [ ] Landing page loads on zuup-forge.vercel.app
- [ ] Email form submits to Formspree
- [ ] Demo video/recording embedded or linked
- [ ] Page is mobile responsive
- [ ] No aspirational claims — TRL 3 disclosed

---

## PHASE 5: AUDIT + AUTH INTEGRATION (4-6 hours)

**Goal**: Generated platforms include working audit trail and auth.

### Step 5.1 — Wire audit into generated routes

The compiler should inject audit logging into every generated route:

```python
# In generated routes, every write operation logs to audit:
from ..services.audit import log_audit_event

@router.post("/opportunities", status_code=201)
async def create_opportunity(opp: OpportunityCreate):
    # ... create logic ...
    log_audit_event(
        platform="aureon",
        action="CREATE_OPPORTUNITY",
        principal_id="anonymous",  # TODO: extract from JWT
        entity_type="opportunity",
        entity_id=opp_id,
        payload=opp.model_dump(),
    )
    return {"id": opp_id}
```

### Step 5.2 — Wire auth middleware

```python
# Generated app.py includes optional auth:
from forge.substrate.zuup_auth.middleware import optional_auth_middleware

# Applied per-route, not globally (allows /health without auth)
```

### Step 5.3 — Test audit chain integrity

```python
# tests/test_audit.py
from forge.substrate.zuup_audit import AuditEntry, SQLiteAuditStore

def test_audit_chain_integrity():
    store = SQLiteAuditStore(":memory:")
    for i in range(10):
        store.append(AuditEntry(
            platform="test",
            action=f"action_{i}",
            principal_id="tester",
            entity_type="test",
            entity_id=str(i),
            payload_hash=f"hash_{i}",
        ))
    result = store.verify_chain()
    assert result.valid
    assert result.entries_checked == 10
```

**EXIT CRITERIA PHASE 5**:
- [ ] Every generated write route logs to audit chain
- [ ] Audit chain verification passes (hash linkage intact)
- [ ] Auth middleware validates JWT when present, passes through when absent
- [ ] Generated tests include audit and auth tests

---

## PHASE 6: DEMO-READY STATE (2-4 hours)

**Goal**: 2-minute live demo from cold start.

### Step 6.1 — Create demo script

```bash
# scripts/demo.sh
#!/bin/bash
set -e

echo "=== Zuup Forge Demo ==="
echo ""
echo "Step 1: Show the spec"
echo "---"
head -30 specs/aureon.platform.yaml
echo ""
read -p "Press Enter to compile..."

echo "Step 2: Compile"
echo "---"
forge compile specs/aureon.platform.yaml
echo ""

echo "Step 3: Seed with real SAM.gov data"
echo "---"
python scripts/seed_sam_gov.py
echo ""

echo "Step 4: Start the API"
echo "---"
cd platforms/aureon
uvicorn app:app --port 8000 &
SERVER_PID=$!
sleep 2

echo ""
echo "Step 5: Query real opportunities"
echo "---"
curl -s http://localhost:8000/api/v1/opportunities?limit=3 | python -m json.tool
echo ""

echo "Step 6: Verify audit trail"
echo "---"
curl -s http://localhost:8000/api/v1/audit/verify | python -m json.tool

kill $SERVER_PID
echo ""
echo "=== Demo complete. Spec → Running API in ~90 seconds. ==="
```

### Step 6.2 — Add Makefile shortcuts

```makefile
# Makefile
.PHONY: install test lint compile demo seed clean

install:
	pip install -e ".[dev]" --break-system-packages

test:
	pytest tests/ -v --tb=short

lint:
	ruff check forge/ tests/
	black --check forge/ tests/

compile:
	forge compile specs/aureon.platform.yaml

seed: compile
	python scripts/seed_sam_gov.py

demo: compile seed
	cd platforms/aureon && uvicorn app:app --reload --port 8000

clean:
	rm -rf platforms/ *.db test_output/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

smoke: install compile test
	@echo "✓ Smoke test passed"
```

### Step 6.3 — Final commit

```bash
git add -A
git commit -m "feat: demo-ready state, Makefile, scripts"
git push origin main
```

**EXIT CRITERIA PHASE 6**:
- [ ] `make smoke` passes (install → compile → test)
- [ ] `make demo` starts a working API with real data
- [ ] Demo completes in under 2 minutes
- [ ] All tests green

---

## VERIFICATION MATRIX

Run this checklist after all phases. Every box must be checked.

### Gate 1: Technical Credibility

| # | Criterion | Command | Expected |
|---|-----------|---------|----------|
| 1 | Package installs | `pip install -e .` | Exit 0 |
| 2 | CLI works | `forge --help` | Usage text |
| 3 | Spec parses | `forge compile specs/aureon.platform.yaml` | "Compiled aureon: N files" |
| 4 | SQL executes | `sqlite3 :memory: < platforms/aureon/migrations/001_initial_sqlite.sql` | Exit 0 |
| 5 | App starts | `uvicorn platforms.aureon.app:app` | "Uvicorn running" |
| 6 | Health check | `curl localhost:8000/health` | `{"status":"ok"}` |
| 7 | CRUD works | POST + GET /api/v1/opportunities | 201 then 200 |
| 8 | Tests pass | `pytest tests/ -v` | All green |
| 9 | CI passes | Check GitHub Actions | Green badge |
| 10 | Demo runs | `bash scripts/demo.sh` | Completes in < 120s |

### Gate 2: Market Credibility (post-technical, track separately)

| # | Criterion | Target | Status |
|---|-----------|--------|--------|
| 1 | Real data in DB | 500+ SAM.gov opportunities | |
| 2 | Landing page live | zuup-forge.vercel.app | |
| 3 | Waitlist signups | ≥ 50 | |
| 4 | User interviews | ≥ 5 with target persona | |
| 5 | Demo video | Published, < 2 min | |

---

## ESTIMATED TIMELINE

| Phase | Hours | Cumulative | Blocked By |
|-------|-------|-----------|------------|
| 0: Triage | 0.5 | 0.5 | Nothing |
| 1: Compiler | 8-16 | 8.5-16.5 | Phase 0 |
| 2: CI + Frontend | 4-6 | 12.5-22.5 | Phase 1 |
| 3: SAM.gov | 4-8 | 16.5-30.5 | Phase 1 |
| 4: Landing Page | 2-4 | 18.5-34.5 | Phase 2 |
| 5: Audit + Auth | 4-6 | 22.5-40.5 | Phase 1 |
| 6: Demo Ready | 2-4 | 24.5-44.5 | All above |

**Total**: 24-44 hours of focused work → Gate 1 complete.

Phases 2, 3, 4, 5 can run in parallel after Phase 1.

---

## CURSOR-SPECIFIC INSTRUCTIONS

### How to use this plan in Cursor

1. Open zuup-forge/ in Cursor
2. Ensure `.cursorrules` is at repo root (Cursor reads it automatically)
3. Work through phases sequentially
4. After each step, run the validation test listed
5. If a test fails, fix it before moving to the next step
6. Commit at the end of each phase (not more often)

### Cursor Composer prompts (copy-paste these)

**Phase 0**: "Fix the repo structure per .cursorrules. Move forge/ package
from zuup-forge/forge/ to root. Delete all flat Python files at root.
Create .gitignore. Fix pyproject.toml. Verify `pip install -e .` works."

**Phase 1**: "Make the compiler produce runnable code. When I run
`forge compile specs/aureon.platform.yaml`, it should create
platforms/aureon/ with app.py, models/, routes/, migrations/, and tests/.
The generated app must start with uvicorn and serve real SQLite CRUD
on /api/v1/opportunities and /api/v1/vendors. No TODO stubs."

**Phase 2**: "Set up GitHub Actions CI at .github/workflows/ci.yml that
runs lint, test, and a smoke compile. Create an honest frontend status
page in frontend/. Fix vercel.json to serve frontend/ and api/index.py."

**Phase 3**: "Create forge/integrations/sam_gov.py that fetches from
SAM.gov public API. Create scripts/seed_sam_gov.py that populates 100+
real opportunities into the Aureon SQLite database."

**Phase 5**: "Wire the audit hash-chain from forge/substrate/zuup_audit/
into every generated write route. Ensure audit chain verification works."

**Phase 6**: "Create scripts/demo.sh, update Makefile, ensure
`make smoke` passes end-to-end."
