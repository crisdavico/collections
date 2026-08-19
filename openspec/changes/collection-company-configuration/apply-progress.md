# Apply Progress: collection-company-configuration

**Change**: collection-company-configuration
**Mode**: Strict TDD
**Batch**: Work unit 3 / PR 3 (stacked-to-main)
**Updated**: 2026-08-19

## Completed Tasks

- [x] 1.1 RED: Flip `"Settings"` (`test_collection_ui.py`, `test_collection_document_review_flag.py`); catalog/empty-sellers/defaults/flag tests.
- [x] 1.2 GREEN: Catalog model+data; company/settings; Collection Settings labels (keep XMLID); `19.0.1.16.0`.
- [x] 2.1 RED: Flip no-`ir.rule` (`test_collection_acl.py`); required `company_id` + hide-other-company (voucher/sheet/snapshot).
- [x] 2.2 GREEN: Required `company_id` on voucher/sheet/snapshot; `collection_security.xml` `ir.rule`; catalog ACL; no extra groups.
- [x] 3.1 RED: Stamp/repair/seed/four-types; per-company `COL/` `CS/` (no `company_id=False` thief).
- [x] 3.2 GREEN: `post-migrate.py` steps 1–6; seq → `base.main_company`; `with_company` `next_by_code`; company create copies seq+types.

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

### Unit 2 (prior)

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

### Unit 3 (this batch)

| File | Action | What Was Done |
|------|--------|---------------|
| `tests/test_collection_company_migration.py` | Created | Stamp/repair/seed/four-types; isolated `COL/` `CS/`; False-sequence thief; company-create copies |
| `tests/test_collection_company_settings.py` | Modified | `enabled_seller_ids` default-empty asserts field default (env.company may be seeded on upgrade) |
| `tests/__init__.py` | Modified | Import migration test module |
| `migrations/19.0.1.17.0/post-migrate.py` | Created | Ordered steps 1–6; tests call `migrate(cr, version)` directly |
| `models/res_company.py` | Modified | Sequence copy + union-all-four helpers; `create` copies seq+types, empty sellers |
| `models/collection_voucher.py` | Modified | `with_company(record.company_id).next_by_code("collection.voucher")` |
| `models/collection_sheet.py` | Modified | `with_company(record.company_id).next_by_code("collection.sheet")` |
| `data/ir_sequence_data.xml` | Modified | Bind XMLIDs to `base.main_company` (`noupdate=1`) |
| `__manifest__.py` | Modified | Version `19.0.1.17.0` so the new migrate folder runs |
| `README.rst` | Modified | Generated source digest from OCA readme hook |
| `static/description/index.html` | Modified | Generated source digest from OCA readme hook |

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `tests/test_collection_ui.py`, `tests/test_collection_document_review_flag.py`, `tests/test_collection_company_settings.py` | Unit (TransactionCase) | ✅ 313 tests / 0 failed (`invoke test -m collection --mode=update`) | ✅ Written | ✅ Passed | ✅ Labels + arch fields; catalog unique vs distinct; empty vs persisted sellers; defaults on env.company and `new()`; flag ON and OFF | ✅ Method default + Command.set |
| 1.2 | same | Unit | N/A (implements 1.1) | ✅ Tests first | ✅ 331 tests / 0 failed | ✅ Covered by 1.1 cases | ✅ Extract `_default_allowed_document_type_ids` |
| 2.1 | `tests/test_collection_acl.py` | Unit (TransactionCase) | ✅ 331 tests / 0 failed (`invoke test -m collection --mode=update`) | ✅ Written (3 FAIL + 7 ERROR: missing `company_id` / zero `ir.rule`) | ✅ Passed | ✅ Allowed-company visible + other-company hide (voucher/sheet/snapshot) | ➖ Docstring wrap for E501 |
| 2.2 | same | Unit | N/A (implements 2.1) | ✅ Tests first | ✅ 340 tests / 0 failed | ✅ Covered by 2.1 cases | ✅ `precompute=True` so required related snapshot `company_id` is present on INSERT |
| 3.1 | `tests/test_collection_company_migration.py` | Unit (TransactionCase) | ✅ 340 tests / 0 failed (`invoke test -m collection --mode=update`) | ✅ Written (missing `post-migrate.py`; XML `eval=False`; shared `COL/` counter `8667 != 1`; partial types stay `{check}`) | ✅ Passed | ✅ Sheet seller vs main; voucher sheet/seller/main; repair; seed active+archived; partial vs extra types; two-company `COL/`+`CS/`; False thief 9999 | ➖ Test helper wrap / `active_test=False` read |
| 3.2 | same | Unit | N/A (implements 3.1) | ✅ Tests first | ✅ 353 tests / 0 failed | ✅ Covered by 3.1 cases | ✅ Extract `_collection_copy_sequences` + `_collection_enable_all_document_types` |

### Test Summary

- **Total tests written this slice**: 11 new migration/sequence tests (plus 1 retargeted default-empty assertion)
- **Total tests passing**: 353 (`invoke test -m collection --mode=update`: `0 failed, 0 error(s) of 319 tests when loading database 'devel'`)
- **Layers used**: Unit (11 new), Integration (0), E2E (0)
- **Approval tests** (refactoring): None — no refactoring-only task
- **Pure functions created**: 0 (Odoo ORM + SQL migrate)

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and exact result | `invoke test -m collection --mode=update` from `/home/crisd/projects/seedian/seedian` → SAFETY NET: `collection: 340 tests` / `0 failed`. RED: missing `migrations/19.0.1.17.0/post-migrate.py`, XML still `eval="False"`, shared numbering `8667 != 1`. GREEN: `collection: 353 tests` / `0 failed, 0 error(s) of 319 tests when loading database 'devel'` |
| Runtime harness command/scenario and exact result | GREEN `-u collection` jumped `19.0.1.16.0` → `19.0.1.17.0` and ran `post-migrate.py` on devel. Tests also call `migrate(cr, version)` directly so RED/GREEN does not depend only on that version jump. Scoped pre-commit on touched collection paths: Passed (optional pylint C8101 author warning unchanged) |
| Rollback boundary | Revert `migrations/19.0.1.17.0/`, sequence XML bind, `with_company` next_by_code, company create seq+type copy, manifest `19.0.1.17.0`, and migration tests. Does not remove catalog/settings (WU1), `company_id`/`ir.rule` (WU2), `_assert_new_work` (WU4), auto-sheet (WU5), or MCP replay (WU6) |

## Deviations from Design

- Catalog read ACL (`base.group_user` read-only) shipped in PR 1 so the new model installs cleanly and Settings M2M can resolve types. Unit 2 still owns `ir.rule` / remaining ACL flips. **Done in unit 2.**
- `_collection_seed_allowed_document_types` fills **empty** company allow-lists on module load so “all four types enabled initially” holds without waiting for unit 3 migration step 5. Non-empty lists are not overwritten. **Unit 3 migrate step 5 unions all four even when a partial list already exists.**
- Empty `enabled_seller_ids` is **persisted as none** in unit 1; NEW-work create rejection is unit 4 (`_assert_new_work`).
- Snapshot `company_id` is related stored **and** `required=True` with `precompute=True`. Design cites the `currency_id` related-stored pattern (not required). `precompute` is required so INSERT satisfies NOT NULL; without it, snapshot create raises `NotNullViolation`.
- Design file path `migrations/19.0.1.16.0/post-migrate.py` would not run on devel already at 1.16.0. Script lives in `migrations/19.0.1.17.0/post-migrate.py` with manifest `19.0.1.17.0`.
- Sequence copies for non-main companies start at `number_next=1` (main keeps historical `number_next`). Design said INSERT copies; it did not require copying the main counter.
- `test_enabled_seller_ids_default_empty` now asserts the field has no default (not `env.company` emptiness). Upgrade seed on devel populates `env.company.enabled_seller_ids` from historical vouchers/sheets, which is required migrate step 4.

None of these change stamp order, repair, four-type union, `with_company` numbering, or XMLID `collection.action_collection_config_settings`.

## Issues Found

- `invoke test -m collection` default `mode=init` reports `0 tests` on an already-installed devel DB. Update mode (`--mode=update`) is required to actually run the suite.
- `res.company.create()` in this devel DB hits `res_partner.autopost_bills` NOT NULL. Hide-other-company tests create the partner with `autopost_bills='ask'` first, then the company.
- Superuser (`res.users` id 1) is not a valid enabled seller under `domain=[("share", "=", False)]` M2M write/search. Persistence tests use `base.user_admin`.
- Related stored `required=True` snapshot `company_id` does not populate on INSERT unless `precompute=True`.
- Reading archived users on `enabled_seller_ids` requires `company.with_context(active_test=False)` (not context on the already-filtered recordset).
- A migrate folder matching the **already-installed** manifest version will not run; bump past current (`1.16.0` → `1.17.0`) and invoke `migrate()` from tests.

## Remaining Tasks

- [ ] 4.1 / 4.2 `_assert_new_work` helper
- [ ] 5.1 / 5.2 `auto_create_sheet` + one-open
- [ ] 6.1 / 6.2 MCP same-co replay vs reject
- [ ] 7.1 `AGENTS.md` domain-rule rewrite

## Workload / PR Boundary

- Mode: stacked PR slice (stacked-to-main)
- Current work unit: Unit 3 — migration + sequences
- Boundary: starts from WU2 branch (`feat/collection-company-config-03-migration`); ends with ordered 6-step `post-migrate.py`, per-company sequences, `with_company` numbering, and company-create copies. Does **not** include `_assert_new_work`, auto-sheet gating, MCP replay, or `AGENTS.md`.
- Estimated review budget impact: production ~210 authored added+deleted lines; tests ~410. Over the 400-line review budget because of TransactionCase coverage. Generated README digest excluded from authored risk.

## Status

6/14 phase tasks complete (unit 3 of 7). Ready for next batch: **sdd-apply work unit 4**.
