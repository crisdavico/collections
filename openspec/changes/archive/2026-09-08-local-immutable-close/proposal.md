# Proposal: Local Immutable Close

## Proposal question round

Skipped. Settled: Close is local; draft receipts become `closed` with no
`external_receipt_id`; Cancel reopens those to `draft`; `issued` unchanged;
MCP/Nebula/sqlite out of scope; no SQL backfill.

## Intent

Close currently dispatches connector `create_receipt` while the sheet is `proposal`, so
it fails without ERP. Close MUST freeze the aggregate locally. Cancel remains the
explicit unfreeze.

**User impact:** Administration Closes a proposal sheet with no ERP. Receipts stay local
(`closed`). MCP Seller Close is unchanged.

## Scope

### In Scope

- `action_close()` from `proposal` only: no connector, no `create_receipt`
- One transaction: draft receipts → `closed`; allocations → `confirmed`; sheet →
  `closed`
- Receipt `closed`; audited `draft ↔ closed`; reject raw state writes
- Harden create/write/unlink freeze on closed/cancelled associates
- Manifest `19.0.1.44.0`; `AGENTS.md`; OpenSpec deltas

### Out of Scope

- Nebula, MCP Seller Close, `collection_connector_sqlite`
- Removing `create_receipt` (keep unused from Close)
- SQL migration or remapping `issued`

## Capabilities

### New Capabilities

- None

### Modified Capabilities

- `collection-sheets`: Close is local-only. Cancel from `closed` still drafts
  allocations; freeze until Reinstate → `submitted`.
- `collection-receipts`: Add `closed`. Remove Close→`create_receipt`. Cancel reopens
  local `closed` to `draft`; `issued` unchanged. Freeze includes create.
- `collection-allocations`: Closed/cancelled freeze MUST refuse **create** of
  allocations, lines, and revisions (write/unlink already specified).

## Approach

Strip Close dispatch in `models/collection_sheet.py`. Close every draft receipt via an
audited context. Keep connector `create_receipt` unused. Add `closed` in
`models/collection_receipt.py` and views. Centralize `raise_if_sheet_frozen` so direct
child creates fail. Vouchers freeze via the parent sheet.

## Affected Areas

- `models/collection_sheet.py` — Modified: local Close; Cancel reopens receipts
- `models/collection_receipt.py` + views — Modified: `closed`; audited transitions
- `models/collection_common.py` + child models — Modified: frozen-sheet CRUD
- `__manifest__.py`, `AGENTS.md` — Modified: `19.0.1.44.0`; Close contract
- `tests/test_collection_{receipt,sheet,allocation,voucher}.py` — Modified
- MCP / Nebula / sqlite — Unchanged

## Risks

- Tests still expect Close dispatch (High) — rewrite receipt Close tests first
- Direct child create bypasses freeze (Med) — centralize checks; cover create
- Cancel mutates historical `issued` (Low) — Cancel only `closed` → `draft`
- `collection_receipt_proposal` drift (Med) — run that module after upgrade

## Rollback Plan

Revert to `19.0.1.43.0`. No SQL; varchar `state` stays valid. Close again requires a
connector.

## Dependencies

- Collection `19.0.1.43.0`. Connector optional after this change.

## Success Criteria

- [ ] Close from `proposal` closes receipts, confirms allocations, closes the sheet,
      assigns no `external_receipt_id`, never calls the connector
- [ ] Frozen sheet/associates refuse create/write/unlink of business data
- [ ] Cycle `closed` → Cancel → `cancelled` → Reinstate → `submitted`: local receipts
      `draft`; `issued` unchanged
- [ ] Manifest `19.0.1.44.0`; no migrate folder
- [ ] `invoke test -m collection --mode=update`; `collection_receipt_proposal`
      regression; scoped pre-commit
