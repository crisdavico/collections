# Tasks: Sheet-Scoped Document Review

## Review Workload Forecast

| Field                   | Value              |
| ----------------------- | ------------------ |
| Estimated changed lines | 480–650            |
| 400-line budget risk    | High               |
| Chained PRs recommended | Yes                |
| Suggested split         | PR 1 → PR 2 → PR 3 |
| Delivery strategy       | ask-on-risk        |
| Chain strategy          | stacked-to-main    |

Decision needed before apply: Yes Chained PRs recommended: Yes Chain strategy:
stacked-to-main 400-line budget risk: High

### Suggested Work Units

| Unit | Goal                        | Likely PR | Focused test command        | Runtime harness                | Rollback boundary                                      |
| ---- | --------------------------- | --------- | --------------------------- | ------------------------------ | ------------------------------------------------------ |
| 1    | Sheet-scoped RPCs + OWL     | PR 1      | `invoke test -m collection` | N/A — TransactionCase          | voucher RPCs, OWL JS, review/flag/ACL tests            |
| 2    | Sheet header opens review   | PR 2      | `invoke test -m collection` | `invoke install -m collection` | sheet model/form XML, sheet/header tests               |
| 3    | Drop menu; bump 19.0.1.11.0 | PR 3      | `invoke test -m collection` | `invoke install -m collection` | review views, `ir_ui_menu.py`, `__init__.py`, manifest |

## Phase 1: Sheet-scoped RPCs (PR 1)

- [x] 1.1 RED `tests/test_collection_document_review.py`: two sheets; queue A excludes
      B; cross-sheet mutations `UserError`.
- [x] 1.2 GREEN `models/collection_voucher.py`: `get_review_queue(sheet_id)` = that
      sheet + pending + attached.
- [x] 1.3 RED same file: empty/ineligible sheet `[]`; other sheets ignored.
- [x] 1.4 GREEN queue domain; no global fallback.
- [x] 1.5 RED review + flag tests: missing/0/`False`/bad id → `UserError` (not `[]`).
- [x] 1.6 GREEN `_require_review_sheet` (`@api.private`): flag first, then `int > 0` and
      `exists()`.
- [x] 1.7 RED review tests: stale/other-sheet mutation refused.
- [x] 1.8 GREEN mutations: `sheet_id` after ids, before `vals`/`degrees`;
      `self.sheet_id == sheet`.
- [x] 1.9 RED flag tests: OFF refuses four RPCs with or without `sheet_id`.
- [x] 1.10 GREEN flag first; pass `sheet_id` at existing review/flag call sites.
- [x] 1.11 RED `tests/test_collection_acl.py`: assign sheet; portal `AccessError`;
      internals pass `sheet_id`.
- [x] 1.12 GREEN ACL call sites; no new groups.
- [x] 1.13 RED OWL source asserts `sheet_id` on four `orm.call` args.
- [x] 1.14 GREEN `static/src/document_review/document_review_action.esm.js`:
      `params.sheet_id` only; invalid → notify, skip queue.

## Phase 2: Sheet header action (PR 2)

- [x] 2.1 RED `tests/test_collection_sheet.py`: saved+ON →
      `collection.document_review` + `params.sheet_id`; OFF/unsaved/`NewId` →
      `UserError`.
- [x] 2.2 GREEN `models/collection_sheet.py`: non-stored helper;
      `action_open_document_review` via `_for_xml_id`.
- [x] 2.3 RED `tests/test_collection_ui.py`: header visible iff saved+flag ON; hidden
      OFF/unsaved.
- [x] 2.4 GREEN `views/collection_views.xml` sheet form: header `type="object"` +
      helper.

## Phase 3: Menu removal (PR 3)

- [x] 3.1 RED UI + flag: menu absent ON/OFF; xmlid gone; `load_menus` omits it; action
      kept; `path` cleared.
- [x] 3.2 GREEN `views/collection_document_review_views.xml`: drop menuitem, `<delete>`
      leftover menu, clear `path`.
- [x] 3.3 GREEN delete `models/ir_ui_menu.py`; drop import in `models/__init__.py`.
- [x] 3.4 GREEN `__manifest__.py` bump `19.0.1.10.0` to `19.0.1.11.0`.

## Phase 4: Upgrade and verify

- [x] 4.1 `invoke install -m collection` or `odoo -u collection`.
- [x] 4.2 Seedian root: scoped `pre-commit` on this change's files (recursive glob
      fails on archived OpenSpec; archives must not be reformatted).
- [x] 4.3 `invoke test -m collection`.
