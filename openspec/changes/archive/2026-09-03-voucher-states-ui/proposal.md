Closed plan used instead of a question round.

# Proposal: Voucher States UI

## Intent

Operators mix voucher pending/approved/rejected with allocation Validate/Reject; stages
kanban can skip Document Review. Replace with Draft → Validated by Seller → Validated by
Collections. **No Reject.** Review is the only Collections path. Odoo-only.

## Scope

### In Scope

- Three-state Selection; ORM/UI `draft`; MCP `_collection_create_vouchers` stamps
  `validated_seller`; form **Validate by Seller** from Draft; Collections only via
  Review Approve (queue `validated_seller` + proof; drop Review Reject)
- SQL remap before ORM; delete stages kanban; keep Reassign Customers kanban
- Unlink only `draft`; attachment reopen → `validated_seller`; drop rejected-allocation
  gate; list/search/form UX; menu `sequence=10`; extra chatter tracking
- Manifest `19.0.1.31.0`, `migrations/19.0.1.31.0/post-migrate.py`, tests

### Out of Scope

- Nebula agent (overrides config Nebula-in-scope rule)
- Snapshot `decision` vocabulary or snapshot-row migrate; form path to Validated by
  Collections; new states; Reject
- Sheets, connectors, seller-lookup, extra groups, `sudo()`, Doodba deps

## Capabilities

### New Capabilities

- None

### Modified Capabilities

- `collection-vouchers`: lifecycle, defaults, unlink, attachment reopen, UI, MCP stamp,
  chatter tracking
- `document-review`: queue `validated_seller`; Approve → `validated_collections`; remove
  Reject; drop History tab; snapshots stay `decision=approved|rejected`
- `collection-allocations`: drop not-`rejected` gate
- `collection-sheet-report`: print-includes voucher key names only

## Approach

In-place Selection remap (exploration 1 + snapshot 2A). SQL CASE before ORM:
`pending`→`draft`, `approved`→`validated_collections`, `rejected`→`draft`. Intercept
refuses raw `validated_collections`; `validated_seller` only via seller action or MCP
create. Review Approve writes voucher `validated_collections` and snapshots
`decision="approved"`. `<delete>` stages kanban; `view_mode` `list,form`; statusbar not
clickable; drop `group_expand` on `state`.

## Affected Areas

- Modified: voucher model; snapshot `decision` stays `approved`/`rejected`; MCP stamp;
  allocation rejected gate; views; OWL; tests; four specs above; leftover `AGENTS.md`
  keys
- New: `migrations/19.0.1.31.0/post-migrate.py` (1.28.0 SQL pattern)
- Manifest: `19.0.1.30.0` → `19.0.1.31.0`

## Risks

- High: leftover old keys crash Selection browse → SQL remap before ORM
- High: coupled state/decision write → voucher `validated_collections`, snapshot
  `approved`
- Med: leftover stages kanban view → `<delete>` + `view_mode` `list,form`
- Med: MCP state consumers → Nebula out of scope
- High: 400-line review budget → `sdd-tasks` chained-PR forecast

## Rollback Plan

Revert addon to `19.0.1.30.0`. Restore Reject, stages kanban, History, coupled snapshot
writes. Reverse SQL: `validated_collections`→`approved`; `validated_seller` and migrated
`draft`→`pending`. Migrated rejects stay `draft`.

## Dependencies

- `migrations/19.0.1.28.0` SQL CASE pattern; `-u collection` after ship

## Success Criteria

- [ ] ORM/UI `draft`; MCP `validated_seller`; Seller button from Draft only; Collections
      only via Review Approve; no Reject
- [ ] Review queues `validated_seller` + proof; Approve snapshots `decision="approved"`
- [ ] Upgrade remaps keys; stages kanban gone; Reassign kanban kept; menu sequence 10
- [ ] All states may allocate; unlink only `draft`; attachment reopen →
      `validated_seller`; extra chatter tracking; History tab gone; tests and scoped
      pre-commit pass
