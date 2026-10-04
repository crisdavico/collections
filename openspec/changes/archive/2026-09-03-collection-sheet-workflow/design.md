# Design: Collection Sheet Workflow

## Technical Approach

Reuse `collection_sheet_audited_state` / `collection_allocation_audited_state`. Extend
the sheet Selection; replace Close/Reopen with Confirm/Close/Cancel/Open; keep MCP
`_open_sheets_for_seller` on `open`. Specs: `collection-sheets`,
`collection-allocations`, `collection-vouchers`, `collection-sheet-report`,
`document-review`. Strict TDD.

## Architecture Decisions

| Decision       | Options                                                         | Tradeoff                                                            | Choice                                                                                                                                     |
| -------------- | --------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Sheet states   | Four Selection keys vs flag on `open`                           | Flag would still match MCP `open` unless every helper special-cases | Keys `open`/`proposal`/`closed`/`cancelled`; default `open`; no SQL remap                                                                  |
| Transitions    | Audited actions vs raw `write`                                  | Raw writes already intercept today                                  | Intercept `state` → `action_confirm`/`action_close`/`action_cancel`/`action_open`; drop `action_reopen`                                    |
| Confirm gate   | Every member `validated_collections` vs also require proof flag | Proof/review-off already block that state                           | `UserError`, no persist, empty members pass                                                                                                |
| Allocation iff | Draft on Open/Proposal/Cancelled; confirmed iff Closed          | Cancelled drafts would be writable without a sheet-state guard      | Close confirms; Cancel drafts; Confirm does not touch allocations; freeze `_FROZEN_FIELDS` when sheet is Closed/Cancelled even if draft    |
| Debt tab       | Nested `allocation_ids.line_ids` vs related stored inverse      | Nested cannot be a flat list                                        | Related stored `sheet_id` + readonly `partner_id` on the line; sheet `debt_line_ids` One2many; create/delete off                           |
| Reassign       | Keep kanban vs delete                                           | Kanban is the only `group_expand` consumer                          | Delete header, XMLID, `group_expand`, auto-follow; keep `_check_voucher_allocation_partner`; refuse `partner_id` while `allocation_id` set |
| Review RPC     | Header hide only vs server gate                                 | Header-only is bypassable                                           | `_require_review_sheet` and `action_open_document_review` refuse non-`open`                                                                |
| MCP            | Change domain vs keep `open`                                    | Changing would block a new Open while Proposal exists               | No tool semantics change; add regressions                                                                                                  |

## Data Flow

```
Open --Confirm(gate)--> Proposal --Close--> Closed --Cancel--> Cancelled
                         |                                      |
                         +--Cancel------------------------------+
Cancelled --Open(one-open)--> Open
```

Confirm writes `proposal` only. Close confirms allocations then `closed`. Cancel writes
`cancelled` and drafts allocations (audited, then `_check_sheet_state_iff`). Open from
Cancelled: one-open lock; allocations stay `draft`.

## File Changes

| File                                                           | Action | Description                                                                                                                                                                                       |
| -------------------------------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `models/collection_sheet.py`                                   | Modify | Four-state Selection; Confirm/Close/Cancel/Open; reject non-open create; freeze Proposal+Closed+Cancelled; `debt_line_ids`; drop Reopen/reassign action; Review Open-only; unlink refuse non-open |
| `models/collection_allocation.py`                              | Modify | iff draft on Open/Proposal/Cancelled; sheet-state write guard; audited message Close/Cancel/Open                                                                                                  |
| `models/collection_allocation_line.py`                         | Modify | related stored `sheet_id`/`partner_id`; `write`/`@api.ondelete` when sheet Closed/Cancelled                                                                                                       |
| `models/collection_sheet_report.py`                            | Modify | recon freeze Closed **and** Cancelled                                                                                                                                                             |
| `models/collection_voucher.py`                                 | Modify | freeze membership + `_REVIEW_EDITABLE_FIELDS` when sheet not Open; drop follow/`group_expand`; `_require_review_sheet` Open-only                                                                  |
| `views/collection_views.xml`                                   | Modify | buttons; statusbar four keys; three pages; `<delete>` reassign kanban; XLSX last before `state`                                                                                                   |
| `views/collection_allocation_views.xml`                        | Modify | readonly from `sheet_id.state`; voucher M2M Open-only                                                                                                                                             |
| `tools/allocation_lookup.py`, `tools/collection_allocation.py` | Verify | `_open_sheets_for_seller` unchanged                                                                                                                                                               |
| `__manifest__.py`                                              | Modify | `19.0.1.33.0`                                                                                                                                                                                     |
| `migrations/19.0.1.33.0/post-migrate.py`                       | Create | unlink reassign view/XMLID only (pattern `19.0.1.32.0`); no state remap                                                                                                                           |
| `tests/test_collection_*.py`                                   | Modify | RED lifecycle, gate, tabs, freeze, PDF/XLSX, mail, manifest, MCP Proposal                                                                                                                         |
| `AGENTS.md`, `readme/`                                         | Modify | workflow/notebook docs                                                                                                                                                                            |

## Interfaces / Contracts

Sheet Selection: `open`, `proposal`, `closed`, `cancelled`. Create MUST omit or pass
`open`. Raw `state` write without audited context MUST route to the matching action or
`UserError`.

Allocation iff (skip during audited writes):

- `draft` iff sheet in `{open, proposal, cancelled}`
- `confirmed` iff sheet `closed`

Voucher freeze when `sheet_id.state in {proposal, closed, cancelled}`: `sheet_id`,
`partner_id`, and `_REVIEW_EDITABLE_FIELDS`. `allocation_id` stays writable in Proposal
(allocation `voucher_ids`). Chatter and PDF/XLSX stay allowed.

Non-obvious: related stored line `sheet_id` is the Debt tab inverse. Create/delete stay
off so RPC never writes the related field; `amount_applied` writes the line.

## Testing Strategy

| Layer                  | What to Test                                                                                          | Approach                                                                               |
| ---------------------- | ----------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Unit (TransactionCase) | Transitions, gate, iff, freeze, unlink, unassign-first, Review Open-only, recon, line RPC             | RED in sheet/allocation/voucher/document_review tests; line guards in allocation tests |
| Unit UI                | Buttons, statusbar, three pages, columns, modifiers, reassign gone                                    | Replace asserts in `test_collection_ui.py`                                             |
| Integration            | PDF/XLSX all four states; MCP Proposal does not occupy open; chatter tracking; manifest `19.0.1.33.0` | Existing report/xlsx/mcp/mail/migration tests                                          |
| E2E                    | N/A                                                                                                   | Not in `openspec/config.yaml`                                                          |

Runner: `invoke test -m collection --mode=update`.

## Threat Matrix

N/A — ORM/views plus a view-unlink migrate. No routing, shell, subprocess, VCS/PR, or
process-integration boundary.

## Migration / Rollout

Bump to `19.0.1.33.0`. Existing `open`/`closed` rows stay; related line fields recompute
on `-u`. `migrations/19.0.1.33.0/post-migrate.py` unlinks the reassign view/XMLID (same
SQL as `19.0.1.32.0`) plus XML `<delete>`. Rollback: revert the `collection` commit.

## Open Questions

None. Empty Confirm remains vacuously allowed. Nebula stays out of scope.
