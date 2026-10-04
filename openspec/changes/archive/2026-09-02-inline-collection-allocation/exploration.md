## Exploration: inline-collection-allocation

### Current State

Odoo `create_collection_allocation` (`tools/collection_allocation.py`) is **document_id
allocation**, not Nebula's inline-payment confirm.

| Surface       | Odoo today                                                                                                                                                                         | Nebula already emits / validates                                                                                                                                                                                      |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Create input  | Required `{seller_id, customer_identification, request_id, vouchers}`; `vouchers` = `document_id` strings; `invoices` optional (omit → `[]`)                                       | Always six keys: top-level identification only; `payments[]` (no per-payment customer); `invoices` always present                                                                                                     |
| Create output | `{allocation:{id,name,state,revision,total_vouchers,total_applied,residual}}`                                                                                                      | Requires `sheet_id` + `vouchers[]` in **submit order** (`id,name,state,document_id`) + the same 7-key `allocation` (`revision` must be `int`)                                                                         |
| Partner       | `_collection_allocation_bound_partner` is **binding-only**; unbound → `UserError` (`The requested customer is not available.`); never `resolve_customer_partner`                   | First payment of a new customer has no binding yet; write must lazy-create via voucher helpers                                                                                                                        |
| Read          | **No** `get_collection_allocation` (`tools/__init__.py` lists allocation, voucher, debt, list, seller only)                                                                        | `get_collection_allocation`: `{allocation: null}` or allocation plus **present** `vouchers`/`invoices` lists. Unbound must be `null`, not generic `UserError`. Errors must be raised, never `{"error": "..."}` bodies |
| Replay        | Identical `request_id` returns the thin allocation object; `content_hash` omits `residual_reason`                                                                                  | Replay must rebuild `sheet_id` + ordered `vouchers[]`. Reason-only retry must not be a silent no-op                                                                                                                   |
| Sheet         | Vouchers must already share one open sheet. ORM `_apply_open_sheet_auto_assign` **skips** when `auto_create_sheet` is False (unassigned voucher → misleading "single sheet" error) | Fail-closed named error, zero writes                                                                                                                                                                                  |

`create_collection_vouchers` is still `@mcp_tool`. Helpers to **reuse, not duplicate**:
`_collection_parse_payment_vals` (today reads **per-payment**
`customer_identification`), nest/attachment parsers, `_collection_create_vouchers` (lazy
`resolve_customer_partner` at `:666`), `_collection_vouchers_payload` (submit-order
4-key rows), `_collection_classify_visible` / `_collection_replay_or_reject` /
`_collection_document_conflict_error` / `_collection_require_internal_seller`. Exact
`document_id` set **early-returns** at `_collection_replay_or_reject` (`:603`) — fused
write must **reuse rows and continue** to allocation; partial overlap / other-company
stay generic conflict.

Manifest is `19.0.1.26.0`. Read-tool pattern for the new file: `tools/customer_debt.py`
(`category=read`). Sheet lookup for read: `_open_sheets_for_seller` (never
`_resolve_open_sheet_id_for_create`, which creates).

Nebula `src/agent/tools/collection_allocation.py` (read-only): `_payment_from_draft`
omits customer on payments; `_parse_create_response` rejects missing `sheet_id` or
mismatched voucher `document_id`s
(`"returned a voucher list that does not match the submitted payments"`);
`_parse_get_allocation_payload` accepts `allocation is None`; confirm refuses an
existing allocation (SUPERSET unused by the agent).

### Affected Areas

- `tools/collection_allocation.py` — schema `vouchers`→`payments`, `invoices` required,
  parse inline payments, payload `sheet_id`+`vouchers[]`, `content_hash` includes
  reason, fail-closed `auto_create_sheet`, identity assert after lazy resolve, no extra
  savepoint
- `tools/collection_voucher.py` — drop per-payment customer from payment item +
  `_collection_parse_payment_vals` (top-level ident replicated); keep helpers; retire
  `@mcp_tool` last
- `tools/allocation_lookup.py` — **new** `get_collection_allocation` read mixin;
  register in `tools/__init__.py`
- `__manifest__.py` / `AGENTS.md` — `19.0.1.27.0`; MCP bullets; **no**
  `migrations/19.0.1.27.0/`
- Specs: `openspec/specs/collection-allocations/spec.md` (create + gates + idempotency;
  **ADDED** get); `collection-connectors/spec.md` requirement "Write path may create
  partners and bindings" (today voucher-create only); `collection-vouchers/spec.md`
  requirement "MCP tool create_collection_vouchers" (REMOVED, helpers stay)
- Tests: `tests/test_collection_mcp_allocation.py` (schema freeze `required` includes
  `vouchers`; `_payload` builds document_id lists over pre-created vouchers);
  `tests/test_collection_mcp_tool.py` (`create_collection_vouchers` create/replay/ACL +
  attachment/provenance classes); `tests/test_collection_mcp_partner_resolve.py`
  (`TOOL_NAME = create_collection_vouchers`);
  `tests/test_collection_company_migration.py` `test_manifest_version_is_1_26_0`

### Approaches

No open fork. Source-plan decisions are closed: SUPERSET amend deferred; one Odoo
transaction (revalidation failure rolls back vouchers); `create_collection_vouchers`
`@mcp_tool` retired in work unit 3; helpers stay; errors raised not body-encoded; exact
`document_id` reuse continues into allocation; fail-closed when `auto_create_sheet` is
False; collection-addon scope only.

1. **Closed path (inline payments + new read + retire voucher MCP)** — Match the live
   Nebula contract in Odoo; chain three work units so review stays under ~400 LOC and
   unit 3 can wait for coordinated Nebula deploy.
   - Pros: Agent confirm/get work without a second Odoo round-trip; first-customer write
     creates partner/binding; read null does not break first payment; helpers keep
     idempotency.
   - Cons: Breaking schema vs current OpenSpec; unit 3 is a coordinated-deploy hazard if
     production still calls `create_collection_vouchers`.
   - Effort: High (tests rewritten; three work units)

### Recommendation

Implement the closed path in `collection` only. Work unit 1: inline payments, full
create/replay payload, `content_hash`+reason, auto-sheet fail-closed, voucher-helper
refactor (old tool still exposed). Work unit 2: `get_collection_allocation`
(unbound/`no sheet`/`no allocation` → `{allocation: null}`). Work unit 3: drop voucher
`@mcp_tool`, retarget surviving tests, manifest `19.0.1.27.0` with no new migrate
folder.

### Risks

- **Coordinated deploy:** retiring `create_collection_vouchers` before the production
  agent stops calling it breaks live confirm. Units 1–2 are backward-compatible; unit 3
  must ship with or after Nebula.
- **OpenSpec archive:** `vouchers`→`payments` and voucher-tool removal are
  backward-incompatible spec deltas (`config.yaml` archive rule).
- **Replay trap:** copying voucher early-return would skip allocation; Nebula would
  reject the thin payload.
- **Read vs write partner:** if read raises the generic unbound `UserError`,
  first-customer confirm still breaks even with lazy write.
- **400-line review budget:** plan already exceeds it; chain the three work units.

### Ready for Proposal

Yes. Propose against this contract; do not reopen closed decisions. Nebula stays
read-only context.
