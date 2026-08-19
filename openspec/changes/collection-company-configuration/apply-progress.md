# Apply Progress: collection-company-configuration

**Change**: collection-company-configuration
**Mode**: Strict TDD
**Batch**: Work unit 5 / PR 5 (stacked-to-main)
**Updated**: 2026-08-19

## Completed Tasks

- [x] 1.1 RED: Flip `"Settings"` (`test_collection_ui.py`, `test_collection_document_review_flag.py`); catalog/empty-sellers/defaults/flag tests.
- [x] 1.2 GREEN: Catalog model+data; company/settings; Collection Settings labels (keep XMLID); `19.0.1.16.0`.
- [x] 2.1 RED: Flip no-`ir.rule` (`test_collection_acl.py`); required `company_id` + hide-other-company (voucher/sheet/snapshot).
- [x] 2.2 GREEN: Required `company_id` on voucher/sheet/snapshot; `collection_security.xml` `ir.rule`; catalog ACL; no extra groups.
- [x] 3.1 RED: Stamp/repair/seed/four-types; per-company `COL/` `CS/` (no `company_id=False` thief).
- [x] 3.2 GREEN: `post-migrate.py` steps 1–6; seq → `base.main_company`; `with_company` `next_by_code`; company create copies seq+types.
- [x] 4.1 RED: Flip nullable-ORM-seller (`test_collection_voucher.py`); empty/disabled/disallowed-type, seller/type write, historical-operable, UI domains.
- [x] 4.2 GREEN: `res.company._assert_new_work` on create + seller/type write; skip Approve/Close/Reopen; `collection_views.xml` domains.
- [x] 5.1 RED: Flip always-on auto-assign + per-seller one-open (`test_collection_sheet.py`); OFF skip both; Action still creates; open in A+B.
- [x] 5.2 GREEN: Gate auto-assign (OFF skips both); lock `(company_id, seller_id)`; list Action uses company + helper.

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

### Unit 3 (prior)

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

### Unit 4 (this batch)

| File | Action | What Was Done |
|------|--------|---------------|
| `tests/test_collection_voucher.py` | Modified | Flip omit-seller create; empty/disabled/disallowed-type; seller/type write; historical approve/reject; type-selection union |
| `tests/test_collection_sheet.py` | Modified | Empty/disabled sheet create; historical close/reopen skip helper |
| `tests/test_collection_ui.py` | Modified | Seller domain asserts on voucher form/list and sheet form |
| `tests/test_collection_payment.py` | Modified | Shared `ensure_enabled_seller` / `create_internal_seller` so existing creates pass the helper |
| `tests/test_collection_acl.py` | Modified | Enable `base.user_admin` before voucher/sheet creates |
| `tests/test_collection_mail.py` | Modified | Enable seller before mail-suite creates |
| `tests/test_collection_document_review.py` | Modified | Enable seller before review creates |
| `tests/test_collection_document_review_flag.py` | Modified | Enable seller before flag-suite creates |
| `tests/test_collection_mcp_tool.py` | Modified | Enable seller in MCP Attachment/Provenance `setUpClass` |
| `tests/test_collection_company_migration.py` | Modified | Enable seller in `_create_voucher` injector |
| `models/res_company.py` | Modified | `@api.private` `_assert_new_work(seller, document_type=None)`; UserError; never sudo |
| `models/collection_voucher.py` | Modified | Helper on create + seller/type write; `_selection_document_type` = allowed ∪ current |
| `models/collection_sheet.py` | Modified | Helper on create (seller only); Close/Reopen unchanged |
| `views/collection_views.xml` | Modified | Seller domain = company enabled list; optional `company_id` column; keep `<list>` |

### Unit 5 (this batch)

| File | Action | What Was Done |
|------|--------|---------------|
| `tests/test_collection_sheet.py` | Modified | OFF skip create+assign and skip assign when open exists; Action still creates when OFF; one-open per `(company, seller)`; auto-assign and Action stamp voucher company |
| `tests/test_collection_company_migration.py` | Modified | Sequence-isolation test turns `auto_create_sheet` OFF so COL/CS asserts are not coupled to auto-created sheets |
| `models/collection_voucher.py` | Modified | Gate auto-assign on company `auto_create_sheet`; resolve by `(company_id, seller_id)`; list Action uses selection company + helper |
| `models/collection_sheet.py` | Modified | Open-sheet search + advisory lock scoped to `(company_id, seller_id)`; create/reopen keys by company+seller; auto-created sheets stamp voucher company |

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `tests/test_collection_ui.py`, `tests/test_collection_document_review_flag.py`, `tests/test_collection_company_settings.py` | Unit (TransactionCase) | ✅ 313 tests / 0 failed (`invoke test -m collection --mode=update`) | ✅ Written | ✅ Passed | ✅ Labels + arch fields; catalog unique vs distinct; empty vs persisted sellers; defaults on env.company and `new()`; flag ON and OFF | ✅ Method default + Command.set |
| 1.2 | same | Unit | N/A (implements 1.1) | ✅ Tests first | ✅ 331 tests / 0 failed | ✅ Covered by 1.1 cases | ✅ Extract `_default_allowed_document_type_ids` |
| 2.1 | `tests/test_collection_acl.py` | Unit (TransactionCase) | ✅ 331 tests / 0 failed (`invoke test -m collection --mode=update`) | ✅ Written (3 FAIL + 7 ERROR: missing `company_id` / zero `ir.rule`) | ✅ Passed | ✅ Allowed-company visible + other-company hide (voucher/sheet/snapshot) | ➖ Docstring wrap for E501 |
| 2.2 | same | Unit | N/A (implements 2.1) | ✅ Tests first | ✅ 340 tests / 0 failed | ✅ Covered by 2.1 cases | ✅ `precompute=True` so required related snapshot `company_id` is present on INSERT |
| 3.1 | `tests/test_collection_company_migration.py` | Unit (TransactionCase) | ✅ 340 tests / 0 failed (`invoke test -m collection --mode=update`) | ✅ Written (missing `post-migrate.py`; XML `eval=False`; shared `COL/` counter `8667 != 1`; partial types stay `{check}`) | ✅ Passed | ✅ Sheet seller vs main; voucher sheet/seller/main; repair; seed active+archived; partial vs extra types; two-company `COL/`+`CS/`; False thief 9999 | ➖ Test helper wrap / `active_test=False` read |
| 3.2 | same | Unit | N/A (implements 3.1) | ✅ Tests first | ✅ 353 tests / 0 failed | ✅ Covered by 3.1 cases | ✅ Extract `_collection_copy_sequences` + `_collection_enable_all_document_types` |
| 4.1 | `tests/test_collection_voucher.py`, `tests/test_collection_sheet.py`, `tests/test_collection_ui.py` | Unit (TransactionCase) | ✅ 353 tests / 0 failed (`invoke test -m collection --mode=update`) | ✅ Written (omit-seller create; empty/disabled seller; disallowed type; seller/type write; missing UI `enabled_seller_ids` domains; missing `_selection_document_type`) | ✅ Passed | ✅ Missing seller; empty list; disabled seller; disallowed type; historical approve/reject/close/reopen; UI domain | ➖ E501 wraps in UI/voucher tests |
| 4.2 | same + existing create suites | Unit | N/A (implements 4.1) | ✅ Tests first | ✅ 373 tests / 0 failed | ✅ Covered by 4.1 cases | ✅ Shared `ensure_enabled_seller`; unique `_other_internal_seller` logins |
| 5.1 | `tests/test_collection_sheet.py` | Unit (TransactionCase) | ✅ 373 tests / 0 failed (`invoke test -m collection --mode=update`) | ✅ Written (5 FAIL + 2 ERROR: OFF still assigned; Action sheet in env.company; second open in B UserError) | ✅ Passed | ✅ OFF skip both vs skip assign when open exists; Action when OFF; open in A+B; auto-assign/Action use voucher company; Action allowed when open only in other company | ➖ E501 docstring wraps |
| 5.2 | same + `tests/test_collection_company_migration.py` | Unit | N/A (implements 5.1) | ✅ Tests first | ✅ 380 tests / 0 failed | ✅ Covered by 5.1 cases; isolation test retargeted with auto OFF | ✅ Extract `_company_id_of`; lock `hashtext('collection.sheet.open.' \|\| company_id)` |

### Test Summary

- **Total tests written this slice**: 7 new auto-sheet/one-open TransactionCase methods; WU3 isolation test retargeted
- **Total tests passing**: 380 (`invoke test -m collection --mode=update`: `0 failed, 0 error(s) of 344 tests when loading database 'devel'`)
- **Layers used**: Unit (7 new this slice), Integration (0), E2E (0)
- **Approval tests** (refactoring): None — no refactoring-only task
- **Pure functions created**: 1 (`_company_id_of` id unwrap)

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and exact result | `invoke test -m collection --mode=update` from `/home/crisd/projects/seedian/seedian` → SAFETY NET: `collection: 373 tests` / `0 failed`. RED: `5 failed, 2 error(s)` (OFF still assigned; Action/auto-assign used env.company; B create UserError). GREEN: `collection: 380 tests` / `0 failed, 0 error(s) of 344 tests when loading database 'devel'` |
| Runtime harness command/scenario and exact result | GREEN `-u collection` on devel ran the auto-sheet + one-open tests. Scoped pre-commit on touched collection paths: Passed (ruff E501 then clean) |
| Rollback boundary | Revert voucher auto-assign gate, sheet open-search/lock/create/reopen company scope, list Action company stamp, WU5 tests, and the isolation-test auto-OFF. Does not remove helper (WU4), catalog/settings (WU1), `company_id`/`ir.rule` (WU2), migrate/sequences (WU3), MCP classifier (WU6), or `AGENTS.md` (WU7) |

## Deviations from Design

- Catalog read ACL (`base.group_user` read-only) shipped in PR 1 so the new model installs cleanly and Settings M2M can resolve types. Unit 2 still owns `ir.rule` / remaining ACL flips. **Done in unit 2.**
- `_collection_seed_allowed_document_types` fills **empty** company allow-lists on module load so “all four types enabled initially” holds without waiting for unit 3 migration step 5. Non-empty lists are not overwritten. **Unit 3 migrate step 5 unions all four even when a partial list already exists.**
- Empty `enabled_seller_ids` is **persisted as none** in unit 1; NEW-work create rejection is unit 4 (`_assert_new_work`).
- Snapshot `company_id` is related stored **and** `required=True` with `precompute=True`. Design cites the `currency_id` related-stored pattern (not required). `precompute` is required so INSERT satisfies NOT NULL; without it, snapshot create raises `NotNullViolation`.
- Design file path `migrations/19.0.1.16.0/post-migrate.py` would not run on devel already at 1.16.0. Script lives in `migrations/19.0.1.17.0/post-migrate.py` with manifest `19.0.1.17.0`.
- Sequence copies for non-main companies start at `number_next=1` (main keeps historical `number_next`). Design said INSERT copies; it did not require copying the main counter.
- `test_enabled_seller_ids_default_empty` now asserts the field has no default (not `env.company` emptiness). Upgrade seed on devel populates `env.company.enabled_seller_ids` from historical vouchers/sheets, which is required migrate step 4.
- `_assert_new_work` is called on **sheet.create** (seller only) because 4.1 sheet enabled-seller tests require it. **WU5** scoped auto-assign, one-open search, and advisory lock to `(company_id, seller_id)`.
- Voucher `write` passes `document_type=None` when only `seller_id` is written so a seller-only write does not re-check type.
- `_selection_document_type` is a public selection method (not `@api.model` / `@api.private`) so form/list can union allowed ∪ current.

None of these change stamp order, repair, four-type union, `with_company` numbering, or XMLID `collection.action_collection_config_settings`.

## Issues Found

- `invoke test -m collection` default `mode=init` reports `0 tests` on an already-installed devel DB. Update mode (`--mode=update`) is required to actually run the suite.
- `res.company.create()` in this devel DB hits `res_partner.autopost_bills` NOT NULL. Hide-other-company tests create the partner with `autopost_bills='ask'` first, then the company.
- Superuser (`res.users` id 1) is not a valid enabled seller under `domain=[("share", "=", False)]` M2M write/search. Persistence tests use `base.user_admin`.
- Related stored `required=True` snapshot `company_id` does not populate on INSERT unless `precompute=True`.
- Reading archived users on `enabled_seller_ids` requires `company.with_context(active_test=False)` (not context on the already-filtered recordset).
- A migrate folder matching the **already-installed** manifest version will not run; bump past current (`1.16.0` → `1.17.0`) and invoke `migrate()` from tests.
- WU3 seed fills `env.company.enabled_seller_ids`; empty/disabled helper tests must `Command.clear()` / unlink rather than assume a default-empty list.
- Sheet auto-create during voucher.create previously used `env.company` (no `company_id` in sheet vals). **WU5** stamps the voucher company; tests that enable a seller on another company must still enable it on that company.
- Searching `id != uid` for “other seller” can return `user_admin` (same as the primary test seller) and trip one-open. Tests now create unique logins via `create_internal_seller`.
- Auto-assign now stamps the voucher company on the created sheet, so WU3 `test_voucher_and_sheet_numbers_isolated_per_company` must turn `auto_create_sheet` OFF (or it consumes `CS/` in company B before the explicit sheet create).
- List Action mixed-company selection now raises a same-company UserError (design: selection same company). No dedicated mixed-company Action test in this slice.

## Remaining Tasks

- [ ] 6.1 / 6.2 MCP same-co replay vs reject
- [ ] 7.1 `AGENTS.md` domain-rule rewrite

## Workload / PR Boundary

- Mode: stacked PR slice (stacked-to-main)
- Current work unit: Unit 5 — `auto_create_sheet` + one-open
- Boundary: starts from WU4 branch (`feat/collection-company-config-05-auto-sheet`); ends with auto-assign gated by `auto_create_sheet`, one-open/lock scoped to `(company_id, seller_id)`, and list Action using selection company + helper. Does **not** include MCP replay classifier (WU6) or `AGENTS.md` (WU7). Does not change `seller_lookup.py`. ORM auto-sheet OFF naturally affects MCP all-new via ORM — left unchanged.
- Estimated review budget impact: production ~80 authored added+deleted lines; tests ~220. Under the 400-line review budget for production; tests are the bulk. OpenSpec progress checkboxes excluded from authored risk.

## Status

10/14 phase tasks complete (unit 5 of 7). Ready for next batch: **sdd-apply work unit 6**.
