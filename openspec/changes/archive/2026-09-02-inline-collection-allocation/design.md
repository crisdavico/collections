# Design: Inline Collection Allocation

## Technical Approach

Fuse voucher create into `create_collection_allocation` (one request →
`{sheet_id, vouchers[], allocation}`). Reuse `_collection_*` helpers. Exact
`document_id` reuse continues to allocation. Add get tool; retire voucher
`@mcp_tool` in unit 3. No model/view/ACL/`migrations/19.0.1.27.0/`. Raise
errors; never `{"error":...}`.

## Architecture Decisions

| Option | Tradeoff | Decision |
| --- | --- | --- |
| Extra savepoint on fused write | Isolates vouchers from revalidation | **None.** Request txn rolls back on revalidation `UserError`. Keep nested binding savepoints. |
| `_collection_replay_or_reject` on exact set | Thin payload; Nebula rejects | **Classify then continue.** `_collection_classify_visible`: `None`→create; raise→stop; dict→keep recordset. |
| Binding-only partner on write | First-customer confirm dies | **Lazy resolve via `_collection_create_vouchers`.** Bound-partner is identity assert; connector from `company._collection_active_connector()`. |
| Read via `_resolve_open_sheet_id_for_create` | Creates a sheet | **`Sheet._open_sheets_for_seller`.** Unbound / no sheet / no allocation → `{allocation: null}`. |
| Hash omits `residual_reason` | Silent no-op | **Include `residual_reason`.** SUPERSET kept. |

## Data Flow

```
CREATE  parse → seller → request_id hit?
          yes → payload(sheet_id, ordered vouchers[], 7-key allocation)
          no  → _assert_new_work(seller.id) → auto_create_sheet?
                  off → named UserError, 0 writes
                  on  → classify document_ids
                        all-new → nests + _collection_create_vouchers
                        exact   → reuse rows (do not return)
                        else    → generic conflict, 0 writes
                      → voucher-set gates → identity assert → lock
                      → hash(+reason) → ERP revalidate → residual → persist
GET     internal + enabled bound seller → _open_sheets_for_seller
          0 open / no binding / no allocation → {allocation: null}
          >1 open → UserError (multi-open msgid)
          hit → allocation(+residual_reason), vouchers, invoices
```

## File Changes

Untouched helpers: `_collection_parse_payment_attachments`,
`_collection_parse_payment_provenance`, `_collection_parse_provenance_nests`,
`_collection_parse_attachment_nest`, `_collection_create_vouchers`,
`_collection_vouchers_payload`, `_collection_classify_visible`,
`_collection_replay_or_reject`, `_collection_replay_existing`,
`_collection_document_conflict_error`, `_collection_require_internal_seller`.

| File | Action | Description |
| --- | --- | --- |
| `tools/collection_voucher.py` | Modify | Extract `_PAYMENT_SCHEMA`; drop `customer_identification`. `_collection_parse_payment_vals(payments, identification)` replicates ident. Unit 1: keep `@mcp_tool`; overlay per-payment idents. Unit 3: delete decorated method + schema. |
| `tools/collection_allocation.py` | Modify | Schema `vouchers`→`payments` (`minItems` 1, items=`_PAYMENT_SCHEMA`); `invoices` required; required set `{seller_id, customer_identification, request_id, payments, invoices}`. Parse via `_collection_parse_payment_vals` + nest parsers; reject duplicate `document_id`. Fail-closed `auto_create_sheet` named error, 0 writes. Payload `sheet_id` + `vouchers[]` via `_collection_vouchers_payload`. Replay from submitted `document_ids`. Hash includes reason. Keep all voucher-set gates. |
| `tools/allocation_lookup.py` | Create | Pattern `customer_debt.py`. `@mcp_tool(name="get_collection_allocation", category="read", registry="mcp")`. Zero writes. |
| `tools/__init__.py` | Modify | `from . import allocation_lookup`. |
| `__manifest__.py` | Modify | `19.0.1.27.0` (unit 3). |
| `AGENTS.md` | Modify | MCP bullets + 1.27.0. |
| `tests/test_collection_mcp_*.py` | Modify/Create | See Testing Strategy: rewrite allocation `_payload`; new `test_collection_mcp_allocation_lookup.py`; unit 3 retargets + `test_manifest_version_is_1_27_0`. |

```python
existing = self._collection_vouchers_by_document_ids(document_ids)
classified = self._collection_classify_visible(existing, document_ids)
if classified is None:
    self._collection_create_vouchers(...)
# exact set: keep existing, continue
```

## Interfaces / Contracts

**Create in:** `seller_id`, top-level `customer_identification`, `request_id`,
`payments[]` min 1, `invoices[]` (may be `[]`), optional ignored `total_debt`,
`residual_reason`. **Out:** `{sheet_id, vouchers:[{id,name,state,document_id}
submit order], allocation:{id,name,state,revision:int,total_vouchers,total_applied,residual}}`.

**Get in:** `{seller_id, customer_identification}`. **Out:** `{allocation: null}`
or `{allocation:{... + residual_reason}, vouchers:[{id,name,state,document_id,amount,document_type}], invoices:[...]}`.

`category="read"` required. Never `sudo()`. Never change `_DISPATCH_OPS`.
Fail-closed msgid: `"This company requires a collection sheet chosen in Odoo."`

## Testing Strategy

`TransactionCase` + fixtures/`tool_model._call`/`_LEAK_TOKENS`/no-sudo.
Strict TDD: RED before GREEN per unit. `invoke test -m collection --mode=update`.

**Rewrite:** `test_collection_mcp_allocation.py` (22 tests; `_payload` used
`vouchers`; discovery `required` includes `vouchers`) → inline `payments`, new
required set.

**Rewrite unit 3:** `test_collection_mcp_tool.py` delete create/replay/ACL;
retarget `TestCollectionMcpAttachment`/`TestCollectionMcpProvenance`.
`test_collection_mcp_partner_resolve.py` retarget. Manifest `1_27_0`; no
migrate folder.

**New write RED (unit 1):** inline create+rev 1; `sheet_id`+ordered
`vouchers[]`; `request_id` replay full payload 0 writes; exact `document_id`
reuse continues to allocation; partial/other-company generic conflict;
`auto_create_sheet` off named error 0 writes; `invoices:[]`+reason on-account;
residual missing reason / negative fail; hash includes reason; SUPERSET
required; validated/rejected refuse amend; revalidation rolls back vouchers
(counts equal); lazy partner+binding; disallowed type via `_assert_new_work`;
leak + no-sudo; anti-drift freeze `{sheet_id,vouchers,allocation}` / 7 alloc
keys / 4 voucher keys.

**New read RED (unit 2):** discovery `category=read`/`registry=mcp`/
`kind=method`/no DB row/`required`; auth AccessError/share/not enabled; no
open sheet → null; **unbound → null, no partner/binding created**; sheet
without allocation → null; confirmed has vouchers+invoices; validated
returned; >1 open `UserError`; read does not create sheet; never
attachment/datas/base64; no-sudo.

**Unit 3 RED:** registry absence of `create_collection_vouchers`.

## Work Units

| # | Slice | Rollback |
| --- | --- | --- |
| 1 | Inline payments + helper refactor; `create_collection_vouchers` **still exposed**; write tests | Revert schema/payload; old tool unmoved |
| 2 | `get_collection_allocation` + register + read tests | Delete lookup, unregister |
| 3 | Retire `@mcp_tool`; migrate/delete MCP tests; registry absence; `AGENTS.md`; manifest `19.0.1.27.0` | Restore decorator. Coordinated Nebula deploy. |

400-line risk: High — chain these three slices.

## Threat Matrix

N/A — MCP JSON tools on `muk_mcp.mixin`. No routing, shell, subprocess,
VCS/PR automation, executable-file classification, or process-integration
boundary.

## Migration / Rollout

No stored-field migration and no `migrations/19.0.1.27.0/`.

## Open Questions

None.