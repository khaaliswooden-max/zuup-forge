# Zuup Forge — Phased Cursor Execution Plan

> **Repo**: `khaaliswooden-max/zuup-forge`
> **North Star**: AI platform factory → production platforms → RSI/RSF flywheel → self-building

---

## Phase 0: Bootstrap (Day 1)

```bash
git clone https://github.com/khaaliswooden-max/zuup-forge.git && cd zuup-forge
pip install -e ".[dev]" --break-system-packages
make smoke   # Parse spec → compile → verify output
make test
```
**Done when**: `forge init aureon` produces bootable FastAPI app.

---

## Phase 1: Substrate Hardening (Days 2-5)
1. **zuup_auth** — PyJWT RS256, API key DB, permission cache → 15+ tests
2. **zuup_audit** — PostgreSQL store, chain verify CLI, export → integrity tests
3. **zuup_comply** — Standards registry, control mapper, FedRAMP/CMMC/HIPAA/Halal YAML
4. **zuup_data** — Async CRUD repo, migration runner, pgvector, retention
5. **zuup_ai** — Tool router, guardrails, prompt versioning, preference hooks
6. **zuup_observe** — OTEL spans, Prometheus, Grafana JSON gen
7. **zuup_gateway** — Redis rate limiter, API key validation

**Done when**: All 7 substrates >90% coverage, pass lint, work in Aureon.

---

## Phase 2: Compiler Completeness (Days 6-10)
1. OpenAPI 3.1 spec generation
2. TypeScript interfaces + API client generation
3. Pulumi IaC generation (dev/staging/prod/govcloud targets)
4. GitHub Actions CI/CD generation
5. Compliance artifact generation (traceability matrices, POAM)
6. Grafana dashboard JSON generation
7. Comprehensive test harness generation

**Done when**: `forge generate aureon` produces 20+ files covering all layers.

---

## Phase 3: All 10 Platform Specs (Days 11-15)
Write + compile specs for: Symbion, Orb, Veyra, Civium, PodX, QAWM, Relian, Stratos, Nexus + Aureon.
Each defines: entities, AI models/tools/guardrails, routes, compliance, deploy targets.

**Done when**: `forge generate` compiles all 10; each boots with uvicorn.

---

## Phase 4: RSI/RSF Flywheel (Days 16-22)
1. Preference collection (implicit signals + explicit A/B UI + HF push)
2. forge-eval harness (per-platform benchmarks, regression detection)
3. DPO pipeline (Axolotl config gen, LoRA training, model versioning)
4. Model registry (version, eval gate, promote, rollback)
5. RSF tracking (cost/revenue per call, break-even, budget allocation)

**Done when**: Preference → train → eval → deploy → serve end-to-end.

---

## Phase 5: Production Infrastructure (Days 23-30)
1. GCP Pulumi (Cloud Run → GKE, Cloud SQL+pgvector, Redis, Cloud Armor)
2. Observability (OTEL → Grafana Cloud, SLO dashboards, alerts)
3. Security (SOPS, SBOM, vulnerability scanning, image signing)
4. Compliance automation (continuous control monitoring, evidence collection)
5. Multi-platform deploy (all 10, unified dashboard, audit viewer)

**Done when**: All 10 running in GCP, observable, secure, compliance evidence auto-collected.

---

## Phase 6: Self-Building (Days 31-45)
1. Spec generation agent (NL → platform.yaml with compliance auto-detect)
2. Domain research agent (scrape regs → map frameworks → gen schemas)
3. Forge self-eval (<5min spec-to-deployment, code quality, compliance coverage)
4. Forge self-improvement (platforms → preferences → models → better Forge)

**Done when**: "Build me a platform for X" → deployed + compliant in <5 minutes.

---

## ADRs to Write (in `docs/architecture/`)
| # | Title | Phase |
|---|-------|-------|
| 001 | Platform Specification DSL | 0 |
| 002 | Substrate Separation | 1 |
| 003 | Hash-Chain over Blockchain | 1 |
| 004 | Compiler Template Strategy | 2 |
| 005 | RSI Flywheel Data Flow | 4 |
| 006 | GovCloud Topology | 5 |
| 007 | Self-Generation Safety | 6 |
