# Zuup Forge — Action Items

**Source:** Audit against cursorrules + CURSOR_EXECUTION_PLAN_V2.md (2026-02-08)

All ⚠️, ❌, and ❓ items consolidated for remediation.

---

## Phase 2 — CI + Frontend

| # | Item | Type | Action |
|---|------|------|--------|
| 1 | `vercel.json` incomplete | ❌ | Add `routes` and `functions` so `/api/*` endpoints work on Vercel |
| 2 | `frontend/app.js` missing | ❌ | Add per plan structure, OR document that inline script in `index.html` is sufficient |

---

## Phase 3 — SAM.gov

| # | Item | Type | Action |
|---|------|------|--------|
| 3 | API key required | ⚠️ | Plan says "no API key required"; current requires `SAM_GOV_API_KEY`. Clarify SAM.gov API policy and either: (a) support keyless requests if possible, or (b) update plan/docs to state key is required |
| 4 | Integration test skipped | ⚠️ | `test_sam_gov_fetch` skipped when no API key. Add optional marker or mock for CI |
| 5 | Seed depends on API key | ⚠️ | "100+ opportunities" exit criterion can't be met without key. Document requirement or provide sample data fallback |

---

## Phase 4 — Landing Page

| # | Item | Type | Action |
|---|------|------|--------|
| 6 | Formspree placeholder | ⚠️ | Replace `YOUR_FORM_ID` in `frontend/index.html` with real Formspree form ID |
| 7 | Demo recording | ❓ | No `demo.cast` or embedded recording. Create with asciinema per plan Step 4.3, or link alternative |

---

## Phase 5 & 6 — Compiler + Demo

| # | Item | Type | Action |
|---|------|------|--------|
| 8 | Generated code imports `forge` | ⚠️ | Plan: "Generated code runs standalone. It does NOT import from forge." Current app/routes import `forge.substrate.*`. Either: (a) inline audit/auth into generated code, or (b) update plan to allow forge as runtime dependency |
| 9 | Compiler generates Dockerfile | ⚠️ | Plan says "Remove Dockerfile (premature)"; cursorrules say "docker only if explicitly needed." Stop generating `platforms/aureon/Dockerfile`, or document exception |
| 10 | Makefile `seed` gated on API key | ⚠️ | Plan: seed runs unconditionally. Current: requires `SAM_GOV_API_KEY`. Either run without key (empty/mock data) or document in Makefile/plan |
| 11 | `demo.sh` is bash-only | ⚠️ | No Windows-native equivalent. Add `scripts/demo.ps1` for PowerShell, or document bash-only in README |

---

## Misc

| # | Item | Type | Action |
|---|------|------|--------|
| 12 | Display name encoding | ⚠️ | `Aureon™` renders as `Aureon???` in generated files. Fix encoding in `api_gen.py` |
| 13 | Pydantic/startup deprecations | ⚠️ | Generated models use deprecated `class Config`; app uses deprecated `on_event("startup")`. Migrate to `ConfigDict` and lifespan |

---

## Quick Reference — Files to Touch

| Item | File(s) |
|------|---------|
| 1 | `vercel.json` |
| 2 | `frontend/` (add app.js or document) |
| 3–5 | `forge/integrations/sam_gov.py`, `scripts/seed_sam_gov.py`, `tests/test_sam_gov.py`, `CURSOR_EXECUTION_PLAN_V2.md` |
| 6 | `frontend/index.html` |
| 7 | `scripts/` (demo.cast), `frontend/index.html` (embed) |
| 8 | `forge/compiler/api_gen.py` or plan |
| 9 | `forge/compiler/__init__.py` (remove `_generate_dockerfile` call) |
| 10 | `Makefile` |
| 11 | `scripts/demo.ps1` (new) or README |
| 12 | `forge/compiler/api_gen.py` |
| 13 | `forge/compiler/schema_gen.py`, `forge/compiler/api_gen.py` |
