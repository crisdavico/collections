# Tasks: Auto-assign Open Sheet

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 550–850 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | `state` + Close/Reopen + statusbar | PR 1 | `invoke test -m collection` | N/A (Odoo TransactionCase in container) | manifest; sheet field/actions/intercept; sheet views; `tests/test_collection_{sheet,ui}.py` |
| 2 | One-open + freeze + Action + leftover Close | PR 2 | `invoke test -m collection` | N/A (Odoo TransactionCase in container) | sheet/voucher models; membership XML; `tests/test_collection_{sheet,ui,document_review}.py` |
| 3 | Auto-assign + lock + MCP inherit | PR 3 | `invoke test -m collection` | N/A (Odoo TransactionCase in container) | create-assign + lock; `tests/test_collection_{sheet,mcp_tool}.py` |

Threat matrix N/A. No UNIQUE. `tools/collection_voucher.py` unchanged. Tests from seedian root.

## Phase 1: Sheet lifecycle + UI (Unit 1 / PR1)

- [x] 1.1 RED `tests/test_collection_sheet.py`: drop `assertNotIn("state")`; default `open`; Close/Reopen; raw `state` write rejected except `collection_sheet_audited_state`.
- [x] 1.2 GREEN `__manifest__.py` `19.0.1.12.0`. `models/collection_sheet.py`: `state` default `open`; `action_close`/`action_reopen`; intercept `write` like voucher audited state.
- [x] 1.3 RED/GREEN `tests/test_collection_ui.py` + `views/collection_views.xml`: replace `test_collection_sheets_form_without_statusbar`; non-clickable statusbar, Close/Reopen, list/search `state`.
- [x] 1.4 `invoke test -m collection`.

## Phase 2: One-open + freeze (Unit 2 / PR2)

- [x] 2.1 RED `tests/test_collection_sheet.py`: second open create rejected; Reopen rejected if another open; leftover `>1` still Closeable; Action reject if open ≥1; freeze add/remove/reassign. Rewrite two-open same-seller tests (close-first or `_other_internal_seller`).
- [x] 2.2 GREEN `models/collection_sheet.py`: `_open_sheets_for_seller`; guard create-if-open and `action_reopen`; freeze `voucher_ids`; unlink via `collection_sheet_unlinking`. GREEN `models/collection_voucher.py`: after `_seller_for_sheet_action` reject open ≥1; reject add to closed or remove/reassign off closed.
- [x] 2.3 RED/GREEN membership readonly when closed (`tests/test_collection_ui.py`, `views/collection_views.xml`). RED/GREEN `tests/test_collection_document_review.py` two-sheet cases close-first or two sellers.
- [x] 2.4 `invoke test -m collection`.

## Phase 3: Auto-assign + MCP (Unit 3 / PR3)

- [x] 3.1 RED `tests/test_collection_sheet.py`: unique open assigns; none → create then assign; `>1` no voucher; explicit open `sheet_id` honored; closed `sheet_id` fails; null seller unassigned; later `seller_id` write does not assign. Unassigned: omit seller / unassign / unlink.
- [x] 3.2 GREEN `models/collection_voucher.py` `create` before `super`: seller set + omitted `sheet_id` → `pg_advisory_xact_lock(hashtext('collection.sheet.open'), seller_id)` then `_open_sheets_for_seller` (0/1/>1). Same lock on sheet create-open.
- [x] 3.3 RED `tests/test_collection_mcp_tool.py`: all-new unique open assigns; none creates one sheet; `>1` no writes; exact replay leaves `sheet_id`/`write_date`; response `{id,name,state,document_id}` only.
- [x] 3.4 `invoke test -m collection`.

## Phase 4: Verify

- [ ] 4.1 Scoped `pre-commit run --files` on touched paths. Full `invoke test -m collection`. Ready for apply.

## Phase 5: AGENTS.md

- [ ] 5.1 `AGENTS.md`: sheet `open`/`closed`; one-open on new ops (leftover Close OK); freeze; ORM create auto-assign; MCP inherit, no payload `sheet_id`.
