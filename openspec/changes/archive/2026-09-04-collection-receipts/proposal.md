# Proposal: Collection Receipts

## Proposal question round

Skipped (automatic). Locked:

| Lock             | Value                                                                            |
| ---------------- | -------------------------------------------------------------------------------- |
| Issuer / pairing | ERP issues; Odoo groups. Agent create.                                           |
| Split / apps     | Voucher MAY split via `receipt.value`. Derived apps by kind.                     |
| Totals / mix     | `total_values >= total_applied`; surplus `amount_on_account`. Quotations = debt. |
| Compat           | `invoices[]` no splits → one `invoice` receipt; unsplit/empty → none/zero.       |
| Out              | Cross-customer; junction; paid-doc model; B/C; Odoo sequence/PDF/fiscal.         |
| Ship             | `19.0.1.34.0` additive, no backfill; no `sudo()`/new groups; `ir.rule` + ACL.    |

## Intent

One voucher, two ERP receipts (invoice vs quotation). Odoo groups by kind.

## Scope

### In Scope

- Receipt + value models; derived apps; freeze; issued; ERP hand-off; compat default;
  views/ACL/tests; `19.0.1.34.0`; AGENTS.md + deltas
- Lift kind ban (omit → `invoice`); persist keeps kind; debt `document_kind`;
  `create_receipt` + sqlite stub; hash splits/kind; get `receipts`

### Out of Scope

- Backfill; forbidden migrate folders; in-tree sqlite or Nebula

## Capabilities

### New Capabilities

- `collection-receipts`: header, values, derived apps, freeze, issued, ERP hand-off,
  compat create

### Modified Capabilities

- `collection-allocations`: MCP kind + splits; hash; persist keeps kind; unlink cascade;
  freeze `receipt_ids`; get `receipts`
- `collection-connectors`: debt `document_kind`; `_DISPATCH_OPS` write op; sqlite stub
  (spec-level)

## Approach

A: `UNIQUE(allocation_id, document_kind)`; values = voucher amounts. Group on persist;
push on Close; `draft` until ERP id then `issued`. Sqlite no-write stub (fake id).

## Affected Areas

- Models: new receipt + value; allocation `receipt_ids`/freeze/unlink; line keep kind;
  connector debt kind + `_DISPATCH_OPS`
- Tools: create splits/kind/hash/compat; get `receipts`
- `views/`, `security/`, `__manifest__.py`, `migrations/19.0.1.34.0/`: UI; ACL
  `1,1,1,1`; bump; no backfill
- `AGENTS.md`, specs, tests: lift bans; deltas; receipt tests

## Risks

| Risk                          | Likelihood | Mitigation                            |
| ----------------------------- | ---------- | ------------------------------------- |
| Kind/`_DISPATCH_OPS` leftover | High       | Lift both here                        |
| Sqlite/Nebula lag             | Med        | Compat receipt; stub; coordinated PRs |
| Hash / amend wipe             | High       | Old hash; persist keeps kind          |
| Review >400 lines             | High       | Chained PRs                           |

## Rollback Plan

Revert to `19.0.1.33.0`. Drop new models/views/ACL. Restore kind ban, hash,
`_DISPATCH_OPS`. No backfill.

## Dependencies

- `collection_connector_sqlite`: debt kind / quotations seed + stub `create_receipt`
  (read-only file)
- `nebula-agent`: `InvoiceApplication` + confirm + `request_id` hash for splits/kind

## Success Criteria

- [ ] Compat receipts; voucher MAY split two ways; derived apps; surplus
      `amount_on_account`
- [ ] Omit kind → `invoice`; persist keeps kind; splits/kind hashed; old payloads replay
- [ ] Close → `create_receipt`; stub fake id; `draft`→`issued`; get `receipts`
- [ ] Issued immutable; freeze/unlink; no `sudo()`; `ir.rule` + ACL; `19.0.1.34.0`
      additive, no backfill
