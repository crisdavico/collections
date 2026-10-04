# Apply Progress: two-step-seller-close-and-seller-deposit

**Work unit**: U1 — Lift receipt-value invariants into core **Mode**: Strict TDD
**Attempt token**:
`sha256:679d5877dfe26c95afaf78b48e414fbabcce71ef09e9a0ec6ad0e1aab7dbd9d5`

## Completed Tasks

- [x] 1.1 RED named same-sheet / cross-sheet / cap tests
- [x] 1.2 GREEN sheet-boundary `_check_same_allocation` + batched sheet-wide cap
- [x] 1.3 RED existing `amount_applied` write recomputes
- [x] 1.4 GREEN field-level `depends=` in core; delete satellite `collection_receipt.py`
- [x] 1.5 RED `receipt_value_ids` reverse relation
- [x] 1.6 GREEN inverse o2m; delete satellite constraint overrides; keep
      `_proposal_card_payload`
- [x] 1.7 GREEN sibling split suite + `collection_receipt_proposal/AGENTS.md`
- [x] 1.8 Verify both `--mode=update` suites, upgrade, scoped pre-commit

U2+ remain unchecked.

## TDD Cycle Evidence

| Task | Test File                                                          | Layer       | Safety Net                               | RED                                                    | GREEN                                            | TRIANGULATE                                      | REFACTOR                                  |
| ---- | ------------------------------------------------------------------ | ----------- | ---------------------------------------- | ------------------------------------------------------ | ------------------------------------------------ | ------------------------------------------------ | ----------------------------------------- |
| 1.1  | `collection/tests/test_collection_receipt.py`                      | Integration | Kept over-split / zero / duplicate       | ✅ Written (allocation-boundary ValidationError)       | ✅ After 1.2                                     | ✅ Cross-customer, cross-sheet, over-cap, at-cap | ➖ None needed                            |
| 1.2  | same                                                               | Integration | Batched `search` preserved               | (1.1)                                                  | ✅ 6/6 named+legacy                              | Covered by 1.1 cases                             | ➖ Deleted `:72-73` filter only           |
| 1.3  | same                                                               | Integration | Surplus / equal totals still pass        | ✅ `Cannot convert collection.receipt.line_ids to SQL` | ✅ After 1.4                                     | ✅ Write-to-zero drops from `line_ids`           | ➖ None needed                            |
| 1.4  | same                                                               | Integration | N/A (lift)                               | (1.3)                                                  | ✅ 3/3 then +zero                                | Surplus + equal + rewrite + zero                 | ➖ Copied satellite `depends=` as-is      |
| 1.5  | same                                                               | Integration | N/A (new field)                          | ✅ `'receipt_value_ids' not found`                     | ✅ After 1.6                                     | ✅ Empty o2m when no values                      | ➖ None needed                            |
| 1.6  | same + satellite delete                                            | Integration | Partner-identity relax left in satellite | (1.5)                                                  | ✅ 5/5                                           | Two values vs empty                              | ➖ Removed leftover duplicate method body |
| 1.7  | `collection_receipt_proposal/tests/test_receipt_proposal_split.py` | Integration | 18/18                                    | ➖ Approval (behavior already in core)                 | ✅ 18/18                                         | Existing sibling cases                           | AGENTS.md updated                         |
| 1.8  | both addons                                                        | Integration | See below                                | n/a                                                    | collection 854/854; split 18/18; pre-commit pass | n/a                                              | n/a                                       |

### Test Summary

- **Total tests written (U1)**: 8 new (`cross_customer_same_sheet_accepted`,
  `cross_sheet_refused`, `over_cap_across_customers_refused`, `at_cap_allowed`,
  `existing_applied_write_recomputes`,
  `existing_applied_write_to_zero_drops_from_totals`,
  `reverse_relation_lists_values_on_receipt_value_ids`,
  `reverse_relation_empty_when_voucher_has_no_values`) plus rename of
  over-split/zero/duplicate
- **Layers used**: Integration (Odoo TransactionCase)
- **Approval tests**: sibling split suite (18) still green after satellite constraint
  deletion
- **Pure functions created**: 0

## Work Unit Evidence

| Evidence                 | Result                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused test command     | `docker exec -i seedian-odoo-1 odoo -d devel --http-port=18069 --gevent-port=18072 --test-enable --stop-after-init --workers=0 --test-tags /collection:TestCollectionReceipt.test_cross_customer_same_sheet_accepted,/collection:TestCollectionReceipt.test_cross_sheet_refused,/collection:TestCollectionReceipt.test_over_cap_across_customers_refused,/collection:TestCollectionReceipt.test_at_cap_allowed,/collection:TestCollectionReceipt.test_over_split_on_one_allocation_zero_or_duplicate_refused,/collection:TestCollectionReceipt.test_split_values_across_two_receipts` → **0 failed, 0 error(s) of 6 tests** |
| Focused applied-write    | same runner `--test-tags /collection:TestCollectionReceipt.test_existing_applied_write_recomputes,/collection:TestCollectionReceipt.test_surplus_on_account_totals,/collection:TestCollectionReceipt.test_equal_totals_amount_on_account_zero` → **0 failed, 0 error(s) of 3 tests**                                                                                                                                                                                                                                                                                                                                        |
| Focused reverse relation | `--test-tags` reverse + write-to-zero + cross-customer + at-cap → **0 failed, 0 error(s) of 5 tests**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| Sibling split            | `docker exec -i seedian-odoo-1 odoo -d devel -u collection,collection_receipt_proposal --http-port=18069 --gevent-port=18072 --test-enable --stop-after-init --workers=0 --test-tags /collection_receipt_proposal:TestReceiptProposalSplit` → **0 failed, 0 error(s) of 18 tests**                                                                                                                                                                                                                                                                                                                                          |
| Full collection suite    | `invoke test -m collection --mode=update` → **0 failed, 0 error(s) of 854 tests**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| Full proposal suite      | `invoke test -m collection_receipt_proposal --mode=update` → **2 failed, 1 error(s) of 134 tests** — all three in pre-existing `TestReceiptProposalOrder` (`document_numbers` is not a model field anywhere in either addon; `_compute_line_ids` does not sort). **Not caused by U1.** Split / FIFO / board / actions tests in that run did not fail.                                                                                                                                                                                                                                                                       |
| Runtime harness          | Upgrade both modules via `docker exec -i seedian-odoo-1 odoo -d devel -u collection,collection_receipt_proposal --http-port=18069 --gevent-port=18072 --stop-after-init` (bundled with the split-tag run) — succeeded                                                                                                                                                                                                                                                                                                                                                                                                       |
| Pre-commit               | `pre-commit run --files` on both addons' touched files — **Passed** (after wrapping one E501 docstring)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| Rollback boundary        | Core: `_check_same_allocation` / `_check_voucher_split_cap` / totals `depends=` / `receipt_value_ids`. Satellite: restore `models/collection_receipt.py` + constraint methods on `collection_receipt_value.py`. Does not revert U2+.                                                                                                                                                                                                                                                                                                                                                                                        |

## Files Changed

| File                                                             | Action   | What Was Done                                                                                |
| ---------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------- |
| `collection/tests/test_collection_receipt.py`                    | Modified | Split bundled mismatch test; added cap / totals / reverse-relation tests                     |
| `collection/models/collection_receipt_value.py`                  | Modified | Sheet-boundary constraint; deleted allocation filter in batched cap                          |
| `collection/models/collection_receipt.py`                        | Modified | Field-level `depends=` on three totals                                                       |
| `collection/models/collection_voucher.py`                        | Modified | Inverse o2m `receipt_value_ids`                                                              |
| `collection_receipt_proposal/models/collection_receipt.py`       | Deleted  | `depends=` now in core                                                                       |
| `collection_receipt_proposal/models/__init__.py`                 | Modified | Dropped `collection_receipt` import                                                          |
| `collection_receipt_proposal/models/collection_receipt_value.py` | Modified | Deleted `_check_same_allocation` / `_check_voucher_split_cap`; kept `_proposal_card_payload` |
| `collection_receipt_proposal/AGENTS.md`                          | Modified | Same-sheet/cap and totals `depends=` now core                                                |
| `openspec/changes/.../tasks.md`                                  | Modified | U1 tasks `[x]`                                                                               |
| `openspec/changes/.../apply-progress.md`                         | Created  | This file                                                                                    |

## Deviations from Design

None — implementation matches design. Partner-identity relax
(`_check_voucher_allocation_partner` / `_check_voucher_partners`) was not lifted.

## Issues Found

- `TestReceiptProposalOrder` (3 tests) fail on the full satellite suite independently of
  U1: `document_numbers` is referenced only in that test file (no model field), and
  receipt `line_ids` is an unsorted filtered recordset. U1 did not change
  `_compute_line_ids` or FIFO keys. Do not treat as a U1 regression.
- `docker exec` against `seedian-odoo-1` needs `--http-port` other than 8069 because the
  long-running server already binds it.

## Changed-line estimate

Addon source `git diff --numstat`: **389** authored additions+deletions (collection 240,
satellite 149). Under the 500-line U1 bound. OpenSpec `tasks.md` / `apply-progress.md`
are extra planning artifacts.

## Workload / PR Boundary

- Mode: stacked PR slice (auto-chain / stacked-to-main)
- Current work unit: U1 / PR 1
- Boundary: receipt-value sheet/cap/`depends=`/`receipt_value_ids` lift; satellite
  constraint + totals override deleted
- Next: sdd-apply U2

---

# Apply Progress: two-step-seller-close-and-seller-deposit (U2)

**Work unit**: U2 — Eighth catalog `seller_deposit` and 19.0.1.43.0 migrate **Mode**:
Strict TDD **Attempt token**:
`sha256:99b0c15d37fed1327e7b076fbfa5a9994ed4d50b6dc69d9dfba79c99ef49d934`

U1 evidence above is unchanged. This section appends U2 only.

## Completed Tasks

- [x] 2.1 RED: Eight codes — `EIGHT_TYPE_CODES`, `CATALOG_XMLIDS` len 8, Selection
      includes `seller_deposit`
- [x] 2.2 GREEN: `seller_deposit` Selection + XMLID `document_type_seller_deposit` + JS
      label
- [x] 2.3 RED: Sentinel partner tests — stamp / refuse customer partner / refuse
      customer identification
- [x] 2.4 GREEN: sentinel seed + `_seller_deposit_partner()` + `COLLECTION_TYPE_CODES`
      follows catalog + manifest data
- [x] 2.5 RED: Upgrade to 19.0.1.43.0 unions `seller_deposit`; leftover pin still
      forbids `migrations/19.0.1.42.0/`
- [x] 2.6 GREEN: Manifest `19.0.1.43.0`; `migrations/19.0.1.43.0/post-migrate.py` clones
      1.40.0 union
- [x] 2.7 GREEN: `AGENTS.md` eight catalog + version; stale “submitted dormant”
      replaced; `readme/DESCRIPTION.md` eighth type
- [x] 2.8 Verify: `invoke test -m collection --mode=update`; upgrade `collection`;
      scoped pre-commit

U3+ remain unchecked.

## TDD Cycle Evidence

| Task | Test File                                                                                                                     | Layer       | Safety Net                                                     | RED                                                    | GREEN                                                                                     | TRIANGULATE                                                                   | REFACTOR                                                                                      |
| ---- | ----------------------------------------------------------------------------------------------------------------------------- | ----------- | -------------------------------------------------------------- | ------------------------------------------------------ | ----------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| 2.1  | `tests/test_collection_company_migration.py`, `tests/test_collection_company_settings.py`, `tests/test_collection_voucher.py` | Integration | Kept `SEVEN_TYPE_CODES` as the prior seven                     | ✅ 3 fail + 2 error of 5 (catalog still seven)         | ✅ After 2.2                                                                              | Eight XMLIDs, Selection, persist without dummy partner                        | ➖ `_enable_seller_deposit_type` Command.link until 1.43.0 migrate                            |
| 2.2  | same                                                                                                                          | Integration | Existing seven types unchanged                                 | (2.1)                                                  | ✅ catalog/selection/persist green except env-company allow-list (until 2.6)              | Persist stamps sentinel once 2.4 lands                                        | ➖ JS label only for `seller_deposit` (did not backfill missing echeck/cash/retention labels) |
| 2.3  | `tests/test_collection_voucher.py`                                                                                            | Integration | Non-deposit create still requires a customer partner           | ✅ 2 fail + 1 error of 3                               | ✅ After 2.4                                                                              | Stamp omit-partner; refuse explicit partner; refuse `customer_identification` | ➖ None                                                                                       |
| 2.4  | same                                                                                                                          | Integration | XMLID `collection.partner_seller_deposit`                      | (2.3)                                                  | ✅ 0 failed, 0 error(s) of 4 sentinel/persist tests                                       | Three refuse/stamp paths                                                      | ➖ Function seed instead of `<record model="res.partner">` (see Deviations)                   |
| 2.5  | `tests/test_collection_company_migration.py`                                                                                  | Integration | Leftover pin still lists `19.0.1.42.0`                         | ✅ manifest still 1.42.0; no `migrations/19.0.1.43.0/` | ✅ After 2.6                                                                              | Union keeps extra `wire_143`; no `migrations/19.0.1.42.0/`                    | ➖ None                                                                                       |
| 2.6  | same                                                                                                                          | Integration | Clone of `19.0.1.40.0` `_collection_enable_all_document_types` | (2.5)                                                  | ✅ 0 failed, 0 error(s) of 4 including `test_env_company_allows_all_eight_document_types` | New company eight types; extras kept                                          | ➖ No `__init__.py` (matches 1.40.0)                                                          |
| 2.7  | `AGENTS.md`, `readme/DESCRIPTION.md`                                                                                          | Docs        | Leftover pin sentence kept                                     | ➖ Approval (docs)                                     | ✅ `test_agents_md_five_state_workflow` + `test_manifest_version_is_1_43_0` 0 failed of 2 | Eight catalog in Domain rules; Seller Close writes `submitted`                | ➖ Compact table cells so prettier does not re-pad every map row                              |
| 2.8  | collection addon                                                                                                              | Integration | See below                                                      | n/a                                                    | collection 859/859; pre-commit pass; upgrade loaded partner data XML                      | n/a                                                                           | n/a                                                                                           |

### Test Summary

- **Total tests written (U2)**: catalog/selection/persist
  (`test_document_type_selection_includes_eight_codes`, `test_persist_seller_deposit`,
  catalog eight-count rename), sentinel trio
  (`test_seller_deposit_stamps_sentinel_partner`,
  `test_seller_deposit_refuses_customer_partner`,
  `test_seller_deposit_refuses_customer_identification`), migrate
  (`test_manifest_version_is_1_43_0`,
  `test_upgrade_143_unions_seller_deposit_keeps_extras`)
- **Layers used**: Integration (Odoo TransactionCase)
- **Approval tests**: full `collection` suite 859
- **Pure functions created**: 0

## Work Unit Evidence

| Evidence                          | Result                                                                                                                                                                                                                                                                                                                                     |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Focused catalog/selection         | `--test-tags` company settings + voucher selection/persist (after 2.2) — catalog/selection/persist green; `test_env_company_allows_all_eight_document_types` waited on 2.6                                                                                                                                                                 |
| Focused sentinel                  | `--test-tags` stamp + refuse partner + refuse identification + persist → **0 failed, 0 error(s) of 4 tests**                                                                                                                                                                                                                               |
| Focused migrate                   | `--test-tags /collection:TestCollectionCompanyMigration.test_manifest_version_is_1_43_0,/collection:TestCollectionCompanyMigration.test_upgrade_143_unions_seller_deposit_keeps_extras` plus env-company eight-type — **0 failed, 0 error(s) of 4**                                                                                        |
| Focused AGENTS after compact docs | `docker exec -i seedian-odoo-1 odoo -d devel --http-port=18069 --gevent-port=18072 --test-enable --stop-after-init --workers=0 --test-tags /collection:TestCollectionCompanyMigration.test_agents_md_five_state_workflow,/collection:TestCollectionCompanyMigration.test_manifest_version_is_1_43_0` → **0 failed, 0 error(s) of 2 tests** |
| Full collection suite             | `invoke test -m collection --mode=update` → **0 failed, 0 error(s) of 859 tests**                                                                                                                                                                                                                                                          |
| Runtime harness                   | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --http-port=18069 --gevent-port=18072 --stop-after-init` — succeeded; loaded `data/collection_seller_deposit_partner_data.xml`                                                                                                                                                  |
| Pre-commit                        | `pre-commit run --files` on U2 collection files — **Passed** (E501 docstring wrap; C8101 author warning pre-existing)                                                                                                                                                                                                                      |
| Rollback boundary                 | Revert catalog XMLID, sentinel seed + `_seller_deposit_partner` / `_apply_seller_deposit_partner`, `migrations/19.0.1.43.0/`, manifest `19.0.1.43.0` + data entry, JS label, AGENTS/DESCRIPTION. Do **not** revert U1 receipt-value files. Do **not** add `migrations/19.0.1.42.0/`.                                                       |

## Files Changed

| File                                                        | Action      | What Was Done                                                                                                   |
| ----------------------------------------------------------- | ----------- | --------------------------------------------------------------------------------------------------------------- |
| `tests/test_collection_company_migration.py`                | Modified    | `EIGHT_TYPE_CODES`; manifest 1.43.0 pin; 1.43.0 union test; leftover still forbids `19.0.1.42.0/`               |
| `tests/test_collection_company_settings.py`                 | Modified    | `CATALOG_XMLIDS` eighth row; tests renamed to eight                                                             |
| `tests/test_collection_voucher.py`                          | Modified    | Eight-code Selection; persist + sentinel stamp/refuse tests                                                     |
| `models/collection_common.py`                               | Modified    | `DOCUMENT_TYPE_SELECTION` `seller_deposit`                                                                      |
| `data/collection_document_type_data.xml`                    | Modified    | XMLID `document_type_seller_deposit`                                                                            |
| `static/src/document_review/document_review_helpers.esm.js` | Modified    | `DOCUMENT_TYPE_LABELS.seller_deposit`                                                                           |
| `data/collection_seller_deposit_partner_data.xml`           | Created     | Calls `_collection_ensure_seller_deposit_partner`                                                               |
| `models/res_company.py`                                     | Modified    | `_seller_deposit_partner`, `_collection_ensure_seller_deposit_partner`; `COLLECTION_TYPE_CODES` follows catalog |
| `models/collection_voucher.py`                              | Modified    | `_apply_seller_deposit_partner` on create (U1 `receipt_value_ids` untouched)                                    |
| `__manifest__.py`                                           | Modified    | `19.0.1.43.0`; data entry for sentinel XML                                                                      |
| `migrations/19.0.1.43.0/post-migrate.py`                    | Created     | Clone of 1.40.0 union-all                                                                                       |
| `AGENTS.md`                                                 | Modified    | Eight catalog + 1.43.0; Seller Close writes `submitted`; leftover pin kept                                      |
| `readme/DESCRIPTION.md`                                     | Modified    | Eighth type + sentinel; Seller Close writes `submitted`                                                         |
| `README.rst`, `static/description/index.html`               | Regenerated | OCA `oca-gen-addon-readme` from DESCRIPTION                                                                     |
| `openspec/changes/.../tasks.md`                             | Modified    | U2 tasks `[x]`                                                                                                  |
| `openspec/changes/.../apply-progress.md`                    | Modified    | This U2 append                                                                                                  |

## Deviations from Design

- Sentinel is still XMLID `collection.partner_seller_deposit` with `noupdate=True` on
  `ir.model.data`. Devel leftover `res_partner.autopost_bills` NOT NULL (column present,
  field absent because `account` is not a collection dependency) refused a plain
  `<record model="res.partner">`. Seed is
  `res.company._collection_ensure_seller_deposit_partner()` from XML `<function>` on
  every update (idempotent). A `<data noupdate="1">` wrapper skipped the function on
  `-u` of an already-installed module.
- Repository-map table does not add a Path cell for
  `data/collection_seller_deposit_partner_data.xml` (that path is one character wider
  than the current Path column and prettier re-pads every row). The file and XMLID are
  documented in Domain rules.

## Issues Found

- `test_new_company_copies_sequences_seeds_types_empty_sellers` can flake on leftover
  `fiscalyear_last_day` NOT NULL (same class of account leftover as `autopost_bills`).
  Did not fire on the 859-test 2.8 run.
- `docker exec` against `seedian-odoo-1` needs `--http-port` other than 8069 because the
  long-running server already binds it.

## Changed-line estimate

U2-only nested-git `diff --numstat` on U2 files **412** plus untracked partner XML +
migrate **14** = **426**. `models/collection_voucher.py` still includes U1's 6-line
`receipt_value_ids` in that 23; U2-authored ≈ **420**. Under the 500-line U2 bound.
OpenSpec `tasks.md` / `apply-progress.md` are extra planning artifacts.

## Workload / PR Boundary

- Mode: stacked PR slice (auto-chain / stacked-to-main)
- Current work unit: U2 / PR 2
- Boundary: eighth catalog `seller_deposit`, sentinel partner, manifest `19.0.1.43.0`
  union migrate; no MCP `create_seller_deposit` (U5c); no Confirm-from-submitted (U4)
- Next: sdd-apply U3

---

# Apply Progress: two-step-seller-close-and-seller-deposit (U3)

**Work unit**: U3 — Exclude remittance from collection totals **Mode**: Strict TDD
**Attempt token**:
`sha256:79993daf830917d31e1b44db2b5f3762cf36e765b28a220b4524afa4e2a26a67`

U1 and U2 evidence above is unchanged. This section appends U3 only.

## Completed Tasks

- [x] 3.1 RED: Remittance excluded from collected; Unallocated remittance does not
      mismatch
- [x] 3.2 GREEN: Skip `seller_deposit` in `_collection_report_voucher_blocks`; mismatch
      ignores remittance
- [x] 3.3 RED: Tendered includes remittance echeck and retention + `seller_deposits`;
      keep existing recon keys
- [x] 3.4 GREEN: `_collection_report_tendered` adds `seller_deposits` + `echecks` +
      `retentions`; algebra untouched
- [x] 3.5 RED: XLSX/QWeb show new tendered buckets
- [x] 3.6 GREEN: Recon header/cross-links; QWeb table shows new buckets; formula ladder
      `net_due`/`difference` kept
- [x] 3.7 Verify: `invoke test -m collection --mode=update`; upgrade `collection`;
      scoped pre-commit

U4+ remain unchecked.

## TDD Cycle Evidence

| Task | Test File                                       | Layer       | Safety Net                                              | RED                                                            | GREEN                                                     | TRIANGULATE                                                                                                 | REFACTOR                             |
| ---- | ----------------------------------------------- | ----------- | ------------------------------------------------------- | -------------------------------------------------------------- | --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | ------------------------------------ |
| 3.1  | `tests/test_collection_sheet_report_data.py`    | Integration | ✅ 4/4 catalog/tendered/mismatch/recon                  | ✅ 4 fail of 4 (collected included remittance; mismatch True)  | ✅ After 3.2                                              | Cash 50 vs remittance 80; cash_deposit still collected; unallocated remittance; stray cash still mismatches | ➖ Skip `continue` only              |
| 3.2  | same                                            | Integration | Existing unallocated non-remittance still mismatches    | (3.1)                                                          | ✅ 0 failed of 6                                          | Four 3.1 cases + catalog order + stray voucher                                                              | ➖ Docstring                         |
| 3.3  | same                                            | Integration | `test_tendered_includes_cash_on_hand` still 4-key total | ✅ 1 fail + 2 error of 3 (missing `echecks`/`seller_deposits`) | ✅ After 3.4                                              | Remittance+echeck+retention; existing keys+algebra; cash_deposit ≠ seller_deposits                          | ➖ None                              |
| 3.4  | same                                            | Integration | Recon `net_due`/`difference` formulas unchanged         | (3.3)                                                          | ✅ 0 failed of 6 including cash_on_hand + recon tri-state | Three 3.3 cases                                                                                             | ➖ None needed                       |
| 3.5  | `tests/test_collection_sheet_xlsx.py`           | Integration | Banner/cached/merges still pass                         | ✅ 2 fail of 2 (no Echeqs header; no QWeb t-out)               | ✅ After 3.6                                              | XLSX headers+cached amounts; QWeb arch keys+labels                                                          | ➖ data_only for cross-link formulas |
| 3.6  | same + `report/collection_sheet_xlsx.py` + QWeb | Integration | Formula ladder `net_due`/`difference` cell math kept    | (3.5)                                                          | ✅ 0 failed of 2 then banner/cached/merges                | New cols 7–9; Total at 10; QWeb composition rows                                                            | ➖ Widen recon section merge only    |
| 3.7  | collection addon                                | Integration | See below                                               | n/a                                                            | collection 868/868; pre-commit pass; upgrade loaded QWeb  | n/a                                                                                                         | n/a                                  |

### Test Summary

- **Total tests written (U3)**: 9 (`test_remittance_excluded_from_collected`,
  `test_cash_deposit_still_collected_when_remittance_present`,
  `test_tendered_includes_remittance_echeck_and_retention`,
  `test_tendered_keeps_existing_keys_and_recon_algebra`,
  `test_tendered_cash_deposit_is_not_seller_deposits`,
  `test_unallocated_remittance_does_not_mismatch`,
  `test_unallocated_remittance_does_not_hide_stray_mismatch`,
  `test_xlsx_tendered_shows_echecks_retentions_seller_deposits`,
  `test_qweb_recon_shows_new_tendered_buckets`)
- **Layers used**: Integration (Odoo TransactionCase)
- **Approval tests**: full `collection` suite 868
- **Pure functions created**: 0

## Work Unit Evidence

| Evidence                              | Result                                                                                                                                                                                                                                                                                |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused remittance collected/mismatch | `--test-tags` four 3.1 tests after skip → **0 failed, 0 error(s) of 6** with catalog + stray                                                                                                                                                                                          |
| Focused tendered buckets              | `--test-tags` three 3.3 tests + cash_on_hand + remittance collected + recon tri-state → **0 failed, 0 error(s) of 6**                                                                                                                                                                 |
| Focused XLSX/QWeb                     | `--test-tags` tendered headers + QWeb arch → **0 failed, 0 error(s) of 2**                                                                                                                                                                                                            |
| Full collection suite                 | `invoke test -m collection --mode=update` → **0 failed, 0 error(s) of 868 tests**                                                                                                                                                                                                     |
| Runtime harness                       | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --http-port=18069 --gevent-port=18072 --stop-after-init` — succeeded; loaded QWeb templates                                                                                                                                |
| Pre-commit                            | `pre-commit run --files` on U3 collection + QWeb/XLSX/tests — **Passed**                                                                                                                                                                                                              |
| Rollback boundary                     | Report/XLSX/QWeb tendered+collected paths only: `_collection_report_voucher_blocks` skip, `_collection_report_tendered` keys, `_write_recon` headers/SUM, QWeb recon table. Do **not** revert U1 receipt-value files or U2 catalog/migrate. Do **not** implement `cash_banked` (U5b). |

## Files Changed

| File                                         | Action   | What Was Done                                                                                                            |
| -------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------ |
| `tests/test_collection_sheet_report_data.py` | Modified | Remittance collected/mismatch + tendered bucket tests; seller_deposit helper                                             |
| `models/collection_sheet_report.py`          | Modified | Skip `seller_deposit` voucher blocks; tendered keys `echecks`/`retentions`/`seller_deposits`                             |
| `tests/test_collection_sheet_xlsx.py`        | Modified | XLSX header/amount + QWeb arch tests for new buckets                                                                     |
| `report/collection_sheet_xlsx.py`            | Modified | Recon composition columns Echeqs/Retenciones/Depósitos vendedor; SUM D:J; Total at K; ladder `net_due`/`difference` kept |
| `report/collection_sheet_templates.xml`      | Modified | QWeb recon composition rows for new tendered buckets                                                                     |
| `openspec/changes/.../tasks.md`              | Modified | U3 tasks `[x]`                                                                                                           |
| `openspec/changes/.../apply-progress.md`     | Modified | This U3 append                                                                                                           |

## Deviations from Design

None — implementation matches design. `cash_banked` was not added (U5b). `cash_deposit`
is not summed into `seller_deposits`. Recon algebra stays
`net_due = collected − withheld` and `difference = tendered − net_due`.

## Issues Found

None for U3. `docker exec` against `seedian-odoo-1` still needs `--http-port` other
than 8069.

## Changed-line estimate

U3-only nested-git `diff --numstat`: **355** (report.py 28, templates 56, xlsx 21,
report_data tests 178, xlsx tests 72). Under the 500-line U3 bound. OpenSpec `tasks.md`
/ `apply-progress.md` are extra planning artifacts.

## Workload / PR Boundary

- Mode: stacked PR slice (auto-chain / stacked-to-main)
- Current work unit: U3 / PR 3
- Boundary: remittance out of collected/mismatch; tendered +
  echeck/retention/seller_deposits; XLSX/QWeb buckets. No Seller Close amount drop (U4).
  No `cash_banked` (U5b).
- Next: sdd-apply U4

---

**Work unit**: U4 — Two-step seller close **Mode**: Strict TDD **Attempt token**:
`sha256:e0460b0af956a673693995b17976b21b7c81738d3bc77bf5bf2eac14593eeaef`

U1–U3 evidence above is unchanged. This section appends U4 only.

## Completed Tasks

- [x] 4.1 RED: Open sheet closes to submitted without amounts; Amounts on close refused
- [x] 4.2 GREEN: `action_seller_close` drops amount vals (keep kwargs `=None`);
      amount-free schema; `cash.collected`
- [x] 4.3 RED: Submitted sheet accepts Declare Cash; re-runnable; Non-submitted refused;
      Disabled seller may still declare
- [x] 4.4 GREEN: `SELLER_DECLARATION_STATES = frozenset({"submitted"})`;
      `action_declare_cash`; invert recon window; keep `cash_on_hand` string Cash to
      Administration; views readonly on submitted
- [x] 4.5 RED: MCP `declare_collection_cash` tests
      (`tests/test_collection_mcp_cash_declare.py`)
- [x] 4.6 GREEN: `tools/collection_cash_declare.py` + `_submitted_sheets_for_seller`;
      import in `tools/__init__.py`
- [x] 4.7 RED: Undeclared cash blocks Confirm; Zero cash Confirm without declaration;
      Declared cash allows Confirm
- [x] 4.8 GREEN: Confirm gate when collected cash > 0 and `cash_declared_at` unset
- [x] 4.9 RED: PDF Submitted sheet returns base64; Open preferred over submitted; More
      than one submitted fails closed
- [x] 4.10 GREEN: Widen `tools/sheet_report.py` call site only (0 open → one submitted).
      `_open_sheets_for_seller` unchanged
- [x] 4.11 GREEN: UI/xlsx/mail tests; `AGENTS.md` MCP contracts; leftover scanner still
      forbids new `"open"` gates
- [x] 4.12 Verify: `invoke test -m collection --mode=update`; upgrade `collection`;
      scoped pre-commit

U5a+ remain unchecked.

## TDD Cycle Evidence

| Task | Test File                                                                    | Layer       | Safety Net                                   | RED                                              | GREEN                                               | TRIANGULATE                                                                      | REFACTOR                         |
| ---- | ---------------------------------------------------------------------------- | ----------- | -------------------------------------------- | ------------------------------------------------ | --------------------------------------------------- | -------------------------------------------------------------------------------- | -------------------------------- |
| 4.1  | `tests/test_collection_sheet.py`, `tests/test_collection_mcp_sheet_close.py` | Integration | Existing Seller Close + one-open             | ✅ Amount-free close + extra-key refuse          | ✅ After 4.2                                        | Kwargs ignored; MCP seller_id-only; `cash.collected`                             | ➖ Keep kwargs `=None`           |
| 4.2  | same + `tools/collection_sheet_close.py`                                     | Integration | Draft-voucher Seller Close refuse kept       | (4.1)                                            | ✅ Close writes `{"state": "submitted"}` only       | Cash SUM vs zero collected                                                       | ➖ Schema drop amounts           |
| 4.3  | `tests/test_collection_sheet.py`                                             | Integration | One-open still `open` only                   | ✅ Declare on submitted / refuse others          | ✅ After 4.4                                        | Re-runnable; disabled seller; cancel-between-states                              | ➖ Named frozenset               |
| 4.4  | `collection_common.py` + recon write + views                                 | Integration | Frozen recon + leftover scanner              | (4.3)                                            | ✅ Decls only while submitted                       | Open freezes decls; submitted accepts; combined raw write                        | ➖ Invert combined-write message |
| 4.5  | `tests/test_collection_mcp_cash_declare.py`                                  | Integration | MCP close/PDF patterns                       | ✅ 8 scenarios (new file)                        | ✅ After 4.6                                        | Success, 0-submitted UserError not null, sheet_id, open not target, non-internal | ➖ No `_open_sheets_for_seller`  |
| 4.6  | `tools/collection_cash_declare.py`                                           | Integration | Multi-open UserError reused                  | (4.5)                                            | ✅ 8/8 after `-u collection`                        | `_submitted_sheets_for_seller`                                                   | ➖ Import in `tools/__init__.py` |
| 4.7  | `tests/test_collection_sheet.py`                                             | Integration | Empty-member Confirm still passes            | ✅ Undeclared cash / zero / declared             | ✅ After 4.8                                        | Zero cash no declare; cash + declare; allocations stay draft                     | ➖ E501 wrap                     |
| 4.8  | `collection_sheet.py` `action_confirm`                                       | Integration | Member `validated_collections` gate kept     | (4.7)                                            | ✅ `compare_amounts` + `cash_declared_at`           | Collected > 0 vs 0                                                               | ➖ None needed                   |
| 4.9  | `tests/test_collection_mcp_sheet_pdf.py`                                     | Integration | `{sheet: null}` no-open kept                 | ✅ Submitted PDF / prefer open / multi-submitted | ✅ After 4.10                                       | Open preferred; `>1` submitted same UserError                                    | ➖ E501 wrap                     |
| 4.10 | `tools/sheet_report.py` call site                                            | Integration | `_open_sheets_for_seller` body unchanged     | (4.9)                                            | ✅ 0 open → one submitted                           | 0/0 null; 1 submitted render                                                     | ➖ Helper not widened            |
| 4.11 | UI / xlsx / mail / leftover / AGENTS                                         | Integration | Leftover scanner still no new `"open"` gates | ➖ Approval (docs+readonly)                      | ✅ 6/6 focused                                      | Readonly `submitted`; xlsx declare-on-submitted; chatter; named set              | ➖ Combined-write invert         |
| 4.12 | collection addon                                                             | Integration | See below                                    | n/a                                              | collection 890/890; pre-commit pass; upgrade loaded | n/a                                                                              | n/a                              |

### Test Summary

- **Total tests written (U4)**: amount-free Seller Close + Declare Cash (ORM + MCP) +
  Confirm cash gate + PDF submitted fallback + UI/xlsx/mail leftover
- **Layers used**: Integration (Odoo TransactionCase)
- **Approval tests**: full `collection` suite 890
- **Pure functions created**: 0 (`_cash_collected_total` /
  `_submitted_sheets_for_seller` are model helpers)

## Work Unit Evidence

| Evidence                                  | Result                                                                                                                                                                                                                                                                                                                                                                          |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused 4.11 UI/mail/xlsx/leftover/AGENTS | `--test-tags` form readonly + declare chatter + five-state xlsx + named sets + leftover scanner + AGENTS five-state → **0 failed, 0 error(s) of 6 tests**                                                                                                                                                                                                                       |
| First full suite                          | `invoke test -m collection --mode=update` → **1 failed, 0 error(s) of 890** — `test_raw_combined_declaration_and_submitted_write_refused` still expected `"Seller Close"`; inverted to submitted-decl message                                                                                                                                                                   |
| Full collection suite (after invert)      | `invoke test -m collection --mode=update` → **0 failed, 0 error(s) of 890 tests**                                                                                                                                                                                                                                                                                               |
| Runtime harness                           | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --http-port=18069 --gevent-port=18072 --stop-after-init` — succeeded                                                                                                                                                                                                                                                 |
| Pre-commit                                | `pre-commit run --files` on U4 collection files — **Passed** (after wrapping two E501 asserts)                                                                                                                                                                                                                                                                                  |
| Rollback boundary                         | Amount-free `action_seller_close` + MCP schema; `action_declare_cash` / `declare_collection_cash`; recon window `submitted`; Confirm cash gate; PDF call-site submitted fallback. Do **not** revert U1–U3. Do **not** implement `create_seller_deposit` or the replacement ledger (U5a). Do **not** change `_open_sheets_for_seller`. Do **not** add `migrations/19.0.1.42.0/`. |

## Files Changed

| File                                         | Action   | What Was Done                                                                                                                |
| -------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `models/collection_common.py`                | Modified | `SELLER_DECLARATION_STATES = frozenset({"submitted"})`                                                                       |
| `models/collection_sheet.py`                 | Modified | Amount-free Seller Close; `_cash_collected_total`; `action_declare_cash`; `_submitted_sheets_for_seller`; Confirm cash gate  |
| `models/collection_sheet_report.py`          | Modified | Invert decl write window to submitted; `cash_on_hand` string Cash to Administration; `cash_declared_at` / `cash_declared_by` |
| `tools/collection_sheet_close.py`            | Modified | Seller-id-only schema; extra keys refused; return `cash.collected`                                                           |
| `tools/collection_cash_declare.py`           | Created  | MCP `declare_collection_cash` via `_submitted_sheets_for_seller`                                                             |
| `tools/__init__.py`                          | Modified | Import declare mixin                                                                                                         |
| `tools/sheet_report.py`                      | Modified | Call site: 0 open → one submitted; helper unchanged                                                                          |
| `views/collection_views.xml`                 | Modified | Cash/withheld `readonly="state != 'submitted'"`                                                                              |
| `tests/test_collection_sheet.py`             | Modified | Amount-free close; Declare Cash; Confirm gate                                                                                |
| `tests/test_collection_mcp_sheet_close.py`   | Modified | Amount-free schema + `cash.collected`                                                                                        |
| `tests/test_collection_mcp_cash_declare.py`  | Created  | Declare MCP scenarios                                                                                                        |
| `tests/test_collection_mcp_sheet_pdf.py`     | Modified | Submitted serve / open preferred / multi-submitted                                                                           |
| `tests/test_collection_sheet_report_data.py` | Modified | Invert decl window; combined raw write expects submitted-decl error                                                          |
| `tests/test_collection_ui.py`                | Modified | Readonly asserts `submitted` not `open`                                                                                      |
| `tests/test_collection_mail.py`              | Modified | Declare Cash tracking                                                                                                        |
| `tests/test_collection_sheet_xlsx.py`        | Modified | Five-state export declares cash on submitted                                                                                 |
| `tests/test_collection_company_migration.py` | Modified | Named `SELLER_DECLARATION_STATES`; leftover scanner unchanged                                                                |
| `tests/__init__.py`                          | Modified | Import cash-declare tests                                                                                                    |
| `AGENTS.md`                                  | Modified | Amount-free close, Declare Cash, Confirm from submitted, PDF fallback, leftover pin kept                                     |
| `openspec/changes/.../tasks.md`              | Modified | U4 tasks `[x]`                                                                                                               |
| `openspec/changes/.../apply-progress.md`     | Modified | This U4 append                                                                                                               |

## Deviations from Design

None — implementation matches design U4. Column remains `cash_on_hand` (`string=` Cash
to Administration). Combined raw `write({decls, state: submitted})` on an open sheet now
raises the declaration-window UserError (decls checked before the state intercept),
still refused, still unpersisted.

## Issues Found

- First 4.12 suite: 1 fail of 890 on leftover combined-write assertion (`"Seller Close"`
  vs submitted-decl message). Fixed by inverting the test; second suite 0/890.
- `docker exec` against `seedian-odoo-1` still needs `--http-port` other than 8069.

## Changed-line estimate

U4-authored (exclusive files + U3-overlap deltas): new declare tool/tests **278**;
sheet/close/PDF/views/tools **~223**; sheet/MCP/PDF/UI/mail tests **~277**; recon invert
leftover **~54**; AGENTS MCP rewrite extra. Gross on U4-touched paths is higher because
U1–U3 remain uncommitted in the nested repo. Slice is near the **700** U4 bound;
production is well under. OpenSpec `tasks.md` / `apply-progress.md` are extra planning
artifacts.

## Workload / PR Boundary

- Mode: stacked PR slice (auto-chain / stacked-to-main)
- Current work unit: U4 / PR 4
- Boundary: amount-free Seller Close; Declare Cash on `submitted`; Confirm
  cash-declaration gate; PDF call-site submitted fallback. No `create_seller_deposit`.
  No replacement ledger (U5a). `_open_sheets_for_seller` not widened. No
  `migrations/19.0.1.42.0/`.
- Next: sdd-apply U5a

---

# Apply Progress: two-step-seller-close-and-seller-deposit (U5a)

**Work unit**: U5a — Replacement ledger + exact-cent primitives + `replaced_amount`
**Mode**: Strict TDD **Attempt token**:
`sha256:3f28cfdd1c34d4ec4e0e7074ef47ea91b57117aa4149e5375c9737e38d0c7498` (provided; not
acquired — no attempt store in this executor; do not settle/reset)

U1–U4 evidence above is unchanged. This section appends U5a only.

## Completed Tasks

- [x] 5.1 RED: Ledger ACL `1,0,1,0` + company `ir.rule`; Write refused; Draft allocation
      unlink cascades replacements
- [x] 5.2 GREEN: `collection.cash.replacement` (revision pattern); ACL + company
      `ir.rule`; `@api.ondelete` exempts `collection_allocation_parent_unlink`
- [x] 5.3 RED: Zero slice skipped; Currency mismatch refused; Same-receipt totals
      unchanged
- [x] 5.4 GREEN: `_shrink_or_unlink` / `_grow_voucher_amount` /
      `_assert_replacement_currencies`; `_cash_replace` / `_cash_reverse`
- [x] 5.5 RED: `replaced_amount` = Σreplace − Σreverse
- [x] 5.6 GREEN: voucher compute; `_receipt_get_or_create`; satellite shrink/grow/
      get-or-create wrappers; Reverse API exists; Cancel does not call it
- [x] 5.7 Verify: collection `--mode=update` 903/903; upgrade; scoped pre-commit;
      sibling split+fifo 38/38

U6+ remain unchecked.

## TDD Cycle Evidence

| Task | Test File                                                                 | Layer       | Safety Net                    | RED                                     | GREEN                                                 | TRIANGULATE                                                          | REFACTOR                                                            |
| ---- | ------------------------------------------------------------------------- | ----------- | ----------------------------- | --------------------------------------- | ----------------------------------------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------- |
| 5.1  | `tests/test_collection_acl.py`, `tests/test_collection_allocation_acl.py` | Integration | Snapshot/revision ACL helpers | ✅ ACL 0 rows; KeyError missing model   | ✅ After 5.2, 5/5                                     | Gated create; write refused; parent-unlink cascade; XML company rule | ➖ Dropped live other-company hide (`fiscalyear_last_day` leftover) |
| 5.2  | same                                                                      | Integration | Revision pattern              | (5.1)                                   | ✅ 0 failed of 5 after `-u collection`                | Cascade keeps vouchers                                               | ➖ No receipt One2many (PG cascade)                                 |
| 5.3  | `tests/test_collection_cash_replacement.py`                               | Integration | N/A (new)                     | ✅ AttributeError `_cash_replace` (5/5) | ✅ After 5.4                                          | Zero + 0.001; mismatch; 40 keep totals; full unlink; over-slice skip | ➖ Shared `_cash_move`                                              |
| 5.4  | same + `collection_receipt_value.py`                                      | Integration | Split cap / freeze untouched  | (5.3)                                   | ✅ 0 failed of 5                                      | Five slicing cases                                                   | ➖ Wrappers later in 5.6                                            |
| 5.5  | same                                                                      | Integration | Totals still 100/70           | ✅ `'replaced_amount' not found`        | ✅ After 5.6                                          | Replace 40; reverse 10 → 30                                          | ➖ Inverse o2m on cash voucher                                      |
| 5.6  | same + satellite wrappers                                                 | Integration | Board transfer still merges   | ➖ Cancel source scan (approval)        | ✅ 0 failed of 9; get-or-create 2 paths               | Reuse invoice receipt; create quotation                              | ➖ Satellite delegates only                                         |
| 5.7  | collection + sibling split/fifo                                           | Integration | See below                     | n/a                                     | collection 903/903; split+fifo 38/38; pre-commit pass | n/a                                                                  | n/a                                                                 |

### Test Summary

- **Total tests written (U5a)**: 13 (ACL/company/write/cascade 4; slicing/ledger 9)
- **Layers used**: Integration (Odoo TransactionCase)
- **Approval tests**: full `collection` suite 903; sibling split+fifo 38
- **Pure functions created**: 0 (ORM primitives)

## Work Unit Evidence

| Evidence              | Result                                                                                                                                                                                                                                                                               |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Focused 5.2 ACL       | `--test-tags` five ACL/write/cascade/rule tests after `-u collection` → **0 failed, 0 error(s) of 5 tests**                                                                                                                                                                          |
| Focused 5.4 slicing   | `--test-tags /collection:TestCollectionCashReplacement` after primitives → **0 failed, 0 error(s) of 5 tests**                                                                                                                                                                       |
| Focused 5.6           | same tag after compute/wrappers → **0 failed, 0 error(s) of 9 tests**                                                                                                                                                                                                                |
| Sibling split/fifo    | `--test-tags /collection_receipt_proposal:TestReceiptProposalSplit,/collection_receipt_proposal:TestReceiptProposalFifo` → **0 failed, 0 error(s) of 38 tests**                                                                                                                      |
| Full collection suite | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --http-port=18069 --gevent-port=18072 --test-enable --stop-after-init --workers=0 --test-tags /collection` → **0 failed, 0 error(s) of 903 tests**                                                                        |
| Runtime harness       | Same command upgraded `collection` (new model + ACL + `ir.rule`)                                                                                                                                                                                                                     |
| Pre-commit            | `pre-commit run --files` on U5a collection + satellite files — **Passed**                                                                                                                                                                                                            |
| Rollback boundary     | `collection.cash.replacement` + ACL/ir.rule; shrink/grow/`_cash_replace`/`_cash_reverse`; `replaced_amount`; `_receipt_get_or_create`; satellite wrappers. Do **not** revert U1–U4. Do **not** implement write-hook/`cash_banked` (U5b), deposit MCP (U5c), or board pool lock (U6). |

## Files Changed

| File                                                          | Action   | What Was Done                                                       |
| ------------------------------------------------------------- | -------- | ------------------------------------------------------------------- |
| `collection/models/collection_cash_replacement.py`            | Created  | Immutable ledger; gated create; write raise; parent-unlink ondelete |
| `collection/models/__init__.py`                               | Modified | Import ledger                                                       |
| `collection/security/ir.model.access.csv`                     | Modified | `1,0,1,0`                                                           |
| `collection/security/collection_security.xml`                 | Modified | Global company `ir.rule`                                            |
| `collection/models/collection_receipt_value.py`               | Modified | Currency-agreement; shrink/grow; `_cash_replace` / `_cash_reverse`  |
| `collection/models/collection_voucher.py`                     | Modified | `cash_replacement_ids`; `replaced_amount` compute                   |
| `collection/models/collection_allocation.py`                  | Modified | `_receipt_get_or_create`                                            |
| `collection/tests/test_collection_acl.py`                     | Modified | ACL 1,0,1,0 + write refused                                         |
| `collection/tests/test_collection_allocation_acl.py`          | Modified | `_assert_acl`; cascade unlink; company rule list                    |
| `collection/tests/test_collection_cash_replacement.py`        | Created  | Slicing, totals, replaced_amount, reverse, get-or-create, Cancel    |
| `collection/tests/__init__.py`                                | Modified | Import cash-replacement tests                                       |
| `collection_receipt_proposal/models/collection_sheet.py`      | Modified | Shrink/grow wrappers of core primitives                             |
| `collection_receipt_proposal/models/collection_allocation.py` | Modified | `_proposal_receipt_get_or_create` delegates to core                 |
| `openspec/changes/.../tasks.md`                               | Modified | U5a tasks `[x]`                                                     |
| `openspec/changes/.../apply-progress.md`                      | Modified | This U5a append                                                     |

## Deviations from Design

- Live other-company hide for the ledger is covered by the XML `ir.rule` assertion (same
  domain as every other collection model). A new-company hide fixture hit leftover
  `res_company.fiscalyear_last_day` NOT NULL and was dropped rather than copying the
  XLSX leftover-column helper into this slice.
- No `One2many` from receipt to replacements: unlink ACL is `0`, so cascade is
  PostgreSQL `ondelete="cascade"` on `receipt_id` (as designed). Inverse o2m lives only
  on the cash voucher for `replaced_amount`.
- `_cash_replace` / `_cash_reverse` live on `collection.receipt.value` (task 5.4 file)
  and share `_cash_move`.

## Issues Found

- `docker exec` against `seedian-odoo-1` still needs `--http-port` other than 8069.
- Nested `collection` git still has U1–U4 uncommitted, so `git diff --numstat` on
  `collection_receipt_value.py` / `collection_voucher.py` mixes prior units.

## Changed-line estimate

U5a-authored ≈ **680** (new model+tests 310; ACL tests 181;
primitives/compute/get-or-create ~155; security 6; satellite wrapper churn 30). Under
the 700-line U5a bound. Mixed-file `git diff` on `collection_receipt_value.py` still
includes U1. OpenSpec `tasks.md` / `apply-progress.md` are extra planning artifacts.

## Workload / PR Boundary

- Mode: stacked PR slice (auto-chain / stacked-to-main)
- Current work unit: U5a / PR 5
- Boundary: ledger + exact-cent primitives + `replaced_amount` + satellite shrink/grow
  wrappers. No write-hook / ordering engine / `cash_banked` (U5b). No deposit MCP (U5c).
  No board pool lock (U6).
- Next: sdd-apply U6

---

# Apply Progress: two-step-seller-close-and-seller-deposit (U6)

**Work unit**: U6 — Board lock: free − replaced; remittance not draggable **Mode**:
Strict TDD **Attempt token**:
`sha256:ec9cfa905fccd1fe80a377030b7ca36f3933d7819d79f39c14f2679158b385d6` (provided; not
acquired — no attempt store in this executor; do not settle/reset)

U1–U5a evidence above is unchanged. This section appends U6 only. No U5b write-hook and
no `create_seller_deposit`.

## Completed Tasks

- [x] 6.1 RED: Replaced cash leaves the pool; Partial replace remains only for the free
      remainder
- [x] 6.2 GREEN: `proposal_free_amount = amount − assigned − replaced_amount`
- [x] 6.3 RED: Remittance is not pool-draggable; Replaced cash keeps allocation_id
- [x] 6.4 GREEN: Guard `_proposal_transfer_plan` pool path and
      `_proposal_sync_voucher_owner` against `seller_deposit`; remittance off the pool
- [x] 6.5 GREEN: `collection_receipt_proposal/AGENTS.md` board lock; largest-share owner
      stays in satellite
- [x] 6.6 Verify: both `--mode=update` suites; upgrade both modules; scoped pre-commit

U5b+ remain unchecked.

## TDD Cycle Evidence

| Task | Test File                              | Layer       | Safety Net                                                 | RED                                                                     | GREEN                                               | TRIANGULATE                                                                      | REFACTOR                                       |
| ---- | -------------------------------------- | ----------- | ---------------------------------------------------------- | ----------------------------------------------------------------------- | --------------------------------------------------- | -------------------------------------------------------------------------------- | ---------------------------------------------- |
| 6.1  | `tests/test_receipt_proposal_board.py` | Integration | Board/actions/split/fifo 86/87 (company-rule pre-existing) | ✅ 2/2 fail (`proposal_free_amount` still 100)                          | ✅ After 6.2                                        | Full replace off pool; partial remainder 60                                      | ➖ Formula only                                |
| 6.2  | `models/collection_voucher.py`         | Integration | Existing free-amount tests still 0 replaced                | (6.1)                                                                   | ✅ 0 failed of 2                                    | Two cash cases                                                                   | ➖ `depends` includes `replaced_amount`        |
| 6.3  | actions + split + board excess         | Integration | Owner-follows-largest still green                          | ✅ 4/4 fail (transfer succeeded; pool listed deposit; sync cleared/set) | ✅ After 6.4                                        | Remittance transfer; remittance sync skip; replaced keep; excess not a pool card | ➖ `_confirm` declares cash when collected > 0 |
| 6.4  | `models/collection_sheet.py`           | Integration | Pool path still uses free amount as max                    | (6.3)                                                                   | ✅ 0 failed of 6 U6 tests                           | Pool filter + transfer UserError + skip remittance + keep replaced owner         | ✅ Docstring on `_proposal_sync_voucher_owner` |
| 6.5  | `AGENTS.md`                            | Docs        | Largest-share paragraph kept                               | ➖ Approval (docs)                                                      | ✅ Board-lock bullets                               | Pool mapping excludes remittance                                                 | ➖ Table pad                                   |
| 6.6  | both addons                            | Integration | See below                                                  | n/a                                                                     | collection 903/903; focused 92/93; proposal 136/140 | n/a                                                                              | n/a                                            |

### Test Summary

- **Total tests written (U6)**: 6 (`test_replaced_cash_leaves_the_pool`,
  `test_partial_replace_remains_only_for_the_free_remainder`,
  `test_excess_deposit_is_not_a_pool_card`, `test_remittance_is_not_pool_draggable`,
  `test_replaced_cash_keeps_allocation_id`,
  `test_remittance_does_not_receive_allocation_id_from_owner_sync`)
- **Layers used**: Integration (Odoo TransactionCase)
- **Approval tests**: collection 903; board/actions/split/fifo excluding the
  pre-existing company-rule fail
- **Pure functions created**: 0

## Work Unit Evidence

| Evidence                 | Result                                                                                                                                                                                                                                                                          |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused 6.1 RED          | `--test-tags` two replaced-cash pool tests → **2 failed of 2** (`100.0 != 0.0` / `100.0 != 60.0`)                                                                                                                                                                               |
| Focused 6.2 GREEN        | same two tags after formula → **0 failed, 0 error(s) of 2 tests**                                                                                                                                                                                                               |
| Focused 6.3 RED          | remittance transfer + owner-sync + excess pool → **4 failed of 4**                                                                                                                                                                                                              |
| Focused 6.4 GREEN        | six U6 tags → **0 failed, 0 error(s) of 6 tests**                                                                                                                                                                                                                               |
| Board/actions/split/fifo | `--test-tags` four classes → **1 failed, 0 error(s) of 93 tests** — only `test_sheet_company_rule_still_guards_the_board` (same fail in safety net before U6 production edits). All six U6 tests, FIFO, split, and other board/actions tests passed                             |
| Full collection suite    | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --http-port=18069 --gevent-port=18072 --test-enable --stop-after-init --workers=0 --test-tags /collection` → **0 failed, 0 error(s) of 903 tests**                                                                   |
| Full proposal suite      | `-u collection_receipt_proposal --test-tags /collection_receipt_proposal` → **3 failed, 1 error(s) of 140 tests**. Pre-existing: `TestReceiptProposalOrder` (1 error `document_numbers` missing + 2 FAIL fifo-key) and board company-rule. **Not U6.**                          |
| Runtime harness          | Upgrade `collection` and `collection_receipt_proposal` bundled with the suite runs (`-u`) — succeeded                                                                                                                                                                           |
| Pre-commit               | `pre-commit run --files` on U6 satellite + OpenSpec paths — **Passed** (W8138 except-pass on pre-existing company-rule test)                                                                                                                                                    |
| Rollback boundary        | Satellite `proposal_free_amount` formula; pool filter; `_proposal_transfer_plan` remittance UserError; `_proposal_sync_voucher_owner` remittance skip + replaced-cash keep. Do **not** revert U1–U5a. Do **not** implement write-hook/`cash_banked` (U5b) or deposit MCP (U5c). |

## Files Changed

| File                                                                 | Action   | What Was Done                                                                                                           |
| -------------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------- |
| `collection_receipt_proposal/models/collection_voucher.py`           | Modified | Free amount subtracts `replaced_amount`; depends includes it                                                            |
| `collection_receipt_proposal/models/collection_sheet.py`             | Modified | Pool skips `seller_deposit`; pool-path transfer refuses remittance; owner sync skips remittance and keeps replaced cash |
| `collection_receipt_proposal/tests/common.py`                        | Modified | Seller-deposit helpers; `_cash_replace`; `_confirm` declares cash when collected > 0                                    |
| `collection_receipt_proposal/tests/test_receipt_proposal_board.py`   | Modified | Replaced cash pool tests; excess deposit not a pool card                                                                |
| `collection_receipt_proposal/tests/test_receipt_proposal_actions.py` | Modified | Remittance pool transfer refused                                                                                        |
| `collection_receipt_proposal/tests/test_receipt_proposal_split.py`   | Modified | Replaced cash keeps `allocation_id`; remittance never receives it                                                       |
| `collection_receipt_proposal/AGENTS.md`                              | Modified | Board lock; largest-share owner stays in satellite                                                                      |
| `openspec/changes/.../tasks.md`                                      | Modified | U6 tasks `[x]`                                                                                                          |
| `openspec/changes/.../apply-progress.md`                             | Modified | This U6 append                                                                                                          |

## Deviations from Design

None — implementation matches design U6. Remittance is excluded from the pool list in
addition to the transfer-plan UserError so an excess `seller_deposit` is not a pool
card. Tests call core `_cash_replace` (U5a); no U5b write-hook.

## Issues Found

- `TestReceiptProposalOrder` (3 tests) still fail independently of U6
  (`document_numbers` missing; `_compute_line_ids` order). Same as U1 report.
- `TestReceiptProposalBoard.test_sheet_company_rule_still_guards_the_board` failed in
  the U6 safety net **before** production edits and still fails. Other-company RPC does
  not refuse on this devel DB. Not treated as a U6 regression.
- `docker exec` against `seedian-odoo-1` still needs `--http-port` other than 8069.

## Changed-line estimate

Satellite nested-git `diff --numstat` on U6 files: **279** (218 insertions, 61
deletions). Under the 400-line U6 bound. OpenSpec `tasks.md` / `apply-progress.md` are
extra planning artifacts. No core `collection` production files in this slice.

## Workload / PR Boundary

- Mode: stacked PR slice (auto-chain / stacked-to-main)
- Current work unit: U6 / PR 6
- Boundary: board free-amount lock, remittance not pool-draggable, replaced cash keeps
  `allocation_id`. No write-hook / ordering engine / `cash_banked` (U5b). No deposit MCP
  (U5c).
- Next: sdd-apply U5b

---

# Apply Progress: two-step-seller-close-and-seller-deposit (U5b)

**Work unit**: U5b — Ordering engine + `validated_collections` write-hook +
`cash_banked` **Mode**: Strict TDD **Attempt token**:
`sha256:337ff77e76aab7a5dc4c63432e0b9df81bf01d69bcc00dc6206df51f33960f91` (provided; not
acquired — no attempt store in this executor; do not settle/reset)

U1–U6 evidence above is unchanged. This section appends U5b only. No
`create_seller_deposit` (U5c).

## Completed Tasks

- [x] 7.1 RED: Deposit validation replaces cash; Review-off still replace;
      Non-transition does not re-replace; No allocations no-op; Cancel does not reverse
- [x] 7.2 GREEN: Write-hook on `collection_voucher.py` entering `validated_collections`
      for `seller_deposit` only (audited write, not `action_review_approve`)
- [x] 7.3 RED: Quotation before invoice; within kind `_proposal_fifo_key`; within bucket
      oldest cash `create_date`
- [x] 7.4 GREEN: Ordering engine calling U5a `_cash_replace` on the same receipt;
      `amount_applied` unchanged
- [x] 7.5 RED: `cash_banked` sums `seller_deposit` only; excess still banks; no
      allocations still banks from vouchers
- [x] 7.6 GREEN: Computed `cash_banked` / `cash_collected` on
      `collection_sheet_report.py` from vouchers, never the ledger
- [x] 7.7 Verify: collection `--mode=update` 914/914; upgrade; scoped pre-commit

U5c remains unchecked.

## TDD Cycle Evidence

| Task | Test File                                    | Layer       | Safety Net                         | RED                                               | GREEN                                             | TRIANGULATE                                                   | REFACTOR                                       |
| ---- | -------------------------------------------- | ----------- | ---------------------------------- | ------------------------------------------------- | ------------------------------------------------- | ------------------------------------------------------------- | ---------------------------------------------- |
| 7.1  | `tests/test_collection_cash_replacement.py`  | Integration | ✅ 9/9 U5a primitives              | ✅ 4 fail of 5 (0 replacement rows)               | ✅ After 7.2                                      | Validate; review-off; non-transition; no-op; Cancel+Reinstate | ➖ Helpers `_submit` / `_validate_collections` |
| 7.2  | `models/collection_voucher.py`               | Integration | Intercept still requires audited   | (7.1)                                             | ✅ 14/14 including U5a                            | Hook only on entering `validated_collections`                 | ➖ Not on `action_review_approve`              |
| 7.3  | same                                         | Integration | Invoice-only path still 40         | ✅ 3/3 fail (id order: invoice/later/newer first) | ✅ After 7.4                                      | Quotation first; earlier due_date; oldest `create_date`       | ➖ Remainder 10 keeps value                    |
| 7.4  | same                                         | Integration | Totals / `amount_applied` kept     | (7.3)                                             | ✅ 17/17                                          | Same-receipt grow; FIFO key min of applications               | ✅ Cash upload key wrap                        |
| 7.5  | `tests/test_collection_sheet_report_data.py` | Integration | Remittance collected/tendered kept | ✅ 3 error + 1 fail (`cash_banked` missing)       | ✅ After 7.6                                      | 80 vs cash_deposit 20; excess 80 vs cash 50; no allocations   | ➖ PAYLOAD_KEYS                                |
| 7.6  | `models/collection_sheet_report.py`          | Integration | `_cash_collected_total` Confirm    | (7.5)                                             | ✅ 5/5 payload + banked                           | Field + payload; `_cash_collected_total` reads compute        | ➖ Helper delegates to `cash_collected`        |
| 7.7  | collection addon                             | Integration | See below                          | n/a                                               | collection 914/914; pre-commit pass; `-u` upgrade | n/a                                                           | n/a                                            |

### Test Summary

- **Total tests written (U5b)**: 11 (`test_deposit_validation_replaces_cash`,
  `test_review_off_companies_still_replace`,
  `test_non_transition_write_does_not_re_replace`, `test_no_allocations_is_a_no_op`,
  `test_cancel_then_reinstate_does_not_reverse`, `test_quotation_before_invoice`,
  `test_within_kind_uses_proposal_fifo_key`,
  `test_within_bucket_oldest_cash_create_date`,
  `test_cash_banked_sums_seller_deposit_only`, `test_excess_deposit_still_banks`,
  `test_no_allocations_still_banks_from_vouchers`)
- **Layers used**: Integration (Odoo TransactionCase)
- **Approval tests**: full `collection` suite 914
- **Pure functions created**: 3 (`_replacement_fifo_key`,
  `_replacement_receipt_fifo_key`, `_replacement_cash_upload_key`)

## Work Unit Evidence

| Evidence              | Result                                                                                                                                                                                                        |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused 7.1 RED       | `--test-tags` five trigger tests → **4 failed of 5** (`0 != 1` rows); no-op already empty                                                                                                                     |
| Focused 7.2 GREEN     | `--test-tags /collection:TestCollectionCashReplacement` → **0 failed, 0 error(s) of 14 tests**                                                                                                                |
| Focused 7.3 RED       | three ordering tags → **3 failed of 3** (quotation value kept; later due consumed first; newer cash consumed first)                                                                                           |
| Focused 7.4 GREEN     | same class → **0 failed, 0 error(s) of 17 tests**                                                                                                                                                             |
| Focused 7.5 RED       | three banked + payload keys → **3 error + 1 fail** (`KeyError: cash_banked`)                                                                                                                                  |
| Focused 7.6 GREEN     | three banked + payload keys + five-state → **0 failed, 0 error(s) of 5 tests**                                                                                                                                |
| Full collection suite | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --http-port=18069 --gevent-port=18072 --test-enable --stop-after-init --workers=0 --test-tags /collection` → **0 failed, 0 error(s) of 914 tests** |
| Runtime harness       | Same command upgraded `collection` (write-hook + computed fields)                                                                                                                                             |
| Pre-commit            | `pre-commit run --files` on U5b collection files — **Passed** (after wrapping six E501 docstrings)                                                                                                            |
| Rollback boundary     | Voucher write-hook + ordering iterator; `cash_banked` / `cash_collected` compute; payload `cash_banked`. Do **not** revert U1–U6. Do **not** implement `create_seller_deposit` (U5c).                         |

## Files Changed

| File                                         | Action   | What Was Done                                                                                        |
| -------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------- |
| `models/collection_voucher.py`               | Modified | Audited `validated_collections` write-hook; quotation→invoice FIFO; oldest cash; U5a `_cash_replace` |
| `models/collection_sheet_report.py`          | Modified | Computed `cash_collected` / `cash_banked` from vouchers; payload `cash_banked`                       |
| `models/collection_sheet.py`                 | Modified | `_cash_collected_total` delegates to `cash_collected`                                                |
| `tests/test_collection_cash_replacement.py`  | Modified | Trigger, Cancel, ordering tests                                                                      |
| `tests/test_collection_sheet_report_data.py` | Modified | `cash_banked` scenarios; `PAYLOAD_KEYS`                                                              |
| `openspec/changes/.../tasks.md`              | Modified | U5b tasks `[x]`                                                                                      |
| `openspec/changes/.../apply-progress.md`     | Modified | This U5b append                                                                                      |

## Deviations from Design

None — implementation matches design U5b. The write-hook lives on `write()` after
`super()`, keyed on entering `validated_collections` for `seller_deposit` only, so
Document Review `_write_review_decision` (audited write) runs it and
`action_review_approve` is untouched. FIFO key is `_replacement_fifo_key` with the same
`(due_date or date.max, invoice_number or "")` shape as satellite `_proposal_fifo_key`.
`cash_banked` is voucher SUM of `seller_deposit`, not ledger rows.

## Issues Found

- `docker exec` against `seedian-odoo-1` still needs `--http-port` other than 8069.
- Nested `collection` git still has U1–U6 uncommitted, so mixed-file `git diff` on
  `collection_voucher.py` / `collection_sheet_report.py` includes prior units.
- `tests/test_collection_cash_replacement.py` remains untracked from U5a; U5b appended.

## Changed-line estimate

U5b-authored ≈ **480** (ordering/trigger tests ~306; report `cash_banked` tests ~50;
write-hook + FIFO iterator ~90; compute/payload/helper ~30). Under the 500-line U5b
bound. OpenSpec `tasks.md` / `apply-progress.md` are extra planning artifacts.

## Workload / PR Boundary

- Mode: stacked PR slice (auto-chain / stacked-to-main)
- Current work unit: U5b / PR 7
- Boundary: replacement write-hook, bucket order, `cash_banked` compute. No
  `create_seller_deposit` / form number-date (U5c).
- Next: sdd-apply U5c

---

# U5c — Deposit creation path + form

U1–U5b evidence above is unchanged. This section appends U5c only. All 61 tasks are
`[x]`.

## Completed Tasks

- [x] 8.1 RED: Internal seller creates a deposit on submitted; Open sheet is not the
      deposit target; Disabled type refused; Non-internal refused; Allocation write
      still requires a customer
- [x] 8.2 GREEN: `tools/collection_seller_deposit.py` `@mcp_tool`
      `create_seller_deposit`; mint `sd-<uuid4 hex>`; stamp sentinel +
      `validated_seller` + explicit `sheet_id`; audited write `validated_collections`
- [x] 8.3 RED: Number and date visible for seller_deposit; Search filter exists; Single
      partner_id in arch
- [x] 8.4 GREEN: Widen `voucher_number`/`voucher_date` `invisible=` for `seller_deposit`
      on Current + OCR + Seller Confirmed; search filter; no second `partner_id`
- [x] 8.5 GREEN: `AGENTS.md` deposit MCP contract
- [x] 8.6 Verify: collection `--mode=update` 925/925; upgrade; scoped pre-commit

## TDD Cycle Evidence

| Task | Test File                                     | Layer       | Safety Net                                  | RED                                          | GREEN                                             | TRIANGULATE                                                              | REFACTOR                                  |
| ---- | --------------------------------------------- | ----------- | ------------------------------------------- | -------------------------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------ | ----------------------------------------- |
| 8.1  | `tests/test_collection_mcp_seller_deposit.py` | Integration | Allocation `_DOCUMENT_TYPES` already 7-wide | ✅ 2 fail + 6 error of 10 (`Tool not found`) | ✅ After 8.2                                      | Submitted create; open refused; disabled type; portal/public; extra keys | ➖ Shared amount/date/unknown-key helpers |
| 8.2  | `tools/collection_seller_deposit.py`          | Integration | U5b write-hook still audited-only           | (8.1)                                        | ✅ 0 failed, 0 error(s) of 10                     | Sentinel; `sd-` hex; explicit `sheet_id`; proof before collections write | ➖ Description trim for line budget       |
| 8.3  | `tests/test_collection_ui.py`                 | Integration | `test_form_cash_deposit_keys_present_*`     | ✅ 2 fail of 3 (visibility + search)         | ✅ After 8.4                                      | Current + OCR + Seller Confirmed; search filter; single `partner_id`     | ➖ Reused `CASH_DEPOSIT_KEYS` / layers    |
| 8.4  | `views/collection_views.xml`                  | Integration | `" and document_type !="` kept              | (8.3)                                        | ✅ 0 failed of 4 including cash_deposit keys      | `bank_transfer` still visible; no second `partner_id`                    | ➖ Filter after unsupported               |
| 8.5  | `AGENTS.md`                                   | Docs        | Five-state / catalog tests                  | ➖ Approval (docs)                           | ✅ suite includes `test_agents_md_five_state_*`   | Integrations list; repo map; MCP contract; testing table                 | ➖ Compact contract to stay near 500      |
| 8.6  | collection addon                              | Integration | See below                                   | n/a                                          | collection 925/925; pre-commit pass; `-u` upgrade | n/a                                                                      | n/a                                       |

### Test Summary

- **Total tests written (U5c)**: 11 (`test_discovered_as_method_write_mcp`,
  `test_input_schema_requires_seller_amount_number_date`,
  `test_internal_seller_creates_a_deposit_on_submitted`,
  `test_optional_proof_is_posted_before_collections_validate`,
  `test_open_sheet_is_not_the_deposit_target`, `test_disabled_type_refused`,
  `test_portal_and_public_callers_denied_access_error`,
  `test_sheet_id_and_customer_identification_are_rejected`,
  `test_allocation_write_still_requires_a_customer`,
  `test_tool_source_never_sudoes_or_returns_error_dict`,
  `test_form_seller_deposit_number_and_date_visible`) plus `DOCUMENT_TYPE_FILTERS` now
  includes `seller_deposit`
- **Layers used**: Integration (Odoo TransactionCase)
- **Approval tests**: full `collection` suite 925
- **Pure functions created**: 0 (reused voucher MCP helpers)

## Work Unit Evidence

| Evidence              | Result                                                                                                                                                                                                                                                                |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused 8.1 RED       | `--test-tags /collection:TestCollectionMcpSellerDeposit` → **2 failed + 6 error(s) of 10** (`Tool not found: create_seller_deposit`); allocation-customer already passed as approval                                                                                  |
| Focused 8.2 GREEN     | same tag → **0 failed, 0 error(s) of 10 tests**                                                                                                                                                                                                                       |
| Focused 8.3 RED       | visibility + search + partner_id → **2 failed of 3** (partner_id already single)                                                                                                                                                                                      |
| Focused 8.4 GREEN     | UI tags including cash_deposit keys → **0 failed, 0 error(s) of 4 tests** after `-u collection`                                                                                                                                                                       |
| Full collection suite | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --http-port=18069 --gevent-port=18072 --test-enable --stop-after-init --workers=0 --test-tags /collection` → **0 failed, 0 error(s) of 925 tests** (invoke `--mode=update` equivalent; 8069 already bound) |
| Runtime harness       | Same command upgraded `collection` (MCP mixin + views)                                                                                                                                                                                                                |
| Pre-commit            | `pre-commit run --files` on U5c collection files — **Passed** (after wrapping two E501 docstrings)                                                                                                                                                                    |
| Leftover scanner      | New tool uses `_submitted_sheets_for_seller` and `_lock_open_sheet_for_seller`; source test asserts no `_open_sheets_for_seller` and no `sudo(`. No new `.state == "open"` / domain `"open"` gates in `tools/`                                                        |
| Rollback boundary     | MCP `create_seller_deposit` + form `invisible=` / search filter + AGENTS contract. Do **not** revert U1–U5b/U6. Do **not** add `seller_deposit` to allocation `_DOCUMENT_TYPES`.                                                                                      |

## Files Changed

| File                                          | Action   | What Was Done                                                                                     |
| --------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------- |
| `tests/test_collection_mcp_seller_deposit.py` | Created  | Discovery, submitted-only write, sentinel, audited validate, allocation still customer-required   |
| `tools/collection_seller_deposit.py`          | Created  | `@mcp_tool create_seller_deposit`; mint `sd-`; sentinel; explicit `sheet_id`; audited collections |
| `tests/__init__.py`                           | Modified | Import the new MCP test module                                                                    |
| `tools/__init__.py`                           | Modified | Import the new MCP mixin                                                                          |
| `tests/test_collection_ui.py`                 | Modified | `DOCUMENT_TYPE_FILTERS` + `test_form_seller_deposit_number_and_date_visible`                      |
| `views/collection_views.xml`                  | Modified | Search filter; widen number/date `invisible=` on Current + OCR + Seller Confirmed                 |
| `AGENTS.md`                                   | Modified | Integrations write list, repo map, MCP contract, testing table                                    |
| `openspec/changes/.../tasks.md`               | Modified | U5c tasks `[x]`; all 61 `[x]`                                                                     |
| `openspec/changes/.../apply-progress.md`      | Modified | This U5c append                                                                                   |

## Deviations from Design

MCP success leaves the voucher in `validated_collections` (task 8.2 / design U5c / U5b
in-process hook), not `validated_seller`. The delta spec scenario still says
`validated_seller`; follow design/task. UI/ORM form deposits stay `validated_seller`
until Document Review. `_apply_open_sheet_auto_assign` is not used; `sheet_id` is passed
explicitly because that helper only resolves **open** sheets. `submitted` ∈
`ADMIN_EDITABLE_SHEET_STATES` so membership write is allowed.

## Issues Found

- `docker exec` against `seedian-odoo-1` still needs `--http-port` other than 8069.
- Nested `collection` git still has U1–U6 uncommitted, so mixed-file `git diff` includes
  prior units.
- Spec vs design state wording (`validated_seller` vs `validated_collections`) is
  unchanged in the delta spec; verify should treat design/task as the coded contract.
- Parent attempt token was supplied; this executor did **not** acquire blindly and did
  **not** settle.

## Changed-line estimate

U5c-authored ≈ **520** (MCP tests 302; tool 137; UI test ~33; views ~24; inits ~2;
AGENTS ~22). Slightly over the 500-line U5c bound; no settle. OpenSpec `tasks.md` /
`apply-progress.md` are extra planning artifacts.

## Workload / PR Boundary

- Mode: stacked PR slice (auto-chain / stacked-to-main)
- Current work unit: U5c / PR 8
- Boundary: MCP `create_seller_deposit`, form number/date + search filter, AGENTS
  contract. Last apply slice.
- Next: sdd-verify

---

# Apply Progress: two-step-seller-close-and-seller-deposit (U6 fixture fix)

**Work unit**: Fix U6 partial-replace board fixture after U5b confirm hook **Mode**:
Strict TDD (fixture-only GREEN of existing RED covering tests) **Attempt token**:
`sha256:f56f123e0dbbac0f0f17bce8640e3551a001f378b052d6e0d681607aac8e201e`

U1–U5c evidence above is unchanged. Completed tasks stay `[x]`. This section appends the
post-verify fixture remediations only. Production replacement / U5b write-hook
untouched.

## Completed Tasks

U6 board covering tests already `[x]` (6.1–6.6). Fixture ordering after U5b was wrong;
tests themselves were not rewritten beyond `_replaced_cash_setup`.

## TDD Cycle Evidence

| Task | Test File                                                          | Layer       | Safety Net                                                                                       | RED                                                                                       | GREEN                                                                                   | TRIANGULATE                                                                                 | REFACTOR                                        |
| ---- | ------------------------------------------------------------------ | ----------- | ------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| U6fx | `collection_receipt_proposal/tests/test_receipt_proposal_board.py` | Integration | Verify FAIL: remainder empty after `_confirm` fully replaced 100 cash before `_cash_replace(40)` | ✅ Existing `test_partial_replace_remains_only_for_the_free_remainder` (fixture, not new) | ✅ 0 failed of 2 named tests after deposit=`replace_amount` and no post-confirm replace | ✅ Full replace `test_replaced_cash_leaves_the_pool` + remittance/owner U6 tags still green | ✅ Comment on why deposit equals replace amount |

### Test Summary

- **Total tests written**: 0 new (existing U6 covering tests)
- **Total tests passing (this slice)**: 2/2 named + 4/4 remittance/owner + board class
  21/22 (only pre-existing company-rule FAIL)
- **Layers used**: Integration (Odoo TransactionCase)
- **Approval tests**: remittance-not-in-pool and full-replace stayed green
- **Pure functions created**: 0

## Work Unit Evidence

| Evidence            | Result                                                                                                                                                                                                                                                      |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused named tests | `--test-tags /collection_receipt_proposal:TestReceiptProposalBoard.test_partial_replace_remains_only_for_the_free_remainder,/collection_receipt_proposal:TestReceiptProposalBoard.test_replaced_cash_leaves_the_pool` → **0 failed, 0 error(s) of 2 tests** |
| Board class         | `--test-tags /collection_receipt_proposal:TestReceiptProposalBoard` → **1 failed, 0 error(s) of 22 tests** — only pre-existing `test_sheet_company_rule_still_guards_the_board`. Partial/full replace and `test_excess_deposit_is_not_a_pool_card` passed   |
| Remittance/owner U6 | `--test-tags` excess-deposit + `test_remittance_is_not_pool_draggable` + `test_replaced_cash_keeps_allocation_id` + `test_remittance_does_not_receive_allocation_id_from_owner_sync` → **0 failed, 0 error(s) of 4 tests**                                  |
| Collection suite    | N/A this slice — no collection production or collection tests edited                                                                                                                                                                                        |
| Runtime harness     | Board RPC via `get_proposal_board` on `proposal` sheets created by `_confirm` (U5b hook ran). Ports `--http-port=18069 --gevent-port=18072`                                                                                                                 |
| Pre-commit          | `pre-commit run --files odoo/custom/src/private/collection_receipt_proposal/tests/test_receipt_proposal_board.py` — **Passed** (W8138 except-pass on pre-existing company-rule test)                                                                        |
| Rollback boundary   | Sibling `_replaced_cash_setup` only: deposit amount = `replace_amount`; drop post-confirm `_cash_replace`. Partial test still unlinks remaining cash values for assigned=0 / free 60. Do **not** revert U5b hook or U6 formula.                             |

## Files Changed

| File                                                               | Action   | What Was Done                                                                                                     |
| ------------------------------------------------------------------ | -------- | ----------------------------------------------------------------------------------------------------------------- |
| `collection_receipt_proposal/tests/test_receipt_proposal_board.py` | Modified | `_replaced_cash_setup`: deposit sized to `replace_amount`; confirm hook performs replace; no late `_cash_replace` |
| `openspec/changes/.../apply-progress.md`                           | Modified | This U6-fixture-fix append                                                                                        |

## Deviations from Design

None. Verify-report suggested keeping deposit `validated_seller` through `_confirm`;
this slice instead sizes the deposit to the intended replace so the U5b hook is the
replace, matching the orchestrator required fix. Board still requires `proposal`
(`_confirm` kept).

## Issues Found

- `test_sheet_company_rule_still_guards_the_board` still fails (pre-existing;
  other-company RPC does not refuse). Not this fixture.
- Did **not** settle. Did **not** reset. Did **not** acquire (HEAD already this token).

## Changed-line estimate

Fixture delta ≈ **8** authored lines (3-line comment, deposit amount, removed
`_cash_replace`). Under the 200-line remediations bound.

## Workload / PR Boundary

- Mode: stacked PR slice (auto-chain / stacked-to-main)
- Current work unit: U6 fixture remediations (post-U5b verify FAIL)
- Boundary: sibling board fixture only
- Next: sdd-verify
