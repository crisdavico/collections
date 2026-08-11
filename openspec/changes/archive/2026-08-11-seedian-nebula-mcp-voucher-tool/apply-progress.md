# Apply Progress: seedian-nebula-mcp-voucher-tool

**Mode**: Strict TDD (Units 1–4) + Standard quality gate (Phase 5)  
**Work unit**: `phase-5-quality-gate`  
**Evidence goal**: `phase5-install-precommit-tests-green`  
**Acquire token**: `sha256:7c21d67a6c0590ff69784f54f1a1c3b5cb7fe7b2e3235a3e6d87510e1c689186`  
**Prior units**: `unit-1-received-date-create-date`, `unit-2-document-id`, `unit-3-mcp-create-acl`, `unit-4-idempotency-race` (complete)  
**Updated**: 2026-08-11

## Completed Tasks

### Unit 1 (prior batch)

- [x] 1.1 RED: voucher tests — no `received_date`; auto `create_date`; reject `received_date` vals
- [x] 1.2 RED: UI tests — readonly `create_date` in views; no `received_date` in arch
- [x] 1.3 GREEN: Drop `received_date` from voucher model (+ strip forged `create_date`/`write_date` on create)
- [x] 1.4 GREEN: Views → readonly `create_date`
- [x] 1.5 GREEN: `migrations/19.0.1.1.0/post-migrate.py` DROP COLUMN; bump `19.0.1.1.0`
- [x] 1.6 Verify: `invoke install -m seedian_nebula`; `invoke test -m seedian_nebula --mode=update`

### Unit 2 (prior batch)

- [x] 2.1 RED: Payment w/o `document_id` OK; duplicate non-null → IntegrityError
- [x] 2.2 GREEN: Nullable Char `document_id` + unique `models.Constraint` on payment model
- [x] 2.3 Verify: `invoke test -m seedian_nebula --mode=update`

### Unit 3 (prior batch)

- [x] 3.1 RED: `tests/test_seedian_nebula_mcp_tool.py` — `_call` discover; all-new return; no `received_date` schema; require `document_id`
- [x] 3.2 RED: Non-permitted user → AccessError, no writes
- [x] 3.3 GREEN: Manifest `depends` += `muk_mcp`; `__init__.py` import `tools`
- [x] 3.4 GREEN: `tools/__init__.py` + `tools/nebula_voucher.py` — mixin + `@mcp_tool` allowlist schema
- [x] 3.5 GREEN: Validate → savepoint voucher+batch payments; return `{id,name,state,payments}`; no `sudo()`
- [x] 3.6 Register in `tests/__init__.py`; `invoke test -m seedian_nebula --mode=update`

### Unit 4 (prior batch)

- [x] 4.1 RED: Exact-retry → same ids, no new rows (customer ignored on match)
- [x] 4.2 RED: In-call duplicate `document_id` → reject, no writes
- [x] 4.3 RED: Partial-conflict → reject, no writes
- [x] 4.4 RED: Cross-voucher-conflict → reject, no writes
- [x] 4.5 RED: UniqueViolation → re-lookup; full match → replay; else UserError
- [x] 4.6 GREEN: Lookup/create/reject + UniqueViolation → replay/reject in `tools/nebula_voucher.py`
- [x] 4.7 Verify: `invoke test -m seedian_nebula --mode=update`

### Phase 5 quality gate (this batch)

- [x] 5.1 `invoke install -m seedian_nebula` → exit 0 (`addons init -w seedian_nebula`, registry loaded, shutdown clean)
- [x] 5.2 `pre-commit run --files` scoped to seedian_nebula module paths → exit 0 after E501 docstring/message wraps + README regen
- [x] 5.3 `invoke test -m seedian_nebula --mode=update` → **0 failed, 0 error(s) of 46 tests** (`seedian_nebula: 58 tests`)

## Remaining Tasks

None — all 25 tasks complete. Apply phase done.

## TDD Cycle Evidence

### Unit 1 (prior)

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `tests/test_seedian_nebula_voucher.py` | Unit | ✅ 27/27 (update mode) | ✅ Written | ✅ Passed | ✅ defaults + field absent + reject vals + create_date not overridable | ✅ Minimal create() pop |
| 1.2 | `tests/test_seedian_nebula_ui.py` | Unit | ✅ included in 27 | ✅ Written | ✅ Passed | ✅ list/search + kanban + form + all-arch absence | ➖ None needed |
| 1.3–1.5 | production | — | — | covered by 1.1/1.2 | ✅ Passed | covered | ➖ |
| 1.6 | verify | Integration | — | — | ✅ install + tests | — | — |

### Unit 2 (prior)

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 2.1 | `tests/test_seedian_nebula_payment.py` | Unit | ✅ 0 failed / 30 tests | ✅ Written (4 errors: missing `document_id`) | covered by 2.2 | ✅ omit / multi-NULL / duplicate / distinct ids | ➖ |
| 2.2 | `models/seedian_nebula_payment.py` | Unit | — | covered by 2.1 | ✅ Passed | covered | ➖ None needed |
| 2.3 | verify | Integration | — | — | ✅ `invoke test -m seedian_nebula --mode=update` | — | — |

### Unit 3 (prior)

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 3.1 | `tests/test_seedian_nebula_mcp_tool.py` | Integration (`muk_mcp.tool._call`) | ✅ 0 failed / 34 tests | ✅ Written | ✅ Passed | ✅ all-new create + missing/empty `document_id` + empty payments | ➖ None needed |
| 3.2 | `tests/test_seedian_nebula_mcp_tool.py` | Integration (ACL) | ✅ included | ✅ Written | ✅ Passed | ➖ Single ACL scenario | ➖ |
| 3.3–3.5 | `tools/nebula_voucher.py` + manifest/`__init__` | — | — | covered by 3.1/3.2 | ✅ Passed | covered | ➖ |
| 3.6 | verify | Integration | — | — | ✅ 0 failed / 40 tests | — | — |

### Unit 4 (prior)

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 4.1 | `tests/test_seedian_nebula_mcp_tool.py` | Integration | ✅ 0 failed / 40 tests | ✅ Written (UniqueViolation ERROR — no lookup yet) | ✅ Passed | ✅ customer mismatch ignored on replay | ✅ helpers extracted |
| 4.2 | same | Integration | ✅ included | ✅ Written (UniqueViolation / no UserError) | ✅ Passed | ➖ Single in-call dup scenario | covered |
| 4.3 | same | Integration | ✅ included | ✅ Written | ✅ Passed | ➖ Single partial scenario | covered |
| 4.4 | same | Integration | ✅ included | ✅ Written | ✅ Passed | ➖ Single cross-voucher scenario | covered |
| 4.5 | same | Integration | ✅ included | ✅ Written (2 ERROR UniqueViolation uncaught) | ✅ Passed | ✅ full-match replay + partial-after-race UserError | ✅ invalidate_all after UV |
| 4.6 | `tools/nebula_voucher.py` | — | — | covered by 4.1–4.5 | ✅ Passed | covered | ✅ parse/lookup/replay/create helpers; non-mutating create vals |
| 4.7 | verify | Integration | — | — | ✅ `invoke test -m seedian_nebula --mode=update` → **0 failed, 0 error(s) of 46 tests** (`seedian_nebula: 58 tests`) | — | — |

### Phase 5 (this batch)

| Task | Command | Result |
|------|---------|--------|
| 5.1 | `invoke install -m seedian_nebula` | ✅ exit 0 |
| 5.2 | `pre-commit run --files` (module paths) | ✅ exit 0 (after E501 lint fixes + README regen) |
| 5.3 | `invoke test -m seedian_nebula --mode=update` | ✅ 0 failed, 0 error(s) / 46 tests (`seedian_nebula: 58 tests`) |

## Work Unit Evidence

### Unit 1 (prior)

| Evidence | Result |
|---|---|
| Focused test command | `invoke test -m seedian_nebula --mode=update` → **0 failed, 0 error(s) of 30 tests** (`seedian_nebula: 38 tests`) |
| Runtime harness | `invoke install -m seedian_nebula` → module `installed` / `latest_version=19.0.1.1.0`; no `received_date` column |
| Rollback boundary | Revert voucher model/views/migration/version + Unit-1 voucher/UI tests |

### Unit 2 (prior)

| Evidence | Result |
|---|---|
| Focused test command | `invoke test -m seedian_nebula --mode=update` → **0 failed, 0 error(s) of 34 tests** (`seedian_nebula: 44 tests`) |
| Runtime harness | N/A — model-only unit |
| Rollback boundary | Revert payment `document_id` + uniqueness tests |

### Unit 3 (prior)

| Evidence | Result |
|---|---|
| Focused test command | `invoke test -m seedian_nebula --mode=update` → **0 failed, 0 error(s) of 40 tests** (`seedian_nebula: 52 tests`) |
| Runtime harness | MCP `_call` in TransactionCase |
| Rollback boundary | Revert `tools/`, manifest/`__init__` muk_mcp wiring, MCP tests — does not touch Units 1–2 or Unit 4 |

### Unit 4 (prior)

| Evidence | Result |
|---|---|
| Focused test command | `invoke test -m seedian_nebula --mode=update` → **0 failed, 0 error(s) of 46 tests** (`seedian_nebula: 58 tests`) |
| Runtime harness | MCP `_call` conflict/idempotency paths + race via first-search miss forcing real `UniqueViolation` then re-lookup |
| Rollback boundary | Revert Unit-4 edits to `tools/nebula_voucher.py` idempotency/race helpers and Unit-4 tests in `tests/test_seedian_nebula_mcp_tool.py` — leaves Units 1–3 create/ACL/discover intact if restored carefully |

### Phase 5 (this batch)

| Evidence | Result |
|---|---|
| Focused test command | `invoke test -m seedian_nebula --mode=update` → **0 failed, 0 error(s) of 46 tests** (`seedian_nebula: 58 tests`, 1.27s, 1734 queries) |
| Runtime harness | `invoke install -m seedian_nebula` → exit 0; `pre-commit run --files` on module paths → exit 0 |
| Rollback boundary | Phase 5 only touched lint-safe docstring/message wraps in tests + regenerated `README.rst`; no feature logic changes |

## Test Summary

### Phase 5

- **Install**: exit 0 (`odoo --stop-after-init --init seedian_nebula`)
- **Pre-commit**: first pass failed on 5× E501 + `oca-gen-addon-readme` auto-edit; fixed E501 in `test_seedian_nebula_mcp_tool.py` / `test_seedian_nebula_ui.py`; second pass **Passed** (optional pylint C8101 Eynes author warning only — non-blocking)
- **Tests**: 0 failed, 0 error(s) / 46 tests (`seedian_nebula: 58 tests`)
- **Layers used**: install + lint + full module TransactionCase suite
- **Approval tests**: None

## Files Changed (Phase 5)

| File | Action | What Was Done |
|------|--------|---------------|
| `tests/test_seedian_nebula_mcp_tool.py` | Modified | Shortened 3 docstrings for E501 ≤88 |
| `tests/test_seedian_nebula_ui.py` | Modified | Split readonly assertion message for E501 |
| `README.rst` | Regenerated | `oca-gen-addon-readme` auto-update |
| `openspec/changes/.../tasks.md` | Modified | Marked 5.1–5.3 `[x]`; noted `--mode=update` on 5.3 |
| `openspec/changes/.../apply-progress.md` | Modified | This cumulative progress artifact |
| `openspec/changes/.../state.yaml` | Modified | `phases.apply: done`; all 25 tasks completed |

## Approximate changed-line count (Phase 5)

≈10–20 authored lint-fix lines (+ generated README). Negligible review budget impact.

## Deviations from Design

None — quality gate only; no feature changes.

## Issues Found

None blocking. Optional pylint `C8101(manifest-required-author)` still warns that author should include `Eynes` — hook Passed; out of scope for this change unless maintainers want it fixed separately.

## Workload / PR Boundary

- Mode: stacked PR slices (`stacked-to-main`) for Units 1–4; Phase 5 is cross-cutting gate evidence for the whole change
- Current work unit: Phase 5 — quality gate
- Boundary: install + pre-commit + full tests only
- Estimated review budget impact: Low for Phase 5 alone

## Status

**25/25 tasks complete.** Apply phase done (`state.yaml` `phases.apply: done`).  
**Next**: `sdd-verify`.

## Acquire token echo

`sha256:7c21d67a6c0590ff69784f54f1a1c3b5cb7fe7b2e3235a3e6d87510e1c689186`
