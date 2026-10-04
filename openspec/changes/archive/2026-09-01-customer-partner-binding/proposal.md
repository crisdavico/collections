# Proposal: Customer Partner Binding

## Intent

Replace voucher Char `customer_identification` with required `partner_id` (label
Customer) so ERP customers are `res.partner`. MCP `create_collection_vouchers` keeps
per-payment identification strings; the server resolves string → partner (D1). No
nebula-agent change.

## Scope

### In Scope

Customer binding (seller-binding mirror); lazy `resolve_customer_partner` (D2); voucher
`partner_id` (P3: required, tracking, index, restrict); six view swaps, no domain (P2);
MCP same I/O, resolve in voucher savepoint, nested UniqueViolation for bindings; ACL
`group_user` `1,0,1,0`, never `sudo()` (P1), company `ir.rule`; helper `customer=` in
~12 helpers (P4); rename `_collection_create_seller_partners` →
`_collection_create_partners` and extend raw-SQL INSERT with `vat`, `company_id`,
`customer_rank` (P5+Q3 — rename-only is insufficient); manifest `19.0.1.24.0` +
version-test bump; connector Customer Bindings page; spec/docs/AGENTS.md.

### Out of Scope

nebula-agent; `collection_connector_sqlite` adapter/schema; Import Customers UI;
`partner_id` on `list_collection_customers` / `customer_debt` payloads; data migration
(D4); dedicated `collection_identification` (Q1: `vat`); tagging created partners;
`customer_code` on partner (`ref`) — binding only (Q2); restaging uncommitted connector
work (Q4).

## Capabilities

### New Capabilities

None

### Modified Capabilities

- `collection-connectors`: reverse write-path partner prohibition; add customer
  binding + `resolve_customer_partner`; keep read tools from creating partners
- `collection-vouchers`: Char → `partner_id`; MCP string input unchanged; replay still
  ignores changed customer

## Approach

Gate identification, then enabled-bound seller, then binding fast path. Miss:
`list_customers`; D3 vat (exact stripped string, no CUIT normalize): 1 bind, 0 create
(`vat=identification`, `company_id` from connector, `customer_rank=1`, no tag), `>1`
generic error. Replay before resolve. Resolve inside the existing savepoint. Binding
UniqueViolation **must** use a nested savepoint; the voucher outer UniqueViolation path
assumes `document_id` and would mis-report the generic document conflict error. MCP
all-new create tests currently have no connector; they fail closed unless they get
connector + bound seller + listable customer fixtures.
`UNIQUE(connector_id, identification)` collapsing two ERP ids that share a VAT is
deliberate.

## Affected Areas

New: `models/collection_connector_customer_binding.py`. Modified:
`models/collection_connector.py`, `collection_voucher.py`, `res_company.py`;
`tools/collection_voucher.py`; voucher and connector views; `security/*`;
`__manifest__.py`; tests; AGENTS.md / readme.

## Risks

MCP tests fail closed without connector fixtures (High). Binding UniqueViolation
mis-classified as `document_id` without nested savepoint (Med). P5 rename-only drops Q3
columns on raw SQL (Med). D4: existing rows skip NOT NULL `partner_id` (High; accept on
devel). 400-line WU4/WU5 → `auto-chain` (Med).

## Rollback Plan

Module-level: revert this change. D4 means no backfill to undo. Existing voucher rows
will not get NOT NULL `partner_id` (accepted for devel).

## Dependencies

Sit on existing connector work; do not restage (Q4). No new module deps.

## Success Criteria

- [ ] Voucher requires `partner_id`; Char gone; views show Customer
- [ ] MCP I/O unchanged; all-new resolves; replay skips resolution
- [ ] Read tools create nothing; binding UNIQUE + user create-only; never `sudo()`
- [ ] Tests pass with MCP connector fixtures; devel upgrade has no migration
