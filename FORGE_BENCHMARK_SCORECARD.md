# Zuup Forge — Development Benchmark Scorecard

**First Run**: 2026-02-10
**Score**: 89/89 (100%)
**Status**: VERIFIED — all benchmarks pass against current codebase
**Runtime**: 3.44s

---

## Summary by Category

| Category | Tests | Pass | Fail | Score | Description |
|----------|-------|------|------|-------|-------------|
| **B0** Install & CLI | 4 | 4 | 0 | 100% | Package installs, CLI works |
| **B1** Spec Parsing | 21 | 21 | 0 | 100% | DSL coverage, validation, error cases |
| **B2** Code Generation | 17 | 17 | 0 | 100% | Compiler output correctness |
| **B3** Code Validity | 10 | 10 | 0 | 100% | Generated code is syntactically valid |
| **B4** Substrate Primitives | 19 | 19 | 0 | 100% | Audit, auth, AI, observe modules |
| **B5** Multi-Domain | 7 | 7 | 0 | 100% | Cross-domain compilation |
| **B6** End-to-End | 5 | 5 | 0 | 100% | Full YAML → platform pipeline |
| **B7** Error Handling | 6 | 6 | 0 | 100% | Graceful failure on bad inputs |
| **Total** | **89** | **89** | **0** | **100%** | |

---

## Grounding Disclaimer

100% pass rate does **not** mean Forge is production-ready. It means:

- The compiler installs, parses specs, and generates syntactically valid output.
- Substrate primitives (audit chain, RBAC, guardrails, metrics) work in isolation.
- The test suite covers what exists today, not what should exist tomorrow.

### What these benchmarks DO NOT test

| Gap | Why it matters | Blocked by |
|-----|---------------|------------|
| Generated server actually starts | Core functionality | Phase 1 (wire DB + uvicorn) |
| HTTP requests return correct data | API correctness | Phase 1 |
| Database migrations execute | Data layer | Phase 1 |
| Auth middleware blocks unauthorized | Security | Phase 2 |
| Audit middleware logs requests | Compliance | Phase 2 |
| Rate limiting enforced | Production readiness | Phase 2 |
| Multi-platform deployment | Infra | Phase 3 |
| AI model integration | LLM features | Phase 3 |
| Preference collection works | RSI flywheel | Phase 3 |
| Load/stress testing | Performance | Phase 4 |

### Future benchmark categories to add

- **B8**: Generated Server Runtime (server starts, /health returns 200)
- **B9**: Database Layer (migrations run, CRUD works)
- **B10**: Auth Middleware Integration (JWT validation in HTTP context)
- **B11**: Audit Middleware Integration (requests logged automatically)
- **B12**: Performance (compilation time, generated server latency)
- **B13**: Compliance Evidence (audit exports, data residency checks)

---

## Specs Used

| Spec | Domain | Entities | Routes | Compliance |
|------|--------|----------|--------|------------|
| `aureon.platform.yaml` | Federal procurement | 3 | 6 | FAR, DFARS, CMMC L2, FedRAMP Mod |
| `civium.platform.yaml` | Halal compliance | 3 | 5 | JAKIM, MUI, GCC, ISO 27001 |
| `minspec.platform.yaml` | Testing (minimal) | 1 | 1 | None |

---

## Run Command

```bash
pytest tests/benchmarks/test_forge_benchmarks.py -v --tb=short
```

For score summary only:
```bash
pytest tests/benchmarks/test_forge_benchmarks.py -q
```

---

## Test Index

### B0 — Install & CLI (4)
- `b0_01` forge importable with __version__
- `b0_02` CLI entry point responds to --help
- `b0_03` Subcommands init/generate/dev/eval registered
- `b0_04` Version string is valid semver

### B1 — Spec Parsing (21)
- `b1_01–03` Load aureon, civium, minspec
- `b1_04–05` Entity counts match spec
- `b1_06–07` Compliance frameworks and data classification parsed
- `b1_08–09` PII and searchable field detection
- `b1_10–11` GovCloud requirement logic
- `b1_12–13` AI models and guardrails parsed
- `b1_14–15` API routes and relations validated
- `b1_16–19` Error cases: invalid name, empty file, missing file, bad relation
- `b1_20` All FieldType enums have PG type mapping
- `b1_21` load_all_specs finds all specs in directory

### B2 — Code Generation (17)
- `b2_01–03` File count (11) for each spec
- `b2_04–05` PG and SQLite migrations have CREATE TABLE
- `b2_06` Pydantic models generated
- `b2_07` Routes include auth references
- `b2_08` app.py has FastAPI
- `b2_09` Dockerfile generated
- `b2_10` Config includes platform name
- `b2_11` platform.spec.json emitted
- `b2_12` Generated tests include test_health
- `b2_13–14` PG migration has audit table and indexes
- `b2_15` Soft delete columns present
- `b2_16` PII encryption markers present
- `b2_17` CompileResult.summary() correct

### B3 — Generated Code Validity (10)
- `b3_01–06` All generated .py files parse via ast.parse (aureon)
- `b3_07–08` Models valid for civium and minspec
- `b3_09–10` SQL has balanced parentheses

### B4 — Substrate Primitives (19)
- `b4_01–04` Audit: hash determinism, store CRUD, chain linking, tamper detection
- `b4_05–09` Auth: role check, admin perms, viewer restrictions, API keys, system principal
- `b4_10–15` AI: SSN block, clean pass, CC block, prompt registry, hash stability, unknown tool
- `b4_16–19` Observe: logger, counter, prometheus export, span timing

### B5 — Multi-Domain (7)
- `b5_01` All specs compile to 11 files each
- `b5_02–03` Civium routes and compliance in output
- `b5_04` Minspec compiles without AI config
- `b5_05` Different specs produce different output
- `b5_06–07` Halal frameworks and PII detection

### B6 — End-to-End (5)
- `b6_01` CLI-driven compilation produces 11 files
- `b6_02` Generated app.py has AST-parseable assignments
- `b6_03` platform.spec.json roundtrips through PlatformSpec
- `b6_04` Compilation is idempotent
- `b6_05` All specs compile to valid Python

### B7 — Error Handling (6)
- `b7_01` Unknown field type rejected
- `b7_02` Duplicate field names handled gracefully
- `b7_03` Read-only output directory raises
- `b7_04` Max length guardrail triggers
- `b7_05` Empty audit query returns []
- `b7_06` Empty chain verification returns valid=True
