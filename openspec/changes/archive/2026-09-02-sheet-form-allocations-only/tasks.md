# Tasks: Sheet Form Allocations Only

## Review Workload Forecast

| Field                   | Value           |
| ----------------------- | --------------- |
| Estimated changed lines | 280–380         |
| 400-line budget risk    | Medium          |
| Chained PRs recommended | No              |
| Suggested split         | Single PR       |
| Delivery strategy       | auto-chain      |
| Chain strategy          | stacked-to-main |

Decision needed before apply: No Chained PRs recommended: No Chain strategy:
stacked-to-main 400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal                                                                        | Likely PR | Focused test command                                     | Runtime harness                                                           | Rollback boundary                                                                                                                               |
| ---- | --------------------------------------------------------------------------- | --------- | -------------------------------------------------------- | ------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| 1    | Allocations-only sheet form, counted Vouchers action, voucher `sheet_id` UI | PR 1      | `invoke test -m collection --mode=update` (Seedian root) | Odoo TransactionCase in Docker; `invoke test -m collection --mode=update` | Revert `models/collection_sheet.py`, `views/collection_views.xml`, `tests/test_collection_ui.py`, `tests/test_collection_sheet.py`, `AGENTS.md` |

## Phase 1: RED — invert and add failing tests

- [x] 1.1 Invert `tests/test_collection_ui.py`
      `test_sheet_form_notebook_vouchers_and_allocations` →
      `test_sheet_form_notebook_allocations_only`: one Allocations page; `partner_id`
      after `name` before `state`; no `voucher_ids` in arch; keep
      `SHEET_NOTEBOOK_VOUCHERS` for absence (spec: Allocations-only notebook with
      Customer).
- [x] 1.2 Invert `test_collection_sheets_form_statusbar_close_reopen`: drop
      `voucher_ids` from required names and many2many asserts; keep
      Close/Reopen/Document Review. Do not change
      `test_customer_field_is_partner_id_without_domain`.
- [x] 1.3 Add sheet-form stat-button arch test in `tests/test_collection_ui.py`:
      `oe_button_box` first child of `<sheet>`; `action_open_vouchers` `oe_stat_button`;
      `voucher_count` `statinfo`; `invisible="not id"` (spec: Unsaved sheet hides
      voucher action).
- [x] 1.4 Add voucher `sheet_id` arch test in `tests/test_collection_ui.py`: list
      `optional="hide"`; form editable after `seller_id` (no extra readonly); search
      field + group-by; kanban must not add `sheet_id` (spec: sheet_id on list form
      search).
- [x] 1.5 Add `tests/test_collection_sheet.py` tests: empty `voucher_count` is 0; N
      members; `action_open_vouchers` `view_mode` `list,kanban,form`, domain
      `[("sheet_id", "=", sheet.id)]`, `default_sheet_id`/`default_seller_id`, no `path`
      (spec: Saved sheet opens filtered vouchers).
- [x] 1.6 Add unsaved `.new()` `UserError` for `action_open_vouchers` in
      `tests/test_collection_sheet.py`; keep Document Review `.new()` (spec: Unsaved
      sheet refuses voucher action). Run `invoke test -m collection --mode=update` from
      Seedian root — RED expected.

## Phase 2: GREEN — model then XML

- [x] 2.1 In `models/collection_sheet.py`: non-stored `voucher_count`
      `@api.depends("voucher_ids")`; hand-built `action_open_vouchers` per design;
      generalize `_ensure_saved_sheet` to
      `"This action requires a saved collection sheet."` Keep `voucher_ids`.
- [x] 2.2 In `views/collection_views.xml` sheet form: `oe_button_box` first inside
      `<sheet>`; drop Vouchers page; keep one Allocations page; `partner_id` after
      `name` before `state` (exactly one `partner_id` on form).
- [x] 2.3 In `views/collection_views.xml` voucher views: list
      `sheet_id optional="hide"`; form `sheet_id` left group after `seller_id`,
      editable; search field + group-by; leave kanban unchanged.
- [x] 2.4 Run `invoke test -m collection --mode=update` from Seedian root — GREEN.
      Existing `test_reassign_moves_voucher_to_sheet_b_only` and
      `test_freeze_rejects_add_remove_and_reassign` cover Clear `sheet_id` /
      Closed-sheet unlink; rely on existing dates and Document Review tests.

## Phase 3: Docs and quality

- [x] 3.1 One-liner in `AGENTS.md` UI bullet: allocations-only notebook + counted
      Vouchers stat button; membership via voucher `sheet_id`.
- [x] 3.2 `pre-commit run --files odoo/custom/src/private/collection/**` from Seedian
      root; re-run `invoke test -m collection --mode=update`.
