# Proposal: Align Allocation Contracts

Sellers cannot register `echeck`, `cash`, or `retention_certificate` because Seedian
rejects Nebula’s `CollectionAllocationRequest.model_dump(mode="json")`. Persist those
dumps; keep replay, draft writes, `balance_seen` revalidation, receipt persist, and
`{sheet_id, vouchers, allocation}`.

## Proposal question round

Settled assumptions (not open questions): dump is authoritative; one customer;
`extra=forbid` and type-owned fields; cash has no proof; no sudo/MuK; persist six dump
types, reject MCP `unsupported`; flattened discovery; OWL labels may lag; empty
`applications[]` = on account; union allow-lists; scope is collection + Nebula
`AGENTS.md` (not MuK, OWL/PDF/XLSX, Nebula schema, sibling Document Review change).

## Intent

Unblock Nebula submit for the three missing types and dump wire shape.

## Scope

### In Scope

- Catalog XMLIDs, Selection, `retention_kind`; manifest `19.0.1.40.0` union migrate
- Runtime-strict flattened parse (seven types, unknown keys, decimal strings, null omit,
  cash without proof, `image/jpg` alias)
- Golden tests; keep `_collection_parse_payment_vals` `unsupported` reject; Nebula
  `AGENTS.md` note

### Out of Scope

MuK; OWL/views/reports; Nebula schema/tools; sibling Document Review change.

## Capabilities

### New Capabilities

- None

### Modified Capabilities

- `collection-vouchers`: seven catalog/Selection codes; `retention_kind`; cash without
  proof; `image/jpg` alias
- `collection-allocations`: strict nested-key parse; decimal-string amounts; keep
  replay/draft/revalidation/response; keep MCP `unsupported` reject

`collection-receipts` unchanged (wire rules live on allocations).

## Approach

Exploration approach 1: MuK-safe flattened schema (seven-value enum, optional
`retention_kind`, number-or-string amounts). Python enforces dump exactness.
Union-migrate via `_collection_enable_all_document_types`. TDD goldens first.

## Affected Areas

| Area                                                       | Impact       | Description                                          |
| ---------------------------------------------------------- | ------------ | ---------------------------------------------------- |
| `tools/collection_voucher.py`                              | Modified     | Types, `retention_kind`, strict parse, MIME alias    |
| `tools/collection_allocation.py`                           | Modified     | Receipt amount schema/runtime                        |
| `models/collection_voucher.py`, snapshot, `res_company.py` | Modified     | Selection, `retention_kind`, `COLLECTION_TYPE_CODES` |
| `data/collection_document_type_data.xml`                   | Modified     | Three XMLIDs                                         |
| `__manifest__.py`, `migrations/19.0.1.40.0/`               | Modified/New | Bump; allow-list union                               |
| MCP + company tests; both `AGENTS.md`                      | Modified     | Goldens, catalog 7, notes                            |

## Risks

| Risk                            | Likelihood | Mitigation                   |
| ------------------------------- | ---------- | ---------------------------- |
| `image/jpg` MIME fail           | High       | Alias to `image/jpeg`        |
| Empty-only seed skips companies | High       | Union-all migrate            |
| Flattened schema vs dump        | Med        | Type-owned fields + goldens  |
| Diff > 400 lines                | Med        | Chained-PR forecast in tasks |

## Rollback Plan

Revert collection to `19.0.1.39.0` and Nebula `AGENTS.md`. Stored new-type rows remain
until operators delete. No MuK rollback.

## Dependencies

Nebula dump goldens (`src/agent/schemas.py`); coordinated Nebula `AGENTS.md` in apply.

## Success Criteria

- [ ] Six dump variants persist; `unsupported` write raises with no writes
- [ ] Decimal strings, nulls, cash without proof, `image/jpg` accepted;
      extra/type-foreign keys rejected
- [ ] Allow-lists union new types; extras kept;
      replay/draft/revalidation/receipts/response unchanged
- [ ] Nebula `AGENTS.md` catalog blocker removed
