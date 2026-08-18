# Design: Auto-assign Open Sheet

## Technical Approach

Add sheet `state` (`open`/`closed`) and resolve membership in
`collection.voucher.create` so form, RPC, and MCP all-new share one path. MCP replay
never calls `create`. One-open is a count on new ops only (leftovers stay closable).
Designed from proposal, exploration, and current code (specs may still be writing).
Sequences and ACL unchanged (`base.group_user` CRUD only).

## Architecture Decisions

| Decision | Options | Tradeoff | Choice |
|----------|---------|----------|--------|
| Lifecycle | `state` vs `is_open` vs dates | Selection fits statusbar; others fight list UX | `state` `open`/`closed`, default `open`, required. Existing rows open on column add. Manifest **19.0.1.12.0**. No UNIQUE. No `migrations/19.0.1.12.0/` — ORM default fills the column (`19.0.1.7.0` was a rename, not a pattern here). |
| Auto-assign | ORM `create` vs MCP-only vs MCP `sheet_id` | ORM covers UI+MCP | Before `super` in `@api.model_create_multi` `create` when `seller_id` set and `sheet_id` omitted/falsey. One resolve per seller in `vals_list`. Explicit `sheet_id` honored if target **open** and same seller. Null seller unassigned. Later `seller_id` write does not assign. |
| One-open | New-ops count vs `@api.constrains` vs UNIQUE | Constraint/UNIQUE blocks Close extras and `-u` | `_open_sheets_for_seller` (`@api.private`): 0 create, 1 use, `>1` `UserError`. Guards: sheet `create` if resulting state is open, `action_reopen`, Action, auto-assign. Not a `write` constrains. |
| Concurrency | Advisory lock vs UNIQUE vs none | UNIQUE fails `-u` | Blocking `pg_advisory_xact_lock` on auto-assign and create-open, inside the MCP savepoint transaction. |
| Close/Reopen | Header + intercept vs clickable statusbar | Odoo 19 statusbar `clickable` defaults **true** | `action_close` / `action_reopen`; raw `write({'state': …})` routed like voucher approve/reject via `collection_sheet_audited_state`. |
| Freeze | Dual write vs constraint vs view | Constraint misses remove-off-closed; view is UX | Closed sheet `write` rejects `voucher_ids` commands. Voucher `create`/`write` rejects add to closed **and** remove/reassign off closed. `unlink` still allowed (`ondelete="set null"`) via `collection_sheet_unlinking`. Review RPCs unchanged. |
| Action | Create-new vs attach-to-open | Product keeps create-new | After `_seller_for_sheet_action`, reject if seller has **≥1** open. Happy path: unassigned selection and zero opens (after unlink, or seller stamped later). |
| MCP | Inherit ORM vs tool assign | Schema freeze | No change to args/response `{id,name,state,document_id}`. All-new `Voucher.create` inherits. Replay stays read-only. |

**Lock key:** `SELECT pg_advisory_xact_lock(hashtext(%s), %s)` namespace
`'collection.sheet.open'`, `int(seller_id)` (`odoo.tools.SQL`). Held until the DB
transaction ends (savepoint rollback does not release xact locks).

## Data Flow

```
vals_list (seller set, sheet_id omitted)
    → pg_advisory_xact_lock(hashtext('collection.sheet.open'), seller_id)
    → _open_sheets_for_seller
         0 → Sheet.create(open) → set sheet_id
         1 → use that id
        >1 → UserError
    → super().create   (MCP savepoint wraps this)

Action: eligibility → open≥1? UserError → else Sheet.create + assign
Close:  action_close → closed (membership frozen)
Reopen: open≥1? UserError → else open
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `models/collection_sheet.py` | Modify | `state`; count + lock; create/reopen guards; close/reopen; intercept `state`; freeze `voucher_ids`; unlink context |
| `models/collection_voucher.py` | Modify | Auto-assign in `create`; freeze `sheet_id`; Action open-count after existing checks |
| `tools/collection_voucher.py` | None | Inherit ORM; no schema/payload change |
| `views/collection_views.xml` | Modify | Close/Reopen; `statusbar_visible="open,closed"` + `options="{'clickable': False}"`; list/search `state`; membership readonly when closed |
| `__manifest__.py` | Modify | `19.0.1.12.0` |
| `tests/test_collection_sheet.py` | Modify | Drop `assertNotIn("state")`; two same-seller sheets: close first or two sellers; Action/auto-assign/freeze |
| `tests/test_collection_ui.py` | Modify | Require sheet statusbar + buttons |
| `tests/test_collection_mcp_tool.py` | Modify | All-new assign; exact replay does not attach |
| `tests/test_collection_document_review.py` | Modify | Two-sheet cases: close-first or two sellers |

## Interfaces / Contracts

Sheet `state`: `open` (default) \| `closed`. Context:
`collection_sheet_audited_state`, `collection_sheet_unlinking`. MCP: no `sheet_id` in
args or `{vouchers:[…]}`.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|--------------|----------|
| Unit | Default open; Close/Reopen; intercept `state`; one-open; leftover `>1` still closable; freeze; unlink closed; explicit `sheet_id`; null seller; batch-per-seller; Action ≥1 open | `test_collection_sheet.py` |
| Unit | Statusbar + button invisibles; membership readonly when closed | `test_collection_ui.py` |
| Integration | MCP all-new assigns; exact replay leaves `sheet_id`/`write_date`; payload keys unchanged | `test_collection_mcp_tool.py` |

`_create_voucher()` with a seller assigns when 0/1 open exists; unassigned cases omit
seller, unassign while open, or unlink first.

## Threat Matrix

N/A — ORM/UI/MCP inside Odoo; no routing/shell/process-integration boundary.

## Migration / Rollout

`-u collection` to `19.0.1.12.0`. ORM adds `state` default `'open'` (all existing
sheets open). Operators close extras; auto-assign/Action fail-closed while `>1` open.
No UNIQUE, no data-fix script, no unassigned backfill. Rollback: revert `19.0.1.11.0` /
snapshot.

## Open Questions

None
