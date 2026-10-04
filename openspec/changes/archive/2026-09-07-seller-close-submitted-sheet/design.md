# Design: Seller Close for Collection Sheets

## Technical Approach

Fifth key `submitted` ("Submitted by Seller"; PDF "Rendida") is seller handover. Named
editable-iff sets in `models/collection_common.py` replace sheet-state `"open"`
literals. MCP write stays `SELLER_SHEET_STATES` (`open`). Admin work uses
`ADMIN_EDITABLE_SHEET_STATES`. `open` is create-only. Strict TDD; six stacked PRs.
Confirm sites: **83 in 14 files**, not 163/12.

## Architecture Decisions

| Option                             | Tradeoff                                     | Decision                                                                   |
| ---------------------------------- | -------------------------------------------- | -------------------------------------------------------------------------- |
| Fifth key vs flag on `open`        | Flag still matches `_open_sheets_for_seller` | **`submitted`**                                                            |
| Editable-iff vs frozen-iff         | Frozen-iff un-freezes new keys               | **Editable-iff**                                                           |
| Dispatcher vs 1:1 map              | Two actions target `submitted`               | **Private dispatcher**; drop `"open"`                                      |
| Combined decls+state vs two writes | Two writes race freeze                       | **One audited write inside lock**                                          |
| Reinstate → `submitted` vs `open`  | `open` trips one-open                        | **`action_reinstate`**; drop that path's `_raise_if_seller_has_open_sheet` |
| MCP `seller_id` vs `sheet_id`      | Sheet id can target a frozen row             | **`seller_id` only**; 0 open → `UserError`                                 |
| `sudo` vs ACL                      | Mixin tools never sudo                       | **`check_access("write")`**                                                |
| Migrate folder vs leftover pin     | Additive Selection; no SQL remap             | **No `migrations/19.0.1.42.0/`**                                           |

Do not change `_closed_membership_user_error` or `_OUTSTANDING_INVOICE_STATES`.

## Data Flow

Advisory lock on `(company, seller)`:

```
close: lock → invalidate_recordset([state, voucher_ids]) → draft gate → decls+submitted
create: same lock; 0 open → new open sheet (close-wins) or draft gate sees new voucher
```

`invalidate_recordset` is load-bearing. Explicit-`sheet_id` ORM create skips the lock
(benign; Confirm still refuses drafts). Comment it; no `FOR UPDATE`. Retry raises.

## File Changes

| File                                                       | Action | Why                                                           |
| ---------------------------------------------------------- | ------ | ------------------------------------------------------------- |
| `models/collection_common.py`                              | Modify | Named sets (PR 1 today; PR 3 widen)                           |
| `models/collection_sheet.py`                               | Modify | Selection, dispatcher, close, reinstate, gates                |
| `models/collection_voucher.py`                             | Modify | Freeze/review → admin-editable                                |
| `models/collection_allocation.py`                          | Modify | `DRAFT_SHEET_STATES` + error copy `:355-358`                  |
| `models/collection_sheet_report.py`                        | Modify | Rendida; recon split; freeze-before-super                     |
| `tools/collection_allocation.py`                           | Modify | Keep seller-axis `:710`                                       |
| `tools/sheet_report.py`, `tools/__init__.py`               | Modify | Identity helper; import close                                 |
| `tools/collection_sheet_close.py`                          | Create | MCP `close_collection_sheet`                                  |
| `views/collection_views.xml`                               | Modify | Seller Close before Confirm; Reinstate; gates; recon readonly |
| `views/collection_allocation_views.xml`                    | Modify | Minimal widen `:137`                                          |
| `__manifest__.py`, `AGENTS.md`, `readme/DESCRIPTION.md`    | Modify | `19.0.1.42.0`; five-state leftover pin                        |
| `tests/common_connector.py` + `tests/test_collection_*.py` | Modify | Helpers + RED/GREEN                                           |
| Sibling `collection_receipt_proposal/tests/common.py`      | Modify | `_confirm()` in PR 5 — **outside `apply.roots`; consent**     |

## Interfaces / Contracts

```python
SELLER_SHEET_STATES = frozenset({"open"})
ADMIN_EDITABLE_SHEET_STATES = frozenset({"open", "submitted"})  # after PR 3
DRAFT_SHEET_STATES = frozenset({"open", "submitted", "proposal", "cancelled"})
CONFIRMED_SHEET_STATE = "closed"
FROZEN_SHEET_STATES = frozenset({"closed", "cancelled"})
# _sheet_is_frozen: bool(sheet) and sheet.state not in ADMIN_EDITABLE_SHEET_STATES
```

```python
_STATE_WRITE_ACTIONS = {
    "proposal": "action_confirm", "closed": "action_close",
    "cancelled": "action_cancel", "submitted": "_dispatch_submitted_state_write",
}  # no "open"
# dispatcher: set(self.mapped("state")); refuse mixed; open→action_seller_close;
# cancelled→action_reinstate. Error names Seller Close and Reinstate.
# Combined {decls, state: submitted} outside audited context → UserError.
```

```python
def action_seller_close(self, cash_on_hand=None, commission_withheld=None):
    # no ensure_one; lock first; invalidate_recordset(["state","voucher_ids"]);
    # assert SELLER_SHEET_STATES; @api.private draft-offender helper;
    # one audited decls+state write inside lock; no extra message_post.
```

MCP on `muk_mcp.mixin` (clone `sheet_report.py`): `category="write"`, `registry="mcp"`,
required `seller_id`; optional amounts as `number` (parse
`_collection_normalize_amount`). Flow: internal user →
`_collection_require_internal_seller` → lock → `_open_sheets_for_seller` →
`check_access("write")` → `action_seller_close`. 0 open → `UserError` not
`{sheet: null}`. Shared `_collection_sheet_identity`. No `sudo()`. Allocation
write/lookup/PDF stay open-only. ACL: `base.group_user` + company `ir.rule`.

## Testing Strategy

| Layer       | What                                                   | How                                       |
| ----------- | ------------------------------------------------------ | ----------------------------------------- |
| Unit        | Sets, dispatcher, close/reinstate, recon, MCP, no-sudo | `TransactionCase`; RED/GREEN per PR       |
| Integration | 83 Confirm sites; sibling `_confirm()` from PR 5       | `invoke test -m collection --mode=update` |
| E2E         | N/A                                                    | Manual after PR 6                         |

PR 1 scan: no bare sheet-state `"open"` outside `collection_common.py` (invoice `open`
exempt). Helpers `force_sheet_state` / `advance_sheet_to`. Drop transitional Confirm
canary in PR 5.

## Threat Matrix

N/A — Odoo state-machine + MCP mixin tool; no routing/shell/subprocess/VCS/process
boundary.

## Migration / Rollout

No SQL remap. Manifest `19.0.1.42.0` in PR 2; leftover scanner + AGENTS pin (no
`migrations/19.0.1.42.0/`). Stacked-to-main:

| PR  | Unit                                                                  | Budget |
| --- | --------------------------------------------------------------------- | ------ |
| 1   | Named sets (today's values), scan, helpers; no version bump           | ~95    |
| 2   | Dormant `submitted` + docs + manifest                                 | ~160   |
| 3   | Admin on submitted; Confirm `open\|submitted`; recon split            | ~210   |
| 4   | Seller Close, dispatcher, buttons, recon readonly                     | ~240   |
| 5   | Confirm `submitted`-only; migrate sites **with sibling `_confirm()`** | ~280   |
| 6   | Reinstate + MCP close                                                 | ~265   |

Rollback: revert newest-first; drop close-tool import. Lint: scoped pre-commit on
`collection/**`.

## Open Questions

None.
