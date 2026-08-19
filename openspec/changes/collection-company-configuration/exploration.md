## Exploration: collection-company-configuration

CodeGraph MCP/CLI was unavailable (`user-codegraph` missing; `gentle-ai codegraph init` exit 127). Investigation used Read/rg on the collection addon.

### Current State

Collections already uses the decided **one config per company** pattern: `res.company.document_review_enabled` (default OFF) with a related `res.config.settings` field, Collections `<app name="collections">`, and menu/action XMLID `collection.action_collection_config_settings` whose **label is "Settings"** (`models/res_company.py`, `models/res_config_settings.py`, `views/res_config_settings_views.xml`). Tests lock that label and the flag-only settings arch (`tests/test_collection_ui.py`, `tests/test_collection_document_review_flag.py`). Document Review RPCs gate on `env.company._document_review_enabled()` (`models/collection_voucher.py`).

`collection.voucher` and `collection.sheet` have **no `company_id`**. Sequences `collection.voucher` (`COL/%(year)s/`) and `collection.sheet` (`CS/%(year)s/`) are **global** (`company_id` False in `data/ir_sequence_data.xml`). Create uses `ir.sequence.next_by_code` without `with_company`.

Seller: voucher `seller_id` is **ORM-optional** (UI form `required="1"`); sheet `seller_id` is required. MCP `create_collection_vouchers` already requires an internal `seller_id` (`tools/collection_voucher.py` `_collection_require_internal_seller`) and stamps it only on all-new create. Exact replay ignores seller and returns `{id,name,state,document_id}`. There is **no enabled-seller allow-list**.

Document type is a **Selection** on the voucher (`bank_transfer`, `check`, `cash_deposit`, `unsupported`) with no per-company allow-list. MCP `_DOCUMENT_TYPES` is the same four keys.

One-open is **per seller only**: `_open_sheets_for_seller` / advisory lock `hashtext('collection.sheet.open') + seller_id` (`models/collection_sheet.py`). Auto-assign on voucher create always runs when `seller_id` is set and `sheet_id` omitted (0 open → create sheet; 1 → assign; >1 → `UserError`). There is **no `auto_create_sheet` flag**.

`document_id` uniqueness is already **global** (`UNIQUE(document_id)` allowing multiple NULLs). MCP idempotency searches all vouchers by `document_id` with **no company filter**, so a hit in any company is treated as exact replay.

MCP `get_seller_id` (`tools/seller_lookup.py`) matches **any internal user** by normalized `phone`, then the same internal-seller bar. It does **not** filter by company or enabled sellers.

Security: ACL only (`security/ir.model.access.csv`). **No `ir.rule`**. Specs and tests assert that (`openspec/specs/collection-vouchers/spec.md`, `collection-sheets/spec.md`, `tests/test_collection_acl.py`). AGENTS.md still says “no extra groups or record rules.”

Main-spec gaps vs this change: voucher seller MAY be null on ORM create; auto-assign always on; one-open per seller not per company+seller; no company ownership; MCP replay is global; document-review spec only covers the existing flag (no-regression boundary).

### Affected Areas

- `models/res_company.py` / `models/res_config_settings.py` / `views/res_config_settings_views.xml` — new per-company fields; rename action/menu **labels** to Collection Settings; keep XMLID `collection.action_collection_config_settings`.
- `models/collection_voucher.py` / `models/collection_sheet.py` — required `company_id`; seller required on new create; enabled-seller + allowed-type + `auto_create_sheet` gates; one-open scoped by company+seller; `with_company` sequences.
- `tools/collection_voucher.py` — enabled seller on all-new create; allowed `document_type`; cross-company `document_id` reject (no replay, no disclosure); exact same-company replay unchanged.
- `tools/seller_lookup.py` — current behavior only; later enabled-seller filter is **out of this change / no Nebula work**.
- `data/ir_sequence_data.xml` plus company create/upgrade — per-company sequences.
- `security/` — new `ir.rule` XML (standard allowed-company); load before/with ACL in `__manifest__.py`.
- `migrations/` — stamp `company_id`; seed `enabled_seller_ids`; seed allowed types; convert/copy sequences.
- Views (`views/collection_views.xml`) — seller/type domains; optional `company_id` column for multi-company.
- Tests: `test_collection_ui.py` (Settings labels), `test_collection_voucher.py` (nullable seller), `test_collection_sheet.py` (one-open/auto-assign), `test_collection_acl.py` (no-rule assertions), `test_collection_mcp_tool.py` (replay/seller), `test_collection_payment.py` (global unique), `test_collection_document_review_flag.py` (preserve flag).
- Main specs: `collection-vouchers`, `collection-sheets`, `seller-lookup` (note-only), `document-review` (no-regression).
- `AGENTS.md` — ACL/one-open/sequence/seller rules will be stale after apply.

### Approaches

1. **`res.company` + related `res.config.settings` (decided)** — persist `enabled_seller_ids`, `auto_create_sheet` (default True), `allowed_document_type_ids`, keep `document_review_enabled` on `res.company`; expose via related settings fields on the existing Collections app.
   - Pros: matches current Document Review pattern and tests; exactly one config per company; Settings admins already gated by `base.group_system`.
   - Cons: `res.company` grows; Many2many defaults need install/upgrade seeding.
   - Effort: Medium

2. **POS-style multi-record config model** — e.g. `collection.config` with `company_id` unique.
   - Pros: isolates collection fields from `res.company`.
   - Cons: **rejected**; extra model/UI; duplicates Settings; not “exactly one config per company” in the existing pattern.
   - Effort: High

Open implementation details (config approach stays):

3. **Allowed types storage**
   - **3a. Catalog model + Many2many on company (recommended)** — tiny `collection.document.type` with four XMLID rows; voucher `document_type` stays Selection; create/MCP/UI validate against company M2M. Matches `allowed_document_type_ids`; Unsupported stays configurable; all four seeded.
   - **3b. Four booleans on company** — simpler DDL, fights the decided field name and Settings UX.
   - **3c. Change voucher `document_type` to Many2one** — breaks MCP enum, snapshots, OWL review. Too wide.

4. **Per-company sequences (Odoo 19)** — `ir.sequence.next_by_code` searches `company_id in [env.company.id, False]` and uses `seq_ids[0]` (`odoo/addons/base/models/ir_sequence.py`). Create one sequence row **per company** with the same codes; call `with_company(record.company_id).next_by_code(...)`. On upgrade: retarget the existing `company_id=False` rows to the main company (keep `number_next`) and copy for other companies; create sequences when a company is created. Do not leave a company-less row competing if numbering must stay isolated.

5. **Upgrade seed for `enabled_seller_ids`** — after stamping `company_id` on vouchers/sheets, set each company’s M2M to distinct `seller_id` used on that company’s vouchers **and** sheets. Stamp rule: seller’s `company_id` when set, else the database main/`env.company` (covers null-seller legacy vouchers). Empty list means none for **new** work.

### Recommendation

Implement the **already decided** `res.company` + `res.config.settings` pattern (approach 1). Keep voucher/sheet Selection `document_type`; store allow-list as catalog Many2many (3a). Add required `company_id` (default `env.company`) plus global `ir.rule` `[('company_id', 'in', company_ids)]` on vouchers and sheets (no extra groups). Scope one-open and the advisory lock to `(company_id, seller_id)`. Make seller required on **new** voucher create (ORM/import/MCP/UI); do not backfill or hide legacy null/disabled-seller rows. Gate new create (and `seller_id` / `document_type` writes) on enabled sellers and allowed types; skip those gates on exact MCP replay.

When `auto_create_sheet` is on, keep today’s auto-assign. When off, skip automatic create **and** assign; list Action and explicit sheet create remain. Keep `UNIQUE(document_id)` global. MCP: same-company exact set still replays; other-company hit or UniqueViolation with no visible row → generic `UserError`, no ids/names. Do not `sudo()`. Preserve `document_review_enabled` and review RPC behavior. Rename action and `menu_collection_settings` **names** to “Collection Settings”; do not change the XMLID or numeric `action-540`. Leave `get_seller_id` unfiltered in this change (report-only: it would later need current-company enabled-seller filtering; no Nebula-agent work).

### Risks

- Specs/tests currently **require** nullable ORM seller, always-on auto-assign, one-open per seller, and **zero record rules** — all must be delta-updated or apply will fail TDD.
- Cross-company `document_id` plus record rules: naive UniqueViolation → `search` → “could not be resolved” must not become a side channel; use one generic reject. Multi-company users who can **read** both companies must still not **replay** the other company’s voucher.
- Review snapshots have no `company_id`/`ir.rule`; voucher rules do not hide snapshot rows. Recommend related stored `company_id` + the same company rule (still no extra groups).
- Sequence migration: leaving `company_id=False` rows can steal `next_by_code` depending on NULL sort; convert/copy explicitly.
- Large test churn (voucher creates without seller, ACL no-rule asserts, Settings “Settings” labels) — likely above the 400-line review budget; plan chained PRs later.
- Empty `enabled_seller_ids` blocks all new collection work for that company after upgrade if the company had no used sellers.

### Ready for Proposal

Yes. Product decisions are settled; remaining work is spec/design of the `res.company` settings fields, company-owned records, per-company sequences, MCP collision semantics, and migration seeding. Orchestrator should run `sdd-propose` next. Out of scope: proof requirement, review threshold, collection kill switch, accounting/journals, HTTP API, Nebula-agent, POS-style config, renaming numeric `action-540`.
