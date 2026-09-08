# Tasks: Two-step Seller Close and Seller Deposit

Sibling U1 deletes and U6 board edits under `collection_receipt_proposal/` are **in
scope**. `apply.roots` omit that addon; orchestrator grants the sibling root before
apply. Stack **U1 → U2 → U3 → U4 → U5a → U6 → U5b → U5c**. Do not merge U4+U5 or
U5b+U5c. Threat matrix is N/A.

## Review Workload Forecast

| Field                   | Value                                                                                                      |
| ----------------------- | ---------------------------------------------------------------------------------------------------------- |
| Estimated changed lines | ~1800–2500 authored across eight units                                                                     |
| 400-line budget risk    | High                                                                                                       |
| Chained PRs recommended | Yes                                                                                                        |
| Suggested split         | PR 1 (U1) → PR 2 (U2) → PR 3 (U3) → PR 4 (U4) → PR 5 (U5a) → PR 6 (U6) → PR 7 (U5b) → PR 8 (U5c) onto main |
| Delivery strategy       | auto-chain                                                                                                 |
| Chain strategy          | stacked-to-main                                                                                            |

Decision needed before apply: No Chained PRs recommended: Yes Chain strategy:
stacked-to-main 400-line budget risk: High

### Suggested Work Units

| Unit | Goal                                                                                            | Likely PR | Focused test command                                                                                     | Runtime harness                                                                                           | Rollback boundary                                                                                                       |
| ---- | ----------------------------------------------------------------------------------------------- | --------- | -------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| U1   | Lift sheet-boundary + sheet-wide cap + receipt `depends=` into core; delete satellite overrides | PR 1      | `invoke test -m collection --mode=update` AND `invoke test -m collection_receipt_proposal --mode=update` | `docker exec -i seedian-odoo-1 odoo -d devel -u collection,collection_receipt_proposal --stop-after-init` | Core constraint/`depends=`/`receipt_value_ids`; restore satellite `collection_receipt.py` + constraint methods          |
| U2   | Eighth catalog `seller_deposit` + sentinel + `19.0.1.43.0` migrate                              | PR 2      | `invoke test -m collection --mode=update`                                                                | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init`                             | Catalog XMLID, sentinel data, `_seller_deposit_partner()`, `migrations/19.0.1.43.0/`, manifest bump (no `19.0.1.42.0/`) |
| U3   | Remittance out of collected/mismatch; tendered + echeck/retention                               | PR 3      | `invoke test -m collection --mode=update`                                                                | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init`                             | Report/XLSX/QWeb tendered+collected paths only                                                                          |
| U4   | Amount-free Seller Close; declare; Confirm gate; PDF call-site `submitted`                      | PR 4      | `invoke test -m collection --mode=update`                                                                | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init`                             | Sheet/MCP close+declare/PDF call site/views/recon window; keep `cash_on_hand` column                                    |
| U5a  | Ledger + exact-cent primitives + `replaced_amount`                                              | PR 5      | `invoke test -m collection --mode=update`                                                                | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init`                             | `collection.cash.replacement`, ACL/ir.rule, shrink/grow/`_receipt_get_or_create` in core                                |
| U6   | Board lock: free − replaced; remittance not draggable                                           | PR 6      | `invoke test -m collection --mode=update` AND `invoke test -m collection_receipt_proposal --mode=update` | `docker exec -i seedian-odoo-1 odoo -d devel -u collection,collection_receipt_proposal --stop-after-init` | Satellite `proposal_free_amount`, transfer-plan + sync-owner guards                                                     |
| U5b  | Replacement engine + `validated_collections` write-hook + `cash_banked`                         | PR 7      | `invoke test -m collection --mode=update`                                                                | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init`                             | Voucher write-hook, bucket order, `cash_banked` compute                                                                 |
| U5c  | MCP `create_seller_deposit` + form number/date                                                  | PR 8      | `invoke test -m collection --mode=update`                                                                | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init`                             | `tools/collection_seller_deposit.py`, form `invisible=` + search filter                                                 |

## Phase 1 / U1 — Lift receipt-value invariants into core

- [x] 1.1 RED: Split `collection/tests/test_collection_receipt.py:170-199` into named
      tests: Cross-customer same sheet accepted, Cross-sheet refused, Over-cap across
      customers refused, At-cap allowed (collection-receipts Receipt values).
- [x] 1.2 GREEN: Sheet-boundary `_check_same_allocation`; delete allocation filter
      `:72-73` in `collection/models/collection_receipt_value.py`; keep one batched
      `search` (do not copy satellite N+1).
- [x] 1.3 RED: Test Existing applied write recomputes (Receipt totals) — write existing
      `amount_applied` without SQL conversion error.
- [x] 1.4 GREEN: Field-level `depends=` on
      `total_values`/`total_applied`/`amount_on_account` in
      `collection/models/collection_receipt.py`; delete
      `collection_receipt_proposal/models/collection_receipt.py` and its
      `models/__init__.py` import.
- [x] 1.5 RED: Test Reverse relation lists values on `receipt_value_ids`.
- [x] 1.6 GREEN: Inverse o2m `receipt_value_ids` on
      `collection/models/collection_voucher.py`; delete satellite
      `_check_same_allocation` / `_check_voucher_split_cap`
      (`collection_receipt_value.py:12-57`); keep `_proposal_card_payload`. Do not lift
      partner-identity relax.
- [x] 1.7 GREEN: Sibling `tests/test_receipt_proposal_split.py` still green; update
      `collection_receipt_proposal/AGENTS.md` (same-sheet/cap now core).
- [x] 1.8 Verify: both `--mode=update` suites;
      `docker exec -i seedian-odoo-1 odoo -d devel -u collection,collection_receipt_proposal --stop-after-init`;
      scoped pre-commit on both addons.

## Phase 2 / U2 — Eighth catalog + 19.0.1.43.0 migrate

- [x] 2.1 RED: Eight codes — `SEVEN_TYPE_CODES` → eight in
      `tests/test_collection_company_migration.py`; `CATALOG_XMLIDS` len 8 in
      `tests/test_collection_company_settings.py`; Selection includes `seller_deposit`
      in `tests/test_collection_voucher.py:361-378` (Eight catalog XMLIDs exist; Persist
      seller_deposit).
- [x] 2.2 GREEN: `seller_deposit` in `collection/models/collection_common.py` +
      `data/collection_document_type_data.xml` XMLID `document_type_seller_deposit`;
      `DOCUMENT_TYPE_LABELS.seller_deposit` in
      `static/src/document_review/document_review_helpers.esm.js`.
- [x] 2.3 RED: Sentinel partner tests — Deposit stamps sentinel; Customer identification
      refused (ORM).
- [x] 2.4 GREEN: `data/collection_seller_deposit_partner_data.xml` (`noupdate`
      `collection.partner_seller_deposit`); `_seller_deposit_partner()` on
      `res_company.py`; `COLLECTION_TYPE_CODES` follows `DOCUMENT_TYPE_CODES`;
      `__manifest__.py` data entry.
- [x] 2.5 RED: Upgrade to 19.0.1.43.0 unions seller_deposit; leftover pin still forbids
      `migrations/19.0.1.42.0/`; New company starts with eight types.
- [x] 2.6 GREEN: Manifest `19.0.1.43.0`; `migrations/19.0.1.43.0/post-migrate.py` clones
      `19.0.1.40.0` `_collection_enable_all_document_types()`.
- [x] 2.7 GREEN: `collection/AGENTS.md` eight catalog rows + version; fix stale
      “submitted dormant”; `readme/DESCRIPTION.md` eighth type.
- [x] 2.8 Verify: `invoke test -m collection --mode=update`; upgrade `collection`;
      scoped pre-commit.

## Phase 3 / U3 — Exclude remittance from collection totals

- [x] 3.1 RED: Remittance excluded from collected; Unallocated remittance does not
      mismatch (`tests/test_collection_sheet_report_data.py` around `:589-661`).
- [x] 3.2 GREEN: Skip `seller_deposit` in `_collection_report_voucher_blocks`
      (`collection_sheet_report.py`); `mismatch` ignores remittance.
- [x] 3.3 RED: Tendered includes remittance echeck and retention + `seller_deposits`;
      keep existing recon keys (`cash`/`deposits`/`checks`/`transfers`).
- [x] 3.4 GREEN: `_collection_report_tendered` adds `seller_deposits` + `echecks` +
      `retentions`; algebra `net_due`/`difference` untouched.
- [x] 3.5 RED: XLSX/QWeb show new tendered buckets
      (`tests/test_collection_sheet_xlsx.py:401-430`).
- [x] 3.6 GREEN: Recon header/cross-links in `report/collection_sheet_xlsx.py:685-724`
      (keep formula ladder `:744-780`); QWeb table
      `report/collection_sheet_templates.xml:382-427`.
- [x] 3.7 Verify: `invoke test -m collection --mode=update`; upgrade `collection`;
      scoped pre-commit.

## Phase 4 / U4 — Two-step seller close

- [x] 4.1 RED: Open sheet closes to submitted without amounts; Amounts on close refused
      (`tests/test_collection_sheet.py`,
      `tests/test_collection_mcp_sheet_close.py:104-197`).
- [x] 4.2 GREEN: `action_seller_close` drops amount `vals` (keep kwargs `=None`) in
      `collection_sheet.py`; amount-free `_CLOSE_COLLECTION_SHEET_SCHEMA`; return
      `cash.collected` in `tools/collection_sheet_close.py`.
- [x] 4.3 RED: Submitted sheet accepts Declare Cash; re-runnable; Non-submitted refused;
      Disabled seller may still declare.
- [x] 4.4 GREEN: `SELLER_DECLARATION_STATES = frozenset({"submitted"})` in
      `collection_common.py` (no new inline `"open"`); `action_declare_cash`; invert
      recon window in `collection_sheet_report.py:69-85`; keep column `cash_on_hand`,
      `string=` "Cash to Administration"; `cash_declared_at`/`cash_declared_by`; views
      `readonly` on `submitted` (`collection_views.xml:510-515`). Invert
      `tests/test_collection_sheet_report_data.py:291-299`.
- [x] 4.5 RED: MCP `declare_collection_cash` scenarios (new
      `tests/test_collection_mcp_cash_declare.py`): success, Zero submitted raise not
      null, `sheet_id` rejected, Open sheet is not the declare target, Non-internal
      refused.
- [x] 4.6 GREEN: `tools/collection_cash_declare.py` + `_submitted_sheets_for_seller`;
      import in `tools/__init__.py`. Do not declare via `_open_sheets_for_seller`.
- [x] 4.7 RED: Undeclared cash blocks Confirm; Zero cash Confirm without declaration;
      Declared cash allows Confirm.
- [x] 4.8 GREEN: Confirm gate in `collection_sheet.py` when `cash_collected > 0` and
      `cash_declared_at` unset.
- [x] 4.9 RED: PDF Submitted sheet returns base64; Open preferred over submitted; More
      than one submitted fails closed (`tests/test_collection_mcp_sheet_pdf.py`).
- [x] 4.10 GREEN: Widen `tools/sheet_report.py` call site only (0 open → one submitted).
      Do **not** change `_open_sheets_for_seller`.
- [x] 4.11 GREEN: UI/xlsx/mail tests (`test_collection_ui.py:1148-1153`,
      `test_collection_sheet_xlsx.py:531-555`); `AGENTS.md` MCP contracts; leftover
      scanner still forbids new `"open"` gates.
- [x] 4.12 Verify: `invoke test -m collection --mode=update`; upgrade `collection`;
      scoped pre-commit.

## Phase 5 / U5a — Replacement ledger + primitives

- [x] 5.1 RED: Ledger ACL `1,0,1,0` + company `ir.rule`
      (`tests/test_collection_acl.py:137`,
      `tests/test_collection_allocation_acl.py:168`); Write refused; Draft allocation
      unlink cascades replacements.
- [x] 5.2 GREEN: `models/collection_cash_replacement.py` (revision pattern, context
      `collection_cash_replacement`); import in `models/__init__.py`; ACL +
      `collection_security.xml`.
- [x] 5.3 RED: Exact-cent Zero slice skipped; Currency mismatch refused; Same-receipt
      totals unchanged (manual `_cash_replace` in
      `tests/test_collection_cash_replacement.py`).
- [x] 5.4 GREEN: `_shrink_or_unlink` / `_grow_voucher_amount` + currency-agreement in
      `collection_receipt_value.py`; `_cash_replace` / `_cash_reverse`; skip 0 slices;
      shrink only if slice == amount or remainder ≥ 1 cent.
- [x] 5.5 RED: `replaced_amount` from ledger (Σreplace − Σreverse) on voucher.
- [x] 5.6 GREEN: `replaced_amount` compute on `collection_voucher.py`;
      `_receipt_get_or_create` on `collection_allocation.py`; satellite wrappers
      `_proposal_shrink_value` / `_proposal_grow_value` /
      `_proposal_receipt_get_or_create` in
      `collection_receipt_proposal/models/collection_sheet.py` and
      `collection_allocation.py`. Reverse API exists; Cancel MUST NOT call it.
- [x] 5.7 Verify: `invoke test -m collection --mode=update`; upgrade `collection`;
      scoped pre-commit.

## Phase 6 / U6 — Board-side locking (collection_receipt_proposal)

Must land before U5b. Sibling grant required.

- [x] 6.1 RED: Replaced cash leaves the pool; Partial replace remains only for the free
      remainder (`tests/test_receipt_proposal_board.py`).
- [x] 6.2 GREEN: `proposal_free_amount = amount − assigned − replaced_amount` (depends
      include `replaced_amount`) in
      `collection_receipt_proposal/models/collection_voucher.py`.
- [x] 6.3 RED: Remittance is not pool-draggable; Replaced cash keeps allocation_id
      (`tests/test_receipt_proposal_actions.py`,
      `tests/test_receipt_proposal_split.py`).
- [x] 6.4 GREEN: Guard `_proposal_transfer_plan` pool path and
      `_proposal_sync_voucher_owner` against `seller_deposit` in
      `collection_receipt_proposal/models/collection_sheet.py`.
- [x] 6.5 GREEN: `collection_receipt_proposal/AGENTS.md` board lock; keep largest-share
      owner in satellite.
- [x] 6.6 Verify: both `--mode=update` suites; upgrade both modules; scoped pre-commit
      on both addons.

## Phase 7 / U5b — Ordering engine + trigger + cash_banked

- [x] 7.1 RED: Deposit validation replaces cash; Review-off companies still replace;
      Non-transition write does not re-replace; No allocations is a no-op; Cancel does
      not reverse (`tests/test_collection_cash_replacement.py`).
- [x] 7.2 GREEN: Write-hook on `collection_voucher.py` when `state` transitions to
      `validated_collections` for `seller_deposit` only (covers
      `collection_audited_state`). Not `action_review_approve`.
- [x] 7.3 RED: Quotation before invoice; within kind `_proposal_fifo_key`; within
      bucket oldest cash `create_date`.
- [x] 7.4 GREEN: Ordering engine calling U5a primitives on the same receipt
      (value-preserving; `amount_applied` unchanged).
- [x] 7.5 RED: `cash_banked` sums seller_deposit only; Excess deposit still banks; No
      allocations still banks from vouchers
      (`tests/test_collection_sheet_report_data.py`).
- [x] 7.6 GREEN: Computed `cash_banked` / `cash_collected` on
      `collection_sheet_report.py` from vouchers, never the ledger. Do not sum
      `cash_deposit`.
- [x] 7.7 Verify: `invoke test -m collection --mode=update`; upgrade `collection`;
      scoped pre-commit.

## Phase 8 / U5c — Deposit creation path + form

- [x] 8.1 RED: Internal seller creates a deposit on submitted; Open sheet is not the
      deposit target; Disabled type refused; Non-internal refused; Allocation write
      still requires a customer (`tests/test_collection_mcp_seller_deposit.py`).
- [x] 8.2 GREEN: `tools/collection_seller_deposit.py` `@mcp_tool`
      `create_seller_deposit`; mint `sd-<uuid4 hex>`; stamp sentinel +
      `validated_seller` + explicit `sheet_id`; audited write `validated_collections` so
      U5b runs in-process. Import in `tools/__init__.py`. No `sudo()`. Do not add
      `seller_deposit` to allocation `_DOCUMENT_TYPES`.
- [x] 8.3 RED: Number and date visible for seller_deposit; Search filter exists; Single
      partner_id in arch (`tests/test_collection_ui.py:476-501`, `:769-803`).
- [x] 8.4 GREEN: Widen `voucher_number`/`voucher_date` `invisible=` for `seller_deposit`
      on Current + OCR + Seller Confirmed; search filter; **no** second `partner_id`
      (`views/collection_views.xml`).
- [x] 8.5 GREEN: `AGENTS.md` deposit MCP contract.
- [x] 8.6 Verify: `invoke test -m collection --mode=update`; upgrade `collection`;
      scoped pre-commit. Manual e2e after this unit: close → PDF → deposit → declare →
      Planilla Cuadrada → Confirm → board lock.
