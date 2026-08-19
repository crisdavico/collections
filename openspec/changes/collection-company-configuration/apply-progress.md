# Apply Progress: collection-company-configuration

**Change**: collection-company-configuration
**Mode**: Strict TDD
**Batch**: Work unit 1 / PR 1 (stacked-to-main)
**Updated**: 2026-08-19

## Completed Tasks

- [x] 1.1 RED: Flip `"Settings"` (`test_collection_ui.py`, `test_collection_document_review_flag.py`); catalog/empty-sellers/defaults/flag tests.
- [x] 1.2 GREEN: Catalog model+data; company/settings; Collection Settings labels (keep XMLID); `19.0.1.16.0`.

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `tests/test_collection_ui.py` | Modified | Labels `"Settings"` → `"Collection Settings"`; settings arch includes new fields |
| `tests/test_collection_document_review_flag.py` | Modified | Flag preserved when other Collection Settings are saved (ON and OFF) |
| `tests/test_collection_company_settings.py` | Created | Catalog XMLIDs, unique code, defaults, empty sellers, Unsupported configurable |
| `tests/__init__.py` | Modified | Import new test module |
| `models/collection_document_type.py` | Created | Catalog `code`/`name` + `UNIQUE(code)` Constraint |
| `data/collection_document_type_data.xml` | Created | Four XMLID rows; seed empty company allow-lists |
| `models/res_company.py` | Modified | `enabled_seller_ids`, `auto_create_sheet` default True, `allowed_document_type_ids` |
| `models/res_config_settings.py` | Modified | Related writable fields for the three company fields |
| `views/res_config_settings_views.xml` | Modified | Collection Settings labels (XMLID kept); new settings fields |
| `models/__init__.py` | Modified | Import catalog model |
| `__manifest__.py` | Modified | Version `19.0.1.16.0`; load catalog data |
| `security/ir.model.access.csv` | Modified | Catalog read ACL for `base.group_user` (no extra groups) |
| `README.rst` | Modified | Generated digest/version from OCA readme hook |
| `static/description/index.html` | Modified | Generated from OCA readme hook |

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `tests/test_collection_ui.py`, `tests/test_collection_document_review_flag.py`, `tests/test_collection_company_settings.py` | Unit (TransactionCase) | ✅ 313 tests / 0 failed (`invoke test -m collection --mode=update`) | ✅ Written | ✅ Passed | ✅ Labels + arch fields; catalog unique vs distinct; empty vs persisted sellers; defaults on env.company and `new()`; flag ON and OFF | ✅ Method default + Command.set |
| 1.2 | same | Unit | N/A (implements 1.1) | ✅ Tests first | ✅ 331 tests / 0 failed | ✅ Covered by 1.1 cases | ✅ Extract `_default_allowed_document_type_ids` |

### Test Summary

- **Total tests written this slice**: 16 new (`14` in `test_collection_company_settings.py`, `2` flag-preservation)
- **Total tests passing**: 331 (`invoke test -m collection --mode=update`: `0 failed, 0 error(s)`)
- **Layers used**: Unit (16 new), Integration (0), E2E (0)
- **Approval tests** (refactoring): None — no refactoring-only task
- **Pure functions created**: 0 (Odoo ORM models)

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and exact result | `invoke test -m collection --mode=update` from `/home/crisd/projects/seedian/seedian` → `collection: 331 tests` / `0 failed, 0 error(s) of 299 tests when loading database 'devel'` |
| Runtime harness command/scenario and exact result | `invoke test -m collection --mode=update` applied `-u collection` (schema + catalog XML + seed). `invoke install -m collection` exited 0 (`--init collection` on already-installed devel). Scoped pre-commit on touched collection paths: Passed |
| Rollback boundary | Revert catalog model/data, company/settings fields, settings views/labels, manifest `19.0.1.16.0`, catalog ACL row, and matching tests. Does not remove `company_id`/`ir.rule`, migrations, `_assert_new_work`, auto-sheet behavior, or MCP replay |

## Deviations from Design

- Catalog read ACL (`base.group_user` read-only) shipped in PR 1 so the new model installs cleanly and Settings M2M can resolve types. Unit 2 still owns `ir.rule` / remaining ACL flips.
- `_collection_seed_allowed_document_types` fills **empty** company allow-lists on module load so “all four types enabled initially” holds without waiting for unit 3 migration step 5. Non-empty lists are not overwritten.
- Empty `enabled_seller_ids` is **persisted as none** in this slice; NEW-work create rejection is unit 4 (`_assert_new_work`).

None of these change the chosen settings storage (`res.company` + related `res.config.settings`) or XMLID `collection.action_collection_config_settings`.

## Issues Found

- `invoke test -m collection` default `mode=init` reports `0 tests` on an already-installed devel DB. Update mode (`--mode=update`) is required to actually run the suite.
- `res.company.create()` in this devel DB hits `res_partner.autopost_bills` NOT NULL. Default tests use `new()` instead of `create()`.
- Superuser (`res.users` id 1) is not a valid enabled seller under `domain=[("share", "=", False)]` M2M write/search. Persistence tests use `base.user_admin`.

## Remaining Tasks

- [ ] 2.1 / 2.2 `company_id` + `ir.rule`
- [ ] 3.1 / 3.2 Migration + sequences
- [ ] 4.1 / 4.2 `_assert_new_work` helper
- [ ] 5.1 / 5.2 `auto_create_sheet` + one-open
- [ ] 6.1 / 6.2 MCP same-co replay vs reject
- [ ] 7.1 `AGENTS.md` domain-rule rewrite

## Workload / PR Boundary

- Mode: stacked PR slice (stacked-to-main)
- Current work unit: Unit 1 — Settings + catalog + labels
- Boundary: starts from current main collection code; ends with catalog + company/settings fields + Collection Settings labels + `19.0.1.16.0`. Does **not** include `company_id`/`ir.rule`, voucher/sheet company backfill, `_assert_new_work`, auto-sheet gating, or MCP replay.
- Estimated review budget impact: ~300 authored added+deleted lines (under 400). Generated README digest included.

## Status

2/14 phase tasks complete (unit 1 of 7). Ready for next batch: **sdd-apply work unit 2**.
