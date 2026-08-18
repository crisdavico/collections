# Proposal: Sheet-Scoped Document Review

## Intent

Reviewers open Document Review from Collections and see a company-wide eligible queue.
They must review one **saved collection sheet**. Direct/global review must stop. Company
`document_review_enabled` still gates entry.

## Scope

### In Scope

- Saved-sheet header action opens existing OWL client action with a **mandatory sheet
  identifier**
- Hide action when flag OFF; **no** standalone menu
- Review RPCs require that id, filter `sheet_id`, reject missing/invalid/stale
  cross-sheet requests
- OWL passes the param on queue, approve, reject, rotation
- Remove `collection.menu_collection_document_review`; retire menu blacklist
- Tests for entry, queue filter, RPC refusals
- Optional non-stored UI helper only (no stored migration)

### Out of Scope

- Nebula / MCP; sheet workflow; extra groups/record rules
- WhatsApp, HTTP API, CRM; voucher lifecycle (`collection-vouchers` unchanged)
- Implementation during `/sdd-new`

## Capabilities

> Contract for sdd-spec.

### New Capabilities

- None

### Modified Capabilities

- `document-review`: sheet-scoped queue/RPCs; menu removed; flag still gates
- `collection-sheets`: saved-sheet header action opens Document Review

## Approach

`collection.sheet` object action checks the flag and returns
`collection.action_collection_document_review` (`tag` `collection.document_review`) with
a mandatory sheet id. RPCs stay on `collection.voucher` (`get_review_queue`,
`action_review_approve`, `action_review_reject`, `action_review_set_rotation`): each
MUST take the sheet id and fail closed. OWL reads the action param and forwards it. Drop
menu XML; add sheet-form header button; remove `ir.ui.menu` blacklist.

## Affected Areas

| Area                                                                                                                        | Impact   | Description                     |
| --------------------------------------------------------------------------------------------------------------------------- | -------- | ------------------------------- |
| `models/collection_sheet.py`                                                                                                | Modified | Object action + optional helper |
| `models/collection_voucher.py`                                                                                              | Modified | Sheet-scoped queue/mutations    |
| `models/ir_ui_menu.py`                                                                                                      | Removed  | Blacklist obsolete              |
| `views/collection_views.xml`                                                                                                | Modified | Sheet header button             |
| `views/collection_document_review_views.xml`                                                                                | Modified | Remove menu                     |
| `static/src/document_review/document_review_action.esm.js`                                                                  | Modified | Pass sheet param                |
| `tests/test_collection_document_review.py`, `tests/test_collection_document_review_flag.py`, `tests/test_collection_acl.py` | Modified | Sheet-scoped RPCs, flag, ACL    |

## Risks

| Risk                                        | Likelihood | Mitigation                      |
| ------------------------------------------- | ---------- | ------------------------------- |
| Direct `/odoo/document-review` stays global | Med        | Fail closed without sheet id    |
| Cross-sheet decide if OWL omits param       | Med        | Server validates every mutation |
| Reviewers cannot find review                | Low        | Header on the open sheet        |

## Rollback Plan

Restore Collections menu, global `get_review_queue`, prior OWL/RPC signatures (no sheet
id), and flag-driven menu blacklist. Drop any non-stored helper. No stored data to undo.

## Dependencies

- `res.company.document_review_enabled`
- Client action tag `collection.document_review`
- `collection.voucher.sheet_id`

## Success Criteria

- [ ] No menu; saved-sheet header opens review when flag ON, hidden/refused when OFF
- [ ] Queue is only that sheet’s eligible pending attached vouchers
- [ ] Missing/invalid/other-sheet or no-sheet RPCs refuse (not empty-queue success)
- [ ] `invoke test -m collection` covers the new contract
