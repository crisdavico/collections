# Apply Progress: collection-company-configuration

**Change**: collection-company-configuration
**Mode**: Strict TDD
**Batch**: Work unit 2 / PR 2 (stacked-to-main)
**Updated**: 2026-08-19

## Completed Tasks

- [x] 1.1 RED: Flip `"Settings"` (`test_collection_ui.py`, `test_collection_document_review_flag.py`); catalog/empty-sellers/defaults/flag tests.
- [x] 1.2 GREEN: Catalog model+data; company/settings; Collection Settings labels (keep XMLID); `19.0.1.16.0`.
- [x] 2.1 RED: Flip no-`ir.rule` (`test_collection_acl.py`); required `company_id` + hide-other-company (voucher/sheet/snapshot).
- [x] 2.2 GREEN: Required `company_id` on voucher/sheet/snapshot; `collection_security.xml` `ir.rule`; catalog ACL; no extra groups.

## Files Changed

### Unit 1 (prior)

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

### Unit 2 (this batch)

| File | Action | What Was Done |
|------|--------|---------------|
| `tests/test_collection_acl.py` | Modified | Flip zero `ir.rule`; required `company_id`; hide-other-company; catalog ACL; no extra groups |
| `models/collection_voucher.py` | Modified | Required `company_id` default `env.company` |
| `models/collection_sheet.py` | Modified | Required `company_id` default `env.company` |
| `models/collection_voucher_review_snapshot.py` | Modified | Related stored required `company_id` from `voucher_id.company_id` (`precompute=True`) |
| `security/collection_security.xml` | Created | Global `ir.rule` `[('company_id', 'in', company_ids)]` on voucher, sheet, snapshot |
| `__manifest__.py` | Modified | Load `collection_security.xml` before ACL CSV |
| `README.rst` | Modified | Generated source digest from OCA readme hook |
| `static/description/index.html` | Modified | Generated source digest from OCA readme hook |

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `tests/test_collection_ui.py`, `tests/test_collection_document_review_flag.py`, `tests/test_collection_company_settings.py` | Unit (TransactionCase) | ✅ 313 tests / 0 failed (`invoke test -m collection --mode=update`) | ✅ Written | ✅ Passed | ✅ Labels + arch fields; catalog unique vs distinct; empty vs persisted sellers; defaults on env.company and `new()`; flag ON and OFF | ✅ Method default + Command.set |
| 1.2 | same | Unit | N/A (implements 1.1) | ✅ Tests first | ✅ 331 tests / 0 failed | ✅ Covered by 1.1 cases | ✅ Extract `_default_allowed_document_type_ids` |
| 2.1 | `tests/test_collection_acl.py` | Unit (TransactionCase) | ✅ 331 tests / 0 failed (`invoke test -m collection --mode=update`) | ✅ Written (3 FAIL + 7 ERROR: missing `company_id` / zero `ir.rule`) | ✅ Passed | ✅ Allowed-company visible + other-company hide (voucher/sheet/snapshot) | ➖ Docstring wrap for E501 |
| 2.2 | same | Unit | N/A (implements 2.1) | ✅ Tests first | ✅ 340 tests / 0 failed | ✅ Covered by 2.1 cases | ✅ `precompute=True` so required related snapshot `company_id` is present on INSERT |

### Test Summary

- **Total tests written this slice**: 9 new ACL/company-isolation tests (plus 2 flipped no-rule assertions)
- **Total tests passing**: 340 (`invoke test -m collection --mode=update`: `0 failed, 0 error(s) of 308 tests when loading database 'devel'`)
- **Layers used**: Unit (9 new), Integration (0), E2E (0)
- **Approval tests** (refactoring): None — no refactoring-only task
- **Pure functions created**: 0 (Odoo ORM models)

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and exact result | `invoke test -m collection --mode=update` from `/home/crisd/projects/seedian/seedian` → RED: `3 failed, 7 error(s) of 308 tests`; GREEN: `collection: 340 tests` / `0 failed, 0 error(s) of 308 tests when loading database 'devel'` |
| Runtime harness command/scenario and exact result | GREEN `-u collection` applied schema + `collection_security.xml`. `invoke install -m collection` exited 0 (`--init collection` on already-installed devel). Scoped pre-commit on touched collection paths: Passed (optional pylint C8101 author warning unchanged) |
| Rollback boundary | Revert `company_id` on voucher/sheet/snapshot, `security/collection_security.xml`, manifest security XML load, and ACL test flips. Does not remove catalog/settings (WU1), migrations/sequences (WU3), `_assert_new_work` (WU4), auto-sheet (WU5), or MCP replay (WU6) |

## Deviations from Design

- Catalog read ACL (`base.group_user` read-only) shipped in PR 1 so the new model installs cleanly and Settings M2M can resolve types. Unit 2 still owns `ir.rule` / remaining ACL flips. **Done in unit 2.**
- `_collection_seed_allowed_document_types` fills **empty** company allow-lists on module load so “all four types enabled initially” holds without waiting for unit 3 migration step 5. Non-empty lists are not overwritten.
- Empty `enabled_seller_ids` is **persisted as none** in this slice; NEW-work create rejection is unit 4 (`_assert_new_work`).
- Snapshot `company_id` is related stored **and** `required=True` with `precompute=True`. Design cites the `currency_id` related-stored pattern (not required). `precompute` is required so INSERT satisfies NOT NULL; without it, snapshot create raises `NotNullViolation`.

None of these change the chosen isolation domain `[('company_id', 'in', company_ids)]`, the global (no-groups) `ir.rule`, or XMLID `collection.action_collection_config_settings`.

## Issues Found

- `invoke test -m collection` default `mode=init` reports `0 tests` on an already-installed devel DB. Update mode (`--mode=update`) is required to actually run the suite.
- `res.company.create()` in this devel DB hits `res_partner.autopost_bills` NOT NULL. Hide-other-company tests create the partner with `autopost_bills='ask'` first, then the company.
- Superuser (`res.users` id 1) is not a valid enabled seller under `domain=[("share", "=", False)]` M2M write/search. Persistence tests use `base.user_admin`.
- Related stored `required=True` snapshot `company_id` does not populate on INSERT unless `precompute=True`.

## Remaining Tasks

- [ ] 3.1 / 3.2 Migration + sequences
- [ ] 4.1 / 4.2 `_assert_new_work` helper
- [ ] 5.1 / 5.2 `auto_create_sheet` + one-open
- [ ] 6.1 / 6.2 MCP same-co replay vs reject
- [ ] 7.1 `AGENTS.md` domain-rule rewrite

## Workload / PR Boundary

- Mode: stacked PR slice (stacked-to-main)
- Current work unit: Unit 2 — `company_id` + `ir.rule`
- Boundary: starts from WU1 branch (`feat/collection-company-config-02-company-id`); ends with required `company_id` on voucher/sheet/snapshot, global company `ir.rule`, and flipped ACL tests. Does **not** include ordered 6-step migration, sequence convert/copy, `_assert_new_work`, auto-sheet gating, MCP replay, or `AGENTS.md`.
- Estimated review budget impact: ~250 authored added+deleted lines (under 400). Generated README digest included.

## Status

4/14 phase tasks complete (unit 2 of 7). Ready for next batch: **sdd-apply work unit 3**.
