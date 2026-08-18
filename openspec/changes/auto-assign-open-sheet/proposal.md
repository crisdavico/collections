# Proposal: Auto-assign Open Sheet

## Intent

Sellers need new vouchers on one working sheet without a manual Action after every
create. Sheets have no lifecycle, so a period cannot be frozen.

## Scope

### In Scope

- Sheet `state` `open`/`closed`; header Close/Reopen; freeze membership when closed
- One open per seller for new ops (create / reopen / Action / auto-assign);
  `UserError` if that seller already has >1 open
- ORM `voucher.create` auto-assign when `seller_id` set and `sheet_id` omitted (UI +
  MCP all-new)
- Keep list Action as create-new-sheet; reject if any open exists
- Manifest `19.0.1.12.0`; rewrite no-state and two-open tests

### Out of Scope

- Nebula; MCP response `{id,name,state,document_id}` (voucher state)
- UNIQUE SQL; backfill unassigned vouchers; auto-assign on later seller write
- Extra ACL groups; Document Review queue changes

## Capabilities

### New Capabilities

- None

### Modified Capabilities

- `collection-sheets`: open/closed workflow, one-open, freeze, Close/Reopen, Action
  reject-if-open-exists
- `collection-vouchers`: create auto-assign when seller set; MCP all-new inherits;
  exact replay still no mutation / sheet attach

## Approach

`state` Selection `open`/`closed` (default `open`; existing rows open). Count guards on
create/reopen/Action/auto-assign only. No UNIQUE (would fail `-u`). Optional
`pg_advisory_xact_lock(seller_id)` on auto-assign/create-open.

Voucher `create`: unique open → assign; none → create then assign; several →
`UserError`. Explicit `sheet_id` honored if valid. Null seller stays unassigned. Closed
sheets reject add/remove/reassign until reopen. Non-clickable statusbar. MCP replay
never calls `create`.

## Affected Areas

- `models/collection_sheet.py` — `state`, close/reopen, one-open, freeze
- `models/collection_voucher.py` — create auto-assign; freeze `sheet_id`; Action
- `tools/collection_voucher.py` — inherit ORM assign; replay no sheet writes
- `views/collection_views.xml` — Close/Reopen, statusbar, membership readonly
- `__manifest__.py` — bump `19.0.1.12.0`
- `tests/test_collection_{sheet,ui,mcp_tool,document_review}.py` — state, statusbar,
  assign, replay, two-seller

## Risks

- **Upgrade multi-open (High):** all sheets start open. Fail closed on >1; close extras.
- **Concurrent double-open (Med):** advisory lock; next write still fail-closed.
- **400-line review budget (High):** `sdd-tasks` forecast chained PRs.
- **Naive one-open constraint (Med):** would block closing extras; new-ops guards only.

## Rollback Plan

Revert to `19.0.1.11.0` and restore prior Python/XML/tests. Drop `state` via reverse
upgrade or DB snapshot. No Nebula/MCP schema to unwind.

## Dependencies

Odoo 19 `models.Constraint`; no new deps. Upgrade required for `state`.

## Success Criteria

- [ ] Unique open receives new seller-stamped creates (UI + MCP all-new); none → create open
- [ ] Explicit `sheet_id` honored; null seller unassigned; no backfill; later seller write does not assign
- [ ] Second open rejected; >1 open after upgrade `UserError` on those ops; closing extras works
- [ ] Closed sheets frozen until reopen; MCP exact replay does not attach; response unchanged
- [ ] Manifest `19.0.1.12.0`; no-state / two-open tests updated; `invoke test -m collection` passes
