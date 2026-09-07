# Tasks: Seller Close for Collection Sheets

## Review Workload Forecast

| Field                   | Value           |
| ----------------------- | --------------- |
| Estimated changed lines | ~1250           |
| 400-line budget risk    | High            |
| Chained PRs recommended | Yes             |
| Suggested split         | PR 1–6          |
| Delivery strategy       | auto-chain      |
| Chain strategy          | stacked-to-main |

Decision needed before apply: No Chained PRs recommended: Yes Chain strategy:
stacked-to-main 400-line budget risk: High

### Suggested Work Units

`invoke test -m collection --mode=update`. PR 5
`invoke test -m collection_receipt_proposal --mode=update`.

| Unit | Goal                | Likely PR | Test                                                       | Harness           | Rollback                                         |
| ---- | ------------------- | --------- | ---------------------------------------------------------- | ----------------- | ------------------------------------------------ |
| 1    | Named sets          | PR 1      | collection `--mode=update`                                 | N/A TxCase        | `collection_common.py` + helpers                 |
| 2    | Dormant `submitted` | PR 2      | collection `--mode=update`                                 | N/A TxCase        | Selection, `19.0.1.42.0`, docs                   |
| 3    | Admin on submitted  | PR 3      | collection `--mode=update`                                 | N/A TxCase        | Admin/draft sets, views, recon, Confirm          |
| 4    | Seller Close        | PR 4      | collection `--mode=update`                                 | N/A TxCase        | Close action, dispatcher, header                 |
| 5    | Confirm mandatory   | PR 5      | collection + `collection_receipt_proposal` `--mode=update` | N/A TxCase        | Confirm 83/14 + sibling `_confirm()`             |
| 6    | Reinstate + MCP     | PR 6      | collection `--mode=update`                                 | Manual MCP+Review | `action_reinstate` + `collection_sheet_close.py` |

## Phase 1: Named sets

- [x] 1.1 RED no sheet `"open"` outside `models/collection_common.py` (invoice `open`
      exempt) — `tests/test_collection_company_migration.py`.
- [x] 1.2 RED `force_sheet_state`/`advance_sheet_to` in `tests/common_connector.py`;
      migrate five bypasses
      (`test_collection_company_migration.py,test_collection_mcp_allocation_lookup.py,test_collection_document_review.py,test_collection_allocation.py,test_collection_sheet.py`).
- [x] 1.3 GREEN `{"open"}` sets `models/collection_common.py`; seller-axis
      `models/collection_sheet.py` + `tools/collection_allocation.py`; admin-axis
      `models/collection_voucher.py`. No behavior.

## Phase 2: Dormant `submitted`

- [x] 2.1 RED pin `__manifest__.py` `19.0.1.42.0`; leftover `19.0.1.42.0`; scanner;
      five-state AGENTS/readme; `Do **not** add migrations/19.0.1.42.0/` —
      `tests/test_collection_company_migration.py`.
- [x] 2.2 GREEN Selection `models/collection_sheet.py`; Rendida
      `models/collection_sheet_report.py`; statusbar `views/collection_views.xml`;
      `__manifest__.py`; `AGENTS.md`; `readme/DESCRIPTION.md`; `oca-gen-addon-readme`.
      No migrate folder.

## Phase 3: Admin on submitted

- [x] 3.1 RED Review on submitted (`tests/test_collection_document_review.py`);
      membership add/remove; partner reassign; draft legal
      (`tests/test_collection_allocation.py`).
- [x] 3.2 RED `tests/test_collection_ui.py`: `assertIn("!=")` → `assertIn("not in")`;
      Review attr strings; `test_confirm_from_open_is_transitional`
      `tests/test_collection_sheet.py`.
- [x] 3.3 GREEN widen `ADMIN_EDITABLE_SHEET_STATES` + `DRAFT_SHEET_STATES`
      `models/collection_common.py`; copy `models/collection_allocation.py`;
      `views/collection_views.xml` + `views/collection_allocation_views.xml`; recon
      split `models/collection_sheet_report.py`; Confirm `open|submitted`
      `models/collection_sheet.py`.

## Phase 4: Seller Close

- [x] 4.1 RED `tests/test_collection_sheet.py`: draft-member names offenders;
      empty/`validated_collections` pass; refuse non-open; disabled seller can close.
- [x] 4.2 RED `tests/test_collection_sheet_report_data.py`: decls frozen from submitted;
      `commission_percent` not; raw combined write refused.
- [x] 4.3 GREEN `action_seller_close` + `_dispatch_submitted_state_write` (drop
      `"open"`) `models/collection_sheet.py`; lock → `invalidate_recordset`. Recon
      `readonly` `views/collection_views.xml`.

## Phase 5: Confirm mandatory

- [x] 5.1 RED delete `test_confirm_from_open_is_transitional`; Confirm-from-open refuses
      `tests/test_collection_sheet.py`. Re-ripgrep `action_confirm` (**22 in 7 test
      files**, plus 2 in `models/collection_sheet.py`; down from ~87/14 after helpers).
- [x] 5.2 GREEN Confirm `submitted`-only `models/collection_sheet.py`;
      `advance_sheet_to`; mail `tests/test_collection_mail.py`; labels 4→5. Sibling
      `_confirm()` `../collection_receipt_proposal/tests/common.py` (`apply.roots`
      consent).

## Phase 6: Reinstate + MCP

- [x] 6.1 RED Cancel from submitted;
      `test_reinstate_succeeds_while_seller_has_a_new_open_sheet`; refuse
      `submitted→open`/`cancelled→open` `tests/test_collection_sheet.py`.
- [x] 6.2 GREEN `action_open` → `action_reinstate` (drop one-open); Cancel from
      `submitted`; Reinstate `views/collection_views.xml`.
- [x] 6.3 RED `tests/test_collection_mcp_sheet_close.py` clone
      `tests/test_collection_mcp_sheet_pdf.py`: `seller_id`-only; 0-open `UserError` not
      `{sheet: null}`; no-sudo / no `{"error"`.
- [x] 6.4 GREEN `tools/collection_sheet_close.py` 1:1 `tools/sheet_report.py`;
      `_collection_sheet_identity`; `tools/__init__.py`.
