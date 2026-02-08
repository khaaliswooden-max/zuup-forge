# Zuup Forge — Declarative Platform Compiler

> YAML in → compliance-ready API out.

## Status: TRL 3 — Proof of Concept

[![CI](https://github.com/khaaliswooden-max/zuup-forge/actions/workflows/ci.yml/badge.svg)](https://github.com/khaaliswooden-max/zuup-forge/actions)

Zuup Forge reads a YAML platform specification and generates a complete
Python codebase: SQLite migrations, Pydantic models, FastAPI routes,
audit logging, and tests.

**Currently generating**: Aureon (federal procurement opportunity matching)

### Quick Start

```bash
pip install -e ".[dev]"
python -m forge.cli.main compile specs/aureon.platform.yaml
cd platforms/aureon
python -m uvicorn app:app --reload
```

Or from repo root (recommended):

```bash
pip install -e ".[dev]"
forge compile specs/aureon.platform.yaml
python -m uvicorn platforms.aureon.app:app --port 8000
```

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
