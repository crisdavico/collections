# Design: Customer Partner Binding

## Technical Approach

Lazy find-or-create (D2) on MCP `create_collection_vouchers` only. Keep per-payment
`customer_identification` (D1). Resolve via `resolve_customer_partner` into required
voucher `partner_id` (P3). Read tools create nothing. No sqlite/nebula. Apply root:
collection addon. Reverse write-path partner ban; keep it on list/debt.

## Architecture Decisions

| Decision | Options | Tradeoff | Choice |
|----------|---------|----------|--------|
| Provisioning | Lazy vs Import | Import needs Settings + replace-all | **Lazy** (D2). Reject Import. |
| Partner key | `vat` vs dedicated field vs `ref` | No `l10n_ar`; vat not unique | **`vat`**, exact strip, no CUIT (Q1/D3). `>1` generic miss. |
| MCP schema | String vs `partner_id` | String keeps Nebula identical | **String in** (D1). |
| Privileges | `sudo()` vs ACL create | Addon forbids sudo | **`group_user` 1,0,1,0** (P1); snapshot precedent. Partner create already on `group_user`. |
| Miss lookup | `list_customers` vs debt | Debt pulls invoices | **`list_customers`**. No new `_DISPATCH_OPS`. |
| Partner factory | Duplicate vs rename helper | Raw SQL writes name/email/phone only | **Rename + extend SQL** (P5+Q3). |

`UNIQUE(connector_id, identification)` collapsing two ERP ids that share a VAT is
deliberate. Fast path does not re-check seller. Created partners: `vat=identification`,
`company_id` from connector, `customer_rank=1`, no tag; `customer_code` on binding only
(Q2/Q3).

## Data Flow

Replay classifies **before** resolve. Resolve **inside** the existing voucher savepoint
so a later miss rolls back earlier writes.

```
create_collection_vouchers
  parse strings → classify(document_id)
       │ exact same-company → return {vouchers}  (no resolve)
       ▼ all-new
  parse nests (no writes)
  savepoint
    for each ident: resolve_customer_partner(seller, ident)
      1 _require_customer_identification
      2 _enabled_bound_external_seller_id  (auth before binding probe)
      3 search (connector, identification) → hit: partner
      4 miss: list_customers; exactly one active row else generic
      5 vat==ident: 1 bind / 0 create / >1 generic
      6 nested savepoint: Binding.create; UniqueViolation → invalidate, re-search
    Voucher.create(..., partner_id)
  outer UniqueViolation = document_id only
```

Generic miss: `_("The requested customer is not available.")`. Connector:
`env.company._collection_active_connector()`.

**Nested UniqueViolation:** seller Import has no handler. Outer MCP maps every
`UniqueViolation` to `Payment document_id conflict could not be resolved.` Binding
races MUST use nested `with self.env.cr.savepoint():` around partner+binding insert;
on `UniqueViolation`, invalidate, re-search by identification, use hit, re-raise only
if missing. Binding UNIQUE must not reach the outer handler.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `models/collection_connector_customer_binding.py` | Create | Seller-binding mirror + ident/`customer_code`; three UNIQUE `models.Constraint`; `create()` company-guard |
| `tests/test_collection_customer_binding.py`, `test_collection_customer_resolution.py` | Create | UNIQUE/ACL; gate, vat 1/0/>1, nested race; import in `tests/__init__.py` |
| `models/__init__.py` | Modify | Import between connector and seller binding |
| `models/collection_connector.py` | Modify | `customer_binding_ids`; `resolve_customer_partner` |
| `models/collection_voucher.py` | Modify | Drop Char; add `partner_id` (P3). No review payload |
| `models/res_company.py` | Modify | Rename `_collection_create_seller_partners` → `_collection_create_partners`; **extend** raw-SQL INSERT with `vat`, `company_id`, `customer_rank` (P5+Q3); caller L224 |
| `tools/collection_voucher.py` | Modify | Parallel ident list; resolve in savepoint; exclusion `("document_id",)` |
| `views/collection_views.xml` | Modify | Six nodes → `partner_id`, **no domain** (P2): 22, 47, 107, 116, 164, 490 |
| `views/collection_connector_views.xml` | Modify | Customer Bindings notebook (`group_system` menu) |
| `security/ir.model.access.csv` | Modify | user `1,0,1,0`; system `1,1,1,1` |
| `security/collection_security.xml` | Modify | `ir.rule` `[('company_id', 'in', company_ids)]` |
| `__manifest__.py` + version test | Modify | `19.0.1.24.0`; bump `test_manifest_version_is_1_23_0` |
| ORM/UI tests (~12 helpers) | Modify | P4: `customer=` on `_create_voucher` / `_voucher_vals` / `_create_voucher_in_company` |
| `tests/test_collection_mcp_tool.py` | Modify | Connector fixtures; replay skips resolve |
| `AGENTS.md`, `readme/DESCRIPTION.md` | Modify | Partner in-scope; MCP string I/O unchanged |
| Seller binding; list/debt tools; `common_connector.py`; debt MCP tests; sqlite; nebula-agent | Unchanged | Out of apply root |

## Interfaces / Contracts

Binding: `connector_id` M2O cascade `check_company`; `external_customer_id` Char;
`partner_id` M2O restrict; `identification` Char; optional `customer_code`; related
stored precompute `company_id`. UNIQUEs: `(connector_id, external_customer_id|identification|partner_id)`.
`resolve_customer_partner(seller_id, identification) -> res.partner`; never `sudo()`.
MCP I/O unchanged: string in; `{vouchers:[{id,name,state,document_id}]}` out.

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| TransactionCase | UNIQUE/ACL; resolve; nested race; P4 | New tests + helper rewrite |
| MCP | All-new resolve; batch rollback; replay skip | **Fixtures:** `install_test_connector_type` + company connector + bound seller + listable customer matching the payment string (`collection_test_customers` / `TEST_CUSTOMERS`). Pattern: `test_collection_mcp_customer_list.py`. Else all-new fail-closed |
| UI | Six `partner_id` nodes; no domain | `test_collection_ui.py` |
| E2E | — | N/A |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file
classification, or process-integration boundary.

## Migration / Rollout

No `migrations/` (D4). Devel: no NOT NULL `partner_id`; leftover Char. Accept.
`prod.sql.gz` needs a later backfill. Manifest `19.0.1.24.0`. `auto-chain`: WU4
views+helpers and WU5 MCP fixtures are the 400-line split.

## Open Questions

None. D1–D4, P1–P5, Q1–Q4 locked. Do not restage connector work (Q4).
