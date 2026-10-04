# Proposal: Inline Collection Allocation

## Intent

Nebula sends inline `payments[]` and requires `sheet_id` plus ordered `vouchers[]`. Odoo
allocates by `document_id` list with no get tool.

**User impact:** one MCP confirm creates vouchers+allocation (lazy partner/binding); get
returns `{allocation: null}` when unbound, no open sheet, or no allocation.

## Scope

### In Scope

- Align create to six keys, full output, lazy partner, fail-closed `auto_create_sheet`
- Add `get_collection_allocation` (read; never writes)
- Retire voucher `@mcp_tool` in unit 3; keep `_collection_*` helpers
- Manifest `19.0.1.27.0` (no migrate folder); tests; AGENTS.md

### Out of Scope

- Nebula code (coordinated-deploy risk only)
- SUPERSET amend / second-payment union
- Models, views, schema

## Capabilities

### New Capabilities

None

### Modified Capabilities

- `collection-allocations`: MCP create (payments inline, invoices required, response
  `sheet_id`+`vouchers[]`); Input and sheet gates (partner lazy on this write;
  fail-closed `auto_create_sheet`); Idempotency and amend (`content_hash` includes
  `residual_reason`; replay returns full payload); **ADDED** `get_collection_allocation`
- `collection-connectors`: Write path may create partners and bindings — extend from
  `create_collection_vouchers`-only to include `create_collection_allocation`
- `collection-vouchers`: MCP tool `create_collection_vouchers` → **REMOVED** at work
  unit 3; `_collection_*` helpers remain internal

## Approach

Three chained units: (1) inline payments, full payload, hash+reason, fail-closed sheet
(old tool still exposed); (2) `tools/allocation_lookup.py` read; (3) drop voucher
`@mcp_tool`. One transaction; exact `document_id` reuse continues to allocation. Errors
raised, never error-as-body.

**Assumptions:** SUPERSET amend; six create keys (top-level identification only); valve
`invoices: []` + `on_account`; read never creates partner/sheet.

## Affected Areas

| Area                                              | Impact   | Description                            |
| ------------------------------------------------- | -------- | -------------------------------------- |
| `tools/collection_allocation.py`                  | Modified | Inline payments; full payload          |
| `tools/collection_voucher.py`                     | Modified | Top-level ident; retire tool in unit 3 |
| `tools/allocation_lookup.py`, `tools/__init__.py` | New      | Read mixin + register                  |
| `__manifest__.py`, `AGENTS.md`                    | Modified | `19.0.1.27.0`; MCP bullets             |
| `tests/test_collection_mcp_*.py`                  | Modified | Rewrite write tests; add read          |

## Risks

| Risk                                                         | Likelihood | Mitigation                                     |
| ------------------------------------------------------------ | ---------- | ---------------------------------------------- |
| Unit 3 before Nebula deploy breaks live voucher-tool callers | High       | Units 1–2 ship alone; unit 3 with/after Nebula |
| Exact `document_id` replay skip or unbound read error        | Med        | Continue to allocation; `{allocation: null}`   |
| OpenSpec breakage; >400 LOC                                  | High       | Warn at archive; three chained units           |

## Rollback Plan

Unit 1 revert schema. Unit 2 delete lookup. Unit 3 restore `@mcp_tool`. Manifest
`19.0.1.26.0`. No migrate undo.

## Dependencies

`_collection_*` helpers, `resolve_customer_partner`; Nebula deploy before/with unit 3.

## Success Criteria

- [ ] Create/replay return `sheet_id` + ordered `vouchers[]` + 7-key allocation (int
      `revision`)
- [ ] Unbound write lazy-creates; read unbound/no sheet/no allocation →
      `{allocation: null}`; `auto_create_sheet` False → named error, zero writes
- [ ] Revalidation rolls back vouchers; unit 3 unregisters voucher tool; tests pass; no
      `migrations/19.0.1.27.0/`
