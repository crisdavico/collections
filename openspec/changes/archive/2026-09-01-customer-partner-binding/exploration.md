# Exploration: customer-partner-binding

CodeGraph: initialized with `gentle-ai codegraph init --cwd` on the collection addon,
then `codegraph_explore` for voucher/MCP/connector/seller-binding/partner-create
symbols. XML/CSV/tests/sqlite used Read + `rg` (CodeGraph is Python-centric). Engram
unavailable; OpenSpec file write is the persistence.

Settled product decisions (D1–D4, P1–P5, Q1–Q4) are treated as locked. This document
checks them against **current working-tree code**, including uncommitted connector work
(do not stage that work for this change — Q4).

## Exploration: Replace `customer_identification` with `res.partner` + ERP binding

### Current State

`collection` is at **19.0.1.23.0**. Connector/seller-binding/customer-list/debt code is
already in the working tree (mostly untracked or uncommitted). Vouchers still store a
free-text customer.

- **Voucher field.** `models/collection_voucher.py:26-29`:
  `customer_identification = fields.Char(required=True, tracking=True)`. No `string=`,
  no `index=True` (company and `document_id` are indexed; this Char is not).
- **Views.** Six `customer_identification` nodes in `views/collection_views.xml`: list
  22, search 47, kanban field 107, kanban card 116, form 164, sheet voucher list 490.
  Seller fields have an enabled-seller domain; the customer Char has **no domain**.
- **Review payload.** `_review_queue_payload` (voucher.py:637) does **not** include
  customer. `_REVIEW_EDITABLE_FIELDS` is payment-type fields only. Plan is correct: no
  review-payload change.
- **MCP create.** `tools/collection_voucher.py`:
  - Schema still requires per-payment `customer_identification` string (items `required`
    at 235–239). Top-level customer is not a method argument. Output is
    `{vouchers:[{id,name,state,document_id}]}` — no customer field.
  - `_collection_parse_payment_vals` (305) puts the stripped string **into voucher
    vals**. Provenance compare excludes `("document_id", "customer_identification")`
    (423–426). Replay comments (256–258, 607–608) already ignore a changed customer.
  - Classify/replay runs **before** nests and before `_collection_create_vouchers`.
  - Writes sit in `with self.env.cr.savepoint():` (659) then `Voucher.create` + optional
    `message_post`. Outer `except UniqueViolation` (295) assumes
    **`UNIQUE(document_id)`**, invalidates, and classifies; otherwise raises
    `Payment document_id conflict could not be resolved.`
- **Connector.** Untracked `models/collection_connector.py`: `_DISPATCH_OPS` =
  `{test_connection, list_sellers, list_customers, get_customer_debt}`.
  `list_customers(seller_id)` already gates via `_enabled_bound_external_seller_id` then
  dispatches. `get_customer_debt` calls `_require_customer_identification` **then** the
  same seller gate. Generic miss message:
  `_("The requested customer is not available.")`.
- **Seller binding pattern.** Untracked `models/collection_connector_seller_binding.py`:
  M2O connector (`cascade`, `check_company`), Char external id, M2O `res.users`
  (`restrict`), related stored `company_id` (`precompute`). `models.Constraint` UNIQUE
  on `(connector_id, external_seller_id)` and `(connector_id, user_id)`. `create()`
  rejects company ≠ connector company **only when both ids are in vals**.
- **Seller match/create.** `res.company._collection_resolve_connector_sellers`: existing
  binding → unique phone match → else create. `>1` phone match:
  `_("Multiple Odoo users share the same seller phone.")` (not the generic seller
  message). Import is `group_system`; **no UniqueViolation handler** on binding insert.
- **Autopost workaround.** `_collection_create_seller_partners` (res_company.py:250):
  one caller at 224; **zero tests reference the name**. Three paths: field in registry →
  `Partner.create`; column absent → `Partner.create`; column present but field missing →
  **raw SQL INSERT of `name, email, phone` only**.
- **ACL.** Seller binding: `group_user` `1,0,0,0`; `group_system` `1,1,1,1`. Snapshot
  precedent for lazy create: `1,0,1,0`. Connector menu is `groups="base.group_system"`.
  Global `ir.rule` `[('company_id', 'in', company_ids)]` on voucher, sheet, snapshot,
  connector, seller binding. Never `sudo()`.
- **Specs.** `openspec/specs/collection-connectors/spec.md` purpose + three requirements
  (`Normalized customer list output`, `Read-only MCP tool list_collection_customers`,
  `Read-only MCP tool customer_debt` / normalized debt) say the system MUST NOT create
  `res.partner` or customer bindings. `openspec/specs/collection-vouchers/spec.md`
  requires Char `customer_identification` on the voucher and on each MCP payment; replay
  ignores a changed customer; stamps stored first-call values.
- **SQLite adapter.** `collection_connector_sqlite` already implements
  `_sqlite_list_customers` and `_sqlite_get_customer_debt`. No new dispatch op is
  required if resolution reuses `list_customers`.
- **Test helpers (P4).** Twelve helpers, not ~280 raw dicts: `_create_voucher` in
  voucher (3 classes), sheet, mail, company_migration; `_voucher_vals` in acl, payment
  (2 classes), document_review, voucher; `_create_voucher_in_company` in mcp_tool.
  Occurrence counts match the plan table (mcp_tool 88, document_review 55, sheet 42,
  voucher 42, …). `customer_debt` 14 and `common_connector.py` 2 are connector
  identification strings — leave them.
- **MCP tests vs connector.** `tests/test_collection_mcp_tool.py` has **zero** connector
  / `install_test_connector_type` usage. Creates succeed with a free-text customer and
  an enabled seller only. `common_connector.py` test provider already supports
  `collection_test_customers` context and identifications like `20-11111111-1`.
- **Uncommitted tree (Q4).** Connector model, seller binding, connector views, MCP
  list/debt tools, connector specs, and related tests are untracked or mixed into
  modified files (`res_company.py`, ACL, manifest, AGENTS.md). This change must sit on
  top; do not restage that work.

### Affected Areas

- `models/collection_voucher.py` — drop Char; add `partner_id` (P3).
- `models/collection_connector.py` — `customer_binding_ids` O2M;
  `resolve_customer_partner`.
- **New** `models/collection_connector_customer_binding.py` — mirror seller binding
  - `identification` / `customer_code` + three UNIQUE constraints.
- `models/__init__.py` — import (alphabetically between connector and seller binding).
- `models/res_company.py` — P5 rename; **extend** the raw-SQL fallback (see approaches).
- `tools/collection_voucher.py` — parallel identification list; resolve **inside** the
  existing savepoint; nested UniqueViolation for binding races; provenance exclusion
  becomes `("document_id",)`.
- `views/collection_views.xml` — six field swaps; **no** partner domain (P2).
- `views/collection_connector_views.xml` — currently a flat form with **no**
  seller-binding notebook. Adding a Customer Bindings page is new UI (connector menu is
  already `group_system`).
- `security/ir.model.access.csv` — user `1,0,1,0` (P1); system `1,1,1,1`.
- `security/collection_security.xml` — company `ir.rule` on the new model.
- `__manifest__.py` `19.0.1.23.0` → `19.0.1.24.0` plus
  `tests/test_collection_company_migration.py` `test_manifest_version_is_1_23_0` (plan
  omitted this test).
- Tests: new binding/resolution files; helper `customer=` (P4); MCP create tests **must
  gain connector + bound seller + listable customers** (plan understated).
- Specs: reverse the no-partner prohibition for the **write/lazy** path only; keep it on
  `list_collection_customers` / `customer_debt`. Voucher spec: required `partner_id`,
  MCP input string unchanged, stored customer is the partner.
- `AGENTS.md` currently lists partner/CRM linkage as out of scope — rewrite that
  sentence. `openspec/config.yaml` still says coordinated Nebula work is in-scope; **D1
  overrides** for this change (no nebula-agent edit).
- **Not affected:** `collection_connector_sqlite` adapter; nebula-agent; seller binding
  model; read-tool payloads.

### Approaches

1. **Plan as written (lazy find-or-create + seller-binding mirror)** — MCP keeps the
   identification string (D1). Miss path: gate → binding by identification →
   `list_customers` → D3 vat match (1 bind / 0 create / >1 generic fail) → create
   binding. Resolve inside the voucher savepoint; nested savepoint on binding
   UniqueViolation. ORM/UI picks `partner_id` with no domain (P2).

   - Pros: Matches locked decisions; zero sqlite/nebula contract change; binding fast
     path skips the adapter; nested savepoint avoids mis-classifying a binding race as a
     `document_id` conflict; P4 keeps helper churn reviewable.
   - Cons: First MCP sighting lists all seller customers; lazy partners land in the
     global `res.partner` list; `UNIQUE(connector_id, identification)` collapses two ERP
     ids that share a VAT; MCP tests need connector fixtures they do not have today.
   - Effort: Medium (WU4/WU5 still the bulk; WU5 larger than the plan's “assertions move
     to `partner_id`”).

2. **Miss path via existing `get_customer_debt` instead of `list_customers`** — Same
   binding model; lookup one identification through the already-dispatched debt op
   (sqlite already filters `seller_id + identification`).

   - Pros: Also zero adapter change; one-row lookup; fail-closed already generic.
   - Cons: Pulls invoices on a write path; diverges from the locked plan; slightly odd
     semantically.
   - Effort: Medium (same binding/voucher work).

3. **Eager Import Customers (rejected by D2)** — Mirror seller Import.
   - Pros: Roster for a UI domain; `group_system` create ACL like seller bindings.
   - Cons: Reopens D2; needs Settings button and replace-all semantics; larger scope.
   - Effort: High.

### Recommendation

**Approach 1 — the source plan**, with these code-backed corrections for design (do not
reopen D1–D4 / P1–P5 / Q1–Q4):

1. **Recommend the plan.** Seller-binding field/constraint/`create()`-guard pattern is
   the right mirror. Reusing `list_customers` means **no sqlite adapter change**. MCP
   input/output stay byte-identical (D1). Read tools stay create-nothing.
   Replay-before-resolve is already the create-path shape. Nested binding
   UniqueViolation is necessary: seller Import has **no** such handler, and the voucher
   outer `except UniqueViolation` would otherwise surface a document_id conflict.

2. **P5 is not a drop-in for Q3.** Rename is safe (one caller, no tests). The raw-SQL
   fallback **must be extended** to persist `vat`, `company_id`, and `customer_rank`
   (and any other lazy defaults). Today's INSERT only writes name/email/phone. ORM
   `Partner.create` paths already accept extra keys.

3. **P4 helper count is real (~12 defs), but MCP tests are not helper-only.** ORM tests
   can resolve `customer=` to a dummy partner without the connector.
   `test_collection_mcp_tool.py` will fail closed unless each all-new create has: test
   connector type installed, company connector set, seller **bound**, and a
   `list_customers` row whose `identification` matches the payment string (use
   `collection_test_customers` context, already in `common_connector.py`). Replay tests
   must still skip resolution.

4. **Connector form has no binding notebook today.** A Customer Bindings page is
   additive; seller bindings are also absent from that form. Connector UI is
   `group_system`, so “read-only for `group_user`” is ACL-true but the menu never opens
   for them.

5. **VAT match is exact stripped string**, unlike seller-phone
   `_collection_normalize_ar_mobile`. Q1 locks `res.partner.vat`. Duplicate or
   differently formatted VATs fail closed (D3) — document that; do not add CUIT
   normalization in this slice.

6. **OpenSpec folder.** Plan named
   `openspec/changes/2026-09-01-customer-partner-binding/`. Active convention is the
   undated folder already created: `openspec/changes/customer-partner-binding/`.

7. **Version test.** Bump `test_manifest_version_is_1_23_0` in the same change as the
   manifest.

8. **Spec rewrite scope.** Keep “MUST NOT create partners/bindings” on the two **read**
   tools. Purpose paragraph and write-path voucher requirements must allow lazy create.
   Do not claim mail tests already assert customer tracking — they use the Char as a
   unique label; `tracking=True` on `partner_id` is still correct (P3).

### Risks

- **MCP test blast radius.** All-new `create_collection_vouchers` tests currently have
  no connector. Without fixtures, resolution raises the generic customer error and WU5
  explodes. Mitigate with a shared MCP+connector setup helper (pattern:
  `test_collection_mcp_customer_list.py`).
- **Binding UniqueViolation vs voucher UniqueViolation.** Without a nested savepoint, a
  first-sighting race is reported as
  `Payment document_id conflict could not be resolved.` Plan §5.4 is correct.
- **Autopost raw SQL dropping Q3 fields** if P5 is a rename-only.
- **Upgrade without backfill (D4).** Required `partner_id` on a DB that already has
  vouchers: Odoo cannot set NOT NULL; leftover Char column. Acceptable on devel;
  `prod.sql.gz` would need a migration (out of this slice).
- **`UNIQUE(connector_id, identification)`** plus D3 vat collapse: two ERP customers
  with the same identification share one partner. Fast path never re-checks seller.
  Deliberate; document in the voucher/connector specs.
- **No VAT uniqueness in Odoo.** `>1` match fails closed (D3) instead of binding the
  wrong partner.
- **Lazy partners are globally visible** (no extra category/tag — Q3).
- **400-line budget.** WU4 (views + helper migration) plus WU5 (MCP fixture setup) are
  the likely split points. `delivery_strategy` is `auto-chain`.
- **Working tree.** Connector work is already dirty/untracked. This change must not
  restage it (Q4).

### Ready for Proposal

**Yes.** Tell the user the plan matches current code and should proceed, with the
corrections above folded into proposal/design (P5 SQL columns, MCP connector fixtures,
undated OpenSpec folder, version-test bump). Do not reopen D1–D4, P1–P5, or Q1–Q4. Next
phase: `sdd-propose`.
