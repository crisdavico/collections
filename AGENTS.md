# AGENTS.md — collection

Agent operating manual for the **Collections** Odoo addon. Human docs:
[README.md](README.md). Parent Doodba context:
[seedian/AGENTS.md](../../../../../AGENTS.md).

Ground truth order: source under this directory →
`openspec/specs/collection-vouchers/spec.md` → this file → parent AGENTS.md.

## Project overview

- **What:** Manual payment vouchers for company sellers (cobranzas).
- **Stack:** Odoo 19, PostgreSQL 17, Doodba (`seedian` compose project).
- **Models:** `collection.voucher` (standalone per payment; required `partner_id`);
  `collection.sheet` (`open`/`submitted`/`proposal`/`closed`/`cancelled` grouping per
  seller; chatter + activities); `collection.allocation` (one per
  `(sheet_id, partner_id)`; `draft` / `confirmed`; chatter + activities) plus
  `collection.allocation.line` and immutable `collection.allocation.revision`;
  `collection.connector` (company-scoped seller source);
  `collection.connector.seller.binding` (1:1 external seller ↔ `res.users`);
  `collection.connector.customer.binding` (1:1 external customer ↔ `res.partner`).
- **Integrations:** `mail.thread` / activities on vouchers and sheets; MuK MCP tools on
  `muk_mcp.mixin`: write `create_collection_allocation` plus `close_collection_sheet`
  plus `declare_collection_cash` plus `create_seller_deposit`; read `get_seller_id` plus
  `list_collection_customers` plus `customer_debt` plus `get_collection_allocation` plus
  `get_collection_sheet_pdf`. Coordinated Nebula first-party tool
  `register_latest_collection_voucher` lives in
  `/home/crisd/projects/nebula/nebula-agent`.
- **Attachments (in scope):** each `collection.voucher` MAY have one optional image or
  PDF designated proof (`message_main_attachment_id` via chatter / `ir.attachment`).
  There is no Binary `attachment` field.
- **Partner / CRM (in scope for vouchers):** required `partner_id` (`res.partner`); lazy
  resolve on MCP `create_collection_allocation` only via
  `collection.connector.customer.binding`. Read tools MUST NOT create partners.
- **Out of scope (do not invent):** WhatsApp connector inside this addon (MCP `mobile`
  argument **is allowed**), HTTP public API, multi-file or non-image/non-PDF
  attachments, multi-currency UX, agent LLM code inside this addon.

## Skills to load before work

1. Read `.atl/skill-registry.md` and match the task.
2. Always load **`odoo-19`** for Python/XML/security/migration/test work:
   `/home/crisd/projects/seedian/seedian/.agents/skills/odoo-19/SKILL.md`
3. Pick the matching guide under `.agents/skills/odoo-19/references/` (model, view,
   security, testing, transaction, migration, etc.).
4. For reviewable commits / stacked PRs, load `work-unit-commits` / `chained-pr` from
   the registry when relevant.

## Setup commands

Run from the **Seedian repo root** (`seedian/`), not from this submodule alone:

```bash
invoke start
invoke install -m collection
invoke install -m collection -d devel   # explicit DB
```

Upgrade after editing this addon:

```bash
docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init
# or: invoke install -m collection
```

## Development workflow

1. Keep edits **inside** `odoo/custom/src/private/collection/` unless `repos.yaml` /
   `addons.yaml` / Doodba deps must change.
2. Prefer OpenSpec change flow when altering behavior (`openspec/config.yaml`:
   `strict_tdd: true`).
3. After model/view/security/data changes: upgrade the module, then run tests.
4. Do not hand-edit generated `README.rst`; update `readme/` fragments and regenerate
   via OCA hooks / pre-commit when needed.
5. This directory is its own git repo (submodule-style). Commits here are separate from
   the parent Doodba tree unless the user says otherwise.

## Repository map

| Path                                              | Role                                                                                                                                                           |
| ------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `__manifest__.py`                                 | Module metadata `19.0.1.47.0`; depends `base`, `mail`, `muk_mcp`, `web`                                                                                        |
| `models/res_company.py`                           | Collection Settings fields + `_assert_new_work`; Import sync; seq copy; type seed                                                                              |
| `models/res_config_settings.py`                   | Related writable Collection Settings + Import action                                                                                                           |
| `models/collection_connector.py`                  | Company-scoped connector + `_dispatch` allowlist (`list_customers`, `get_customer_debt`, `create_receipt`)                                                     |
| `models/collection_connector_seller_binding.py`   | 1:1 external seller ↔ `res.users`; UNIQUE + related stored `company_id`; stores `commission_percent`; Import overwrite                                         |
| `models/collection_connector_customer_binding.py` | 1:1 external customer ↔ `res.partner`; UNIQUE + related stored `company_id`                                                                                    |
| `models/collection_document_type.py`              | Catalog `code`/`name`; `UNIQUE(code)` Constraint                                                                                                               |
| `models/collection_voucher.py`                    | Voucher model, sequence on create, Validate by Seller, draft-only unlink, provenance copies, `retention_kind`, `allocation_id`; freeze non-open writes         |
| `models/collection_voucher_review_snapshot.py`    | Immutable Document Review snapshots (`UNIQUE(voucher_id, revision)`); eight-type Selection + `retention_kind`                                                  |
| `models/collection_sheet.py`                      | Sheet model, `open`/`submitted`/`proposal`/`closed`/`cancelled`, Confirm/Close/Cancel/Open; one-open; freeze; cascade open unlink                              |
| `models/collection_sheet_report.py`               | Second `_inherit`: recon fields, `_collection_report_data()`, `action_print_xlsx`; freeze Closed+Cancelled; Rendida label                                      |
| `models/collection_allocation.py`                 | Allocation header; UNIQUE(sheet, partner); draft iff Open/Proposal/Cancelled; freeze when sheet Closed/Cancelled; Add Debt picker                              |
| `wizard/collection_allocation_debt_picker.py`     | Transient Add Debt picker + candidates; existing-only multi-select of missing connector debts                                                                  |
| `models/collection_allocation_line.py`            | Invoice snapshot lines; related stored `sheet_id`/`partner_id`; required `document_kind`; related stored currency/company; CHECK/UNIQUE                        |
| `models/collection_allocation_revision.py`        | Immutable revisions; gated create; parent-unlink; UNIQUE(`request_id`)                                                                                         |
| `models/collection_receipt.py`                    | Receipt header; UNIQUE(allocation, kind); `draft`/`closed`/`issued`; freeze create; `collection_receipt_issuing`                                               |
| `models/collection_receipt_value.py`              | Voucher amounts on a receipt; CHECK amount > 0; UNIQUE(receipt, voucher)                                                                                       |
| `tools/collection_voucher.py`                     | Internal `_collection_*` helpers on `muk_mcp.mixin` (not an MCP tool)                                                                                          |
| `tools/collection_allocation.py`                  | `@mcp_tool` `create_collection_allocation` (write) on `muk_mcp.mixin`                                                                                          |
| `tools/allocation_lookup.py`                      | `@mcp_tool` `get_collection_allocation` (read) on `muk_mcp.mixin`                                                                                              |
| `tools/seller_lookup.py`                          | `@mcp_tool` `get_seller_id` (read) on `muk_mcp.mixin`                                                                                                          |
| `tools/customer_list.py`                          | `@mcp_tool` `list_collection_customers` (read) on `muk_mcp.mixin`                                                                                              |
| `tools/customer_debt.py`                          | `@mcp_tool` `customer_debt` (read) on `muk_mcp.mixin`                                                                                                          |
| `tools/sheet_report.py`                           | `@mcp_tool` `get_collection_sheet_pdf` (read) on `muk_mcp.mixin`; base64 Planilla                                                                              |
| `tools/collection_sheet_close.py`                 | `@mcp_tool` `close_collection_sheet` (write) on `muk_mcp.mixin`; Seller Close by `seller_id`                                                                   |
| `tools/collection_cash_declare.py`                | `@mcp_tool` `declare_collection_cash` (write) on `muk_mcp.mixin`; Declare Cash on submitted                                                                    |
| `tools/collection_seller_deposit.py`              | `@mcp_tool` `create_seller_deposit` (write) on `muk_mcp.mixin`; remittance on submitted                                                                        |
| `views/collection_views.xml`                      | List/search/form + menus/actions; no stages kanban; three-page notebook; `<delete>` reassign kanban; XLSX last before `state`                                  |
| `views/collection_allocation_views.xml`           | Allocation list/form/search; Customer Debt Add Debt + `create="false"`; Receipts page; parent-arch `document_kind`; menu sequence 30                           |
| `views/collection_receipt_views.xml`              | Read-mostly receipt `<list>`/`form`/`search`; Values + Applied Debt pages; issuance readonly; menu sequence 40                                                 |
| `report/collection_sheet_report_render.py`        | AbstractModel QWeb `_get_report_values`; `web.external_layout`; `t-out`                                                                                        |
| `report/collection_sheet_xlsx.py`                 | xlsxwriter workbook from payload; cached SUM; percent/100                                                                                                      |
| `report/report_paperformat.xml`                   | A4 portrait paperformat for Planilla de Cobranza                                                                                                               |
| `report/collection_sheet_report.xml`              | Bound `qweb-pdf` Print → Planilla de Cobranza                                                                                                                  |
| `report/collection_sheet_templates.xml`           | QWeb templates (`t-out`, `web.html_container` + `web.external_layout`)                                                                                         |
| `views/res_config_settings_views.xml`             | Collection Settings UI; XMLID `action_collection_config_settings`                                                                                              |
| `data/ir_sequence_data.xml`                       | Per-company seq XMLIDs on `base.main_company` (`COL/` + `CS/` + `CA/`)                                                                                         |
| `data/collection_document_type_data.xml`          | Eight catalog XMLID rows (`bank_transfer`, `check`, `echeck`, `cash_deposit`, `retention_certificate`, `cash`, `unsupported`); seed empty company allow-lists  |
| `security/collection_security.xml`                | Global `ir.rule` `[('company_id', 'in', company_ids)]`                                                                                                         |
| `security/ir.model.access.csv`                    | Voucher/sheet/allocation/line/receipt/value CRUD; picker transients `1,1,1,1`; snapshot/revision gated create; catalog read                                    |
| `migrations/19.0.1.17.0/post-migrate.py`          | Stamp/repair/seed/four-types; per-company `COL/` `CS/` (do not add `CA` here)                                                                                  |
| `migrations/19.0.1.25.0/post-migrate.py`          | Copy per-company sequences including `CA/` via `_collection_copy_sequences()`                                                                                  |
| `migrations/19.0.1.28.0/post-migrate.py`          | SQL remap allocation state from sheet (`open`→`draft`, `closed`→`confirmed`); collapse leftover keys                                                           |
| `migrations/19.0.1.31.0/post-migrate.py`          | SQL remap voucher state (`pending`→`draft`, `approved`→`validated_collections`, `rejected`→`draft`); no snapshot rewrite                                       |
| `migrations/19.0.1.32.0/post-migrate.py`          | DROP `residual_reason` on allocation+revision; DROP leftover line CHECKs; unlink inherit `document_kind` view                                                  |
| `migrations/19.0.1.33.0/post-migrate.py`          | Unlink reassign kanban XMLID from `ir_ui_view` + `ir_model_data`; no sheet-state remap                                                                         |
| `migrations/19.0.1.34.0/post-migrate.py`          | Additive no-op; MUST NOT backfill receipts                                                                                                                     |
| `migrations/19.0.1.40.0/post-migrate.py`          | Union all seven catalog types via `_collection_enable_all_document_types`; extras kept; `migrations/19.0.1.39.0/` and `migrations/19.0.1.40.1/` MUST NOT exist |
| `tests/test_collection_*.py`                      | TransactionCase coverage                                                                                                                                       |
| `openspec/specs/collection-vouchers/spec.md`      | Normative behavior                                                                                                                                             |
| `readme/DESCRIPTION.md`                           | Source for generated `README.rst`                                                                                                                              |

## Domain rules (do not break)

- **Collection Settings:** stored on `res.company` with related writable
  `res.config.settings`. Menu/action label is **Collection Settings**; keep XMLID
  `collection.action_collection_config_settings`. Fields: `enabled_seller_ids` (M2M
  internal users; empty = none for NEW work), `auto_create_sheet` (default True),
  `allowed_document_type_ids` (catalog M2M), keep `document_review_enabled`,
  `collection_connector_id` (company-scoped active connector). **Import** (Settings
  users) fetches `list_sellers()`, creates/matches users, upserts bindings (including
  overwrite of `commission_percent`), and **replaces** `enabled_seller_ids`. Catalog
  `collection.document.type` has eight XMLID rows (`bank_transfer`, `check`, `echeck`,
  `cash_deposit`, `retention_certificate`, `cash`, `unsupported`, `seller_deposit`);
  voucher `document_type` stays Selection, and `_selection_document_type` MUST take
  its **labels from the catalog record's `name`** (`translate=True`), not from
  `DOCUMENT_TYPE_SELECTION`: a method-resolved selection never reaches
  `ir.model.fields.selection`, so `_description_selection` would hand the constant's
  English to every language -- which is what the Conciliación board renders as
  `method`. The catalog mirrors the constant code for code, so en_US is unchanged and
  the constant stays the fallback for a code with no catalog row.
  `seller_deposit` stamps sentinel
  `collection.partner_seller_deposit`
  (`data/collection_seller_deposit_partner_data.xml`) via `_seller_deposit_partner()`.
  Voucher and snapshot carry `retention_kind`. MCP write still rejects `unsupported`.
- **New-work helper:** `res.company._assert_new_work(seller, document_type=None)`
  (`@api.private`). Seller is required; seller MUST be in `enabled_seller_ids` (empty
  list rejects); if `document_type` is not None it MUST be an allowed code. Raise
  `UserError`; never `sudo()`. Called on NEW voucher/sheet create and voucher
  `seller_id` / `document_type` write. Skip Validate by Seller / Review Approve /
  Confirm / Close / Cancel / Open and same-company MCP exact replay. Seller-only voucher
  write passes `document_type=None` so type is not re-checked.
- **Sequence:** per company (never `company_id=False` thief rows). Codes
  `collection.voucher` → `COL/<year>/<number>`, `collection.sheet` →
  `CS/<year>/<number>`, and `collection.allocation` → `CA/<year>/<number>`. Always
  `with_company(record.company_id).next_by_code(...)`. XMLIDs bind to
  `base.main_company` (`seq_collection_allocation`). `res.company.create` copies all
  three sequences (`number_next=1` on copies) and unions all eight types
  (`COLLECTION_TYPE_CODES` follows `DOCUMENT_TYPE_CODES`); new companies start with
  empty enabled sellers. Manifest `19.0.1.47.0`; migrate folders
  `migrations/19.0.1.17.0/` (COL/CS stamp/repair), `migrations/19.0.1.25.0/` (`CA/`
  copy), `migrations/19.0.1.28.0/` (allocation state remap; no `CA/`),
  `migrations/19.0.1.31.0/` (voucher state SQL remap; no snapshot `decision` rewrite),
  `migrations/19.0.1.32.0/` (DROP `residual_reason`; Customer Debt residual), and
  `migrations/19.0.1.33.0/` (unlink reassign XMLID; no sheet-state remap), and
  `migrations/19.0.1.34.0/` (additive; no receipt backfill), and
  `migrations/19.0.1.40.0/` (union all seven types onto every company via
  `_collection_enable_all_document_types`; extras kept), and `migrations/19.0.1.43.0/`
  (union all eight types including `seller_deposit`; extras kept), and
  `migrations/19.0.1.46.0/` (recompute stored `cash_on_hand` over the old
  seller-declared column; the column predates the compute so `_init_column` never
  fires). Do **not** add `collection.allocation` to `COLLECTION_SEQUENCE_CODES` in
  1.17.0. Do **not** add `migrations/19.0.1.26.0/`, `migrations/19.0.1.27.0/`,
  `migrations/19.0.1.29.0/`, `migrations/19.0.1.30.0/`, `migrations/19.0.1.35.0/`, or
  `migrations/19.0.1.36.0/` (Document Review OCR-only has no stored fields). Do **not**
  add `migrations/19.0.1.37.0/` (Add Debt picker has no stored fields). Do **not** add
  `migrations/19.0.1.38.0/` (Document Review editable OCR prefill has no stored fields).
  Do **not** add `migrations/19.0.1.39.0/` (receipts-only MCP write input has no stored
  fields). Do **not** add `migrations/19.0.1.40.1/` (allocatable `customer_debt` fields
  are response-only). Do **not** add `migrations/19.0.1.41.0/` (the
  `get_collection_sheet_pdf` MCP read tool has no stored fields). Do **not** add
  `migrations/19.0.1.42.0/` (additive Selection key; leftover scanner is the pin). Do
  **not** add `migrations/19.0.1.44.0/` (local Close; receipt `closed`; freeze create
  have no stored fields). Do **not** add `migrations/19.0.1.45.0/` (the Confirm
  cash-review exemption has no stored fields). Do **not** add `migrations/19.0.1.47.0/`
  (dropping the deposit auto-promote has no stored fields). Do **not** add a second 1.31
  migrate folder later.
- **No `received_date`:** registration time is ORM `create_date` only; strip forged
  `create_date` / `write_date` on create; views must not expose `received_date`.
- **States:** voucher `draft` → `validated_seller` → `validated_collections`. No Reject
  / no voucher `rejected`. ORM/UI create defaults `draft`; MCP
  `_collection_create_vouchers` stamps `validated_seller`. Form **Validate by Seller**
  (`action_validate_seller`) from `draft` only (no reviewer stamp). Validated by
  Collections only via Document Review Approve (no form button; intercept refuses raw
  `validated_collections`). Unlink only when voucher `state == 'draft'` **and**
  `allocation_id` is unset or **draft** (`@api.ondelete`). Draft + **confirmed**
  allocation refused. Unlink MUST NOT project voucher amounts onto residual and MUST NOT
  refuse because leftover-voucher residual would be `< 0`. Invoice lines MUST NOT be
  auto-edited. Attachment replacement of designated proof reopens to `validated_seller`
  and clears reviewer/time; clearing proof does not reopen. Write of `allocation_id`
  only when current and target are both `draft` or unset. Voucher `partner_id` write
  injects matching `allocation_id` into the same `super().write` vals (unique draft
  same-sheet attach without leftover-voucher residual or `residual_reason` checks;
  otherwise unallocated + chatter). Source residual 0 or leftover `<` amount MUST NOT
  refuse the move. Voucher-side `@api.constrains("partner_id", "allocation_id")`.
  Snapshot `decision` stays `approved`/`rejected` (not voucher states).
- **Sheet lifecycle:** `collection.sheet` `state` Selection is
  `open`/`submitted`/`proposal`/`closed`/`cancelled` (English Submitted by Seller; PDF
  Rendida). Default `open`. Seller Close (`action_seller_close` / MCP
  `close_collection_sheet`) writes `submitted` without declaration amounts. Declare Cash
  (`action_declare_cash(commission_withheld)` / MCP `declare_collection_cash`) runs only
  from `submitted` and takes the withheld commission only. Confirm runs only from
  `submitted`. Confirm/Close/Cancel/Open. Existing `open`/`closed` rows stay on upgrade
  (no remap). Raw `state` write is rejected except via Confirm/Close/Cancel/Open. Sheets
  inherit `mail.thread` + `mail.activity.mixin`; Seller Close, Declare Cash, Confirm,
  Close/Cancel/Open SHOULD be tracked in chatter. Confirm runs only from `submitted`
  (every member `validated_collections`, except `CONFIRM_REVIEW_EXEMPT_TYPES` — today
  just `cash`, which has no designated proof, so `validated_seller` is enough;
  `seller_deposit` is NOT exempt; `draft` always blocks; the `UserError` names the
  offending vouchers; empty members pass; collected cash > 0 requires
  `cash_declared_at`), writes `proposal`, and MUST NOT confirm allocations.
  `action_close` (from `proposal`) MUST NOT consult the connector and MUST NOT call
  `create_receipt`. Close, in one transaction, sets every local `draft` receipt to
  `closed` with no `external_receipt_id`, confirms every allocation, and closes the
  sheet. Historical `issued` receipts keep `issued` and their external id. Zero receipts
  still close. Cancel (from `submitted`, `proposal`, or `closed`) writes `cancelled` and
  drafts allocations (skip iff mid-flight via `collection_allocation_audited_state`,
  recheck after both writes). Cancel from `closed` reopens local `closed` receipts to
  `draft` and MUST NOT change `issued` receipts. Freeze remains until Reinstate. Open
  (from `cancelled`) writes `open` and leaves allocations `draft`. Unlink **open**
  sheets: unlink draft allocations first (vouchers unassigned). Unlink **proposal**,
  **closed**, or **cancelled** refused even when empty (`sheet_id`
  `ondelete="restrict"`). Recon inputs (`commission_percent` 0–100,
  `commission_withheld`) live on `models/collection_sheet_report.py` (second
  `_inherit`); Closed and Cancelled refuse those writes; Proposal remains editable; the
  seller declaration (`commission_withheld`) is writable only while `submitted`;
  Open-from-Cancelled keeps stored values. `cash_on_hand` (string Cash to
  Administration) is a **stored compute**,
  `cash_collected − cash_banked − commission_withheld` (cash vouchers minus
  `seller_deposit` vouchers minus the withheld commission); create and write of
  `cash_on_hand` raise `UserError` in every state, the MCP tool MUST NOT accept it, and
  the derived value makes the PDF recon banner balance by construction (`in_favor` is
  unreachable from real data).
- **Allocations:** `UNIQUE(sheet_id, partner_id)`. Selection `draft` | `confirmed`;
  default `draft` (`draft` iff sheet `open`/`proposal`/`cancelled`, `confirmed` iff
  sheet `closed`). Drop Validate/Reject. Freeze `line_ids` / `voucher_ids` /
  `receipt_ids` / `partner_id` / `sheet_id` when the sheet is **closed** or
  **cancelled**, including freeze create of allocations, lines, revisions, receipts,
  values, and cash replacements. Close confirms; Cancel drafts; Confirm does not confirm
  allocations. O2M `Command.DELETE` MUST unassign vouchers. Residual is
  `total_debt − total_applied` (negative allowed) in both `draft` and `confirmed`.
  Allocation and revision MUST NOT persist `residual_reason`. Revisions are immutable,
  gated by `collection_allocation_revision`, `UNIQUE(request_id)`; direct revision
  unlink stays `UserError`; draft parent-unlink uses
  `collection_allocation_parent_unlink`. Delete **draft** even with revisions; refuse
  **confirmed**. Related stored `currency_id` on line/revision; related stored
  `company_id` required precompute index on allocation/line/revision. Line
  `document_kind` is required Selection `invoice`/`quotation` (default `invoice`;
  `_init_column` backfill). Parent-arch `document_kind` immediately before
  `invoice_number` on the Customer Debt `<list>` (MUST NOT rely on inherit). MCP
  `create_collection_allocation` sends `document_kind` on `receipts[]`; each application
  inherits that kind. Get invoice rows include `document_kind`. Customer Debt disables
  native line create (`create="false"`) and exposes **Add Debt** for saved writable
  allocations. The picker searches live outstanding connector debts excluding
  `external_invoice_id` values already on the allocation, then inserts snapshots with
  `amount_applied` 0 (existing applied amounts stay). Connector identity/balance fields
  are form-readonly; `amount_applied` stays editable. Snapshotted and picked rows
  preserve connector `document_kind`.
- **One-open:** at most one open sheet per `(company_id, seller_id)` on NEW ops only
  (sheet create, Open from Cancelled, list Action, auto-assign). one-open still `open`
  only. `proposal`/`closed`/`cancelled` MUST NOT count. Same seller MAY have one open
  sheet in company A and one in B. Leftover `>1` open in that company remains
  Confirmable. No UNIQUE SQL. Advisory lock
  `pg_advisory_xact_lock(hashtext('collection.sheet.open.' || company_id), seller_id)`.
- **Closed freeze:** no add/remove/reassign of membership while `proposal`, `closed`, or
  `cancelled`, including voucher `partner_id`; voucher `unlink` still unassigns
  (`ondelete="set null"`). Reuses
  `"Closed collection sheets cannot change membership. Reopen first."`
- **Auto-assign:** ORM `voucher.create` assigns only when company `auto_create_sheet` is
  ON, `seller_id` is set, and `sheet_id` is omitted (0 create open in that company / 1
  use / `>1` UserError). OFF skips create **and** assign (voucher stays unassigned).
  Later `seller_id` write does not assign. Auto-created sheets stamp the voucher
  company.
- **List Action:** still create-new-sheet even when auto is OFF; reject if that seller
  already has an open sheet **in the selection company**; selection must be one company;
  sheet gets that company. Helper still runs via `sheet.create`.
- **Currency:** company default; no multi-currency UX.
- **Customer / partner:** voucher requires `partner_id` (Many2one `res.partner`, label
  Customer). The Char `customer_identification` field is gone. MCP
  `create_collection_allocation` accepts a top-level `customer_identification` string
  and resolves it server-side on all-new voucher create via the fused write.
- **ACL:** internal users only (`base.group_user`); no extra groups. Required
  `company_id` (default `env.company`) on voucher/sheet; snapshot related stored
  `company_id` from `voucher_id.company_id` (`required=True`, `precompute=True`).
  Allocation/line/revision related stored `company_id` from sheet/allocation
  (`required=True`, `precompute=True`, `index=True`). Global `ir.rule`
  `[('company_id', 'in', company_ids)]` on voucher, sheet, snapshot, connector, seller
  binding, customer binding, allocation, line, revision, receipt, and value
  (`security/collection_security.xml`). Catalog is read-only for `base.group_user`.
  Connector/seller binding: `group_user` read, `group_system` write. Customer binding:
  `group_user` `1,0,1,0` (read+create; no write/unlink), `group_system` `1,1,1,1`.
  Allocation and line: `group_user` `1,1,1,1`. Add Debt picker and candidates:
  `group_user` `1,1,1,1` (transients; no company `ir.rule`). Receipt and value:
  `group_user` `1,1,1,1`. Revision: `group_user` `1,0,1,1` (unlink for cascade;
  `@api.ondelete` is the lock). Never `sudo()`.
- **Attachment:** optional one image/PDF designated proof per voucher
  (`message_main_attachment_id`, chatter `ir.attachment`, `copy=False` on rotation);
  extras do not steal proof; server validates base64 and detected MIME on MCP nest; omit
  remains valid. Replacing designated proof reopens `state` to `validated_seller` and
  clears reviewer/time; extras and clearing proof do not reopen. Document Review serves
  `/web/content/{id}` (no Binary `field=attachment`).
- **MCP:**
  - `create_collection_vouchers` is **not** an MCP tool. Internal `_collection_*`
    helpers remain on `muk_mcp.mixin` in `tools/collection_voucher.py` and are reused by
    `create_collection_allocation`. `_collection_create_vouchers` stamps
    `validated_seller` on all-new create. They MUST NOT be `@mcp_tool` and MUST NOT have
    a `muk_mcp.tool` row.
  - Method-discovered `@mcp_tool` `get_seller_id` (`category=read`, `registry=mcp`) in
    `tools/seller_lookup.py`. Required `mobile` (WhatsApp/mobile string; **no
    connector** in this addon). Unique internal match on
    `env.company.enabled_seller_ids` → `{seller_id}` only. Empty enabled list or
    unique-but-not-enabled → same generic `UserError`
    (`No unique seller found for that mobile.`). Does not write vouchers, fill invoke
    context, or replace write-tool connector `seller_id`.
  - MUST NOT expose `list_collection_sellers` or any MCP tool that lists connector
    sellers. Import uses ORM `collection.connector.list_sellers()` only.
  - Method-discovered `@mcp_tool` `get_collection_sheet_pdf` (`category=read`,
    `registry=mcp`) in `tools/sheet_report.py`. Required integer `seller_id` only.
    Internal caller; resolves the seller's single `open` sheet via
    `_open_sheets_for_seller` on `env.company` (MUST NOT widen that helper). When there
    is no open sheet, it serves the seller's single `submitted` sheet via
    `_submitted_sheets_for_seller`. Renders `collection.action_report_collection_sheet`
    and returns
    `{sheet:{id,name,state,seller_id,date_from,date_to,voucher_count},filename,mimetype,content_base64}`.
    No open and no submitted sheet → `{sheet: null}`; more than one open or more than
    one submitted sheet → same `UserError` as `get_collection_allocation`. Open
    preferred over submitted. No connector, no `sudo()`, no attachment written. MUST NOT
    expose the XLSX or accept a `sheet_id`, report ref, or any generic report argument.
  - Method-discovered `@mcp_tool` `close_collection_sheet` (`category=write`,
    `registry=mcp`) in `tools/collection_sheet_close.py`. Required integer `seller_id`
    only. MUST NOT accept `cash_on_hand` or `commission_withheld`. Internal caller;
    `_collection_require_internal_seller` then lock, `_open_sheets_for_seller`,
    `check_access("write")`, `action_seller_close`. Success
    `{sheet:{id,name,state,seller_id,date_from,date_to,voucher_count}, cash:{collected}}`
    with `state` `submitted`. `cash.collected` is SUM of `document_type == "cash"` on
    that sheet. No open sheet → `UserError` (MUST NOT `{sheet: null}`). More than one
    open sheet → same `UserError` as `get_collection_allocation`. Disabled sellers MAY
    still close. No `sudo()`, no `sheet_id`, no report bytes. MUST NOT add a migrate
    folder for this tool.
  - Method-discovered `@mcp_tool` `declare_collection_cash` (`category=write`,
    `registry=mcp`) in `tools/collection_cash_declare.py`. Required integer `seller_id`
    plus `cash_on_hand` and `commission_withheld` (schema `number`; decimal strings
    accepted). Internal caller; `_collection_require_internal_seller` then lock,
    `_submitted_sheets_for_seller` (MUST NOT `_open_sheets_for_seller`),
    `check_access("write")`, `action_declare_cash`. Success
    `{sheet:{id,name,state,seller_id,date_from,date_to,voucher_count}}` with `state`
    `submitted`. Zero submitted sheets → `UserError` (MUST NOT `{sheet: null}`). More
    than one submitted sheet → same `UserError` as `get_collection_allocation`. Disabled
    sellers MAY still declare. No `sudo()`, no `sheet_id`, no report bytes.
  - Method-discovered `@mcp_tool` `create_seller_deposit` (`category=write`,
    `registry=mcp`) in `tools/collection_seller_deposit.py`. Required integer
    `seller_id`, `amount`, `voucher_number`, `voucher_date` (ISO); optional nested
    `attachment`. MUST NOT accept `customer_identification` or `sheet_id`. Internal
    caller; `_assert_new_work(seller, "seller_deposit")`, lock,
    `_submitted_sheets_for_seller` (MUST NOT `_open_sheets_for_seller`),
    `check_access("write")`. Mints `sd-<uuid4 hex>`; stamps sentinel +
    `validated_seller` + explicit `sheet_id`. MUST NOT write `validated_collections`:
    the slip is designated proof, so the deposit enters `get_review_queue` and only
    Document Review Approve promotes it (and runs cash replacement). Success
    `{sheet:{...}, voucher:{id,name,state,document_id}}` with sheet `submitted`. 0 or
    `>1` submitted → `UserError`. Portal/public → `AccessError`. Do **not** add
    `seller_deposit` to allocation `_DOCUMENT_TYPES`. No `sudo()`.
  - Method-discovered `@mcp_tool` `list_collection_customers` (`category=read`,
    `registry=mcp`) in `tools/customer_list.py`. Required integer `seller_id` (internal
    `res.users` id). Internal caller; must be on `env.company.enabled_seller_ids` and
    bound on the current company's connector. Dispatches the **external** seller id to
    the selected adapter. Success:
    `{customers:[{external_customer_id,name,identification,customer_code}]}` (no
    `source`). Payload keys and values unchanged. Drop inactive externals. MUST NOT
    create `res.partner` or customer bindings. MUST NOT import or open SQLite in this
    addon.
  - Method-discovered `@mcp_tool` `customer_debt` (`category=read`, `registry=mcp`) in
    `tools/customer_debt.py`. Required integer `seller_id` and non-empty
    `customer_identification`. Same Enabled Seller + connector-binding gates as
    `list_collection_customers`. Dispatches the **external** seller id plus
    identification to the selected adapter. Unknown, other-seller, or inactive customers
    → generic `UserError`. Active customer with no debt → zero totals and
    `invoices: []`. Success:
    `{customer:{external_customer_id,name,identification,customer_code}, summary:{total_balance,overdue_balance,open_balance,invoice_count,total_allocatable_balance,open_allocatable_balance,overdue_allocatable_balance}, invoices:[{external_invoice_id,number,issue_date,due_date,amount,balance,allocatable_balance,state,document_kind}]}`
    (no `source`). Gross `balance` and existing summary totals stay the connector
    values. `allocatable_balance` is gross minus same-company draft+confirmed
    `amount_applied` (including hidden proposal/closed/cancelled sheets), clamped at 0.
    Outstanding invoices only (`balance > 0`, state `open`/`overdue`). MUST NOT create
    `res.partner` or customer bindings. MUST NOT import or open SQLite in this addon.
  - Method-discovered `@mcp_tool` `create_collection_allocation` (`category=write`,
    `registry=mcp`) in `tools/collection_allocation.py`. Required `seller_id`, top-level
    `customer_identification`, `request_id`, `payments[]` (`minItems` 1; items omit
    `customer_identification`; recheck in Python), and `receipts[]` (`minItems` 1). MUST
    NOT accept `invoices`, `splits`, `total_debt`, or `residual_reason`. Internal
    caller; `_collection_require_internal_seller` then `_assert_new_work` on the write
    path. Fail-closed: `auto_create_sheet` False → named UserError
    `"This company requires a collection sheet chosen in Odoo."` and zero writes. Lazy
    partner via `_collection_create_vouchers` / `resolve_customer_partner` (MAY create
    `res.partner` plus `collection.connector.customer.binding`); identity assert after
    create. Order: form → seller → `request_id` replay → `_assert_new_work` → auto-sheet
    gate → classify `document_id`s (all-new create / exact set reuse continues / else
    generic conflict) → voucher-set gates (all voucher states may allocate) → lock →
    hash (vouchers plus receipt values, applications, and `document_kind`; MUST NOT
    include `residual_reason`) → ERP revalidate (`balance_seen` vs fresh
    `currency.compare_amounts`; expand outstanding zeros; subtract other **draft and
    confirmed** applications) → persist (`state` omitted so default `draft`; revision
    1). Advisory lock on create `(sheet, partner)`; `FOR UPDATE` on amend; amend only
    while **draft**; PUT voucher set MUST be a superset. Identical `request_id` and
    matching `content_hash` replay with zero writes. `UniqueViolation` →
    `invalidate_all()` → replay or generic conflict (no ids). Success:
    `{sheet_id, vouchers:[{id,name,state,document_id}] in submit order, allocation:{id,name,state,revision:int,total_vouchers,total_applied,residual}}`.
    MUST NOT `sudo()`. `_DISPATCH_OPS` includes `create_receipt` (unused from Close;
    Import still calls `list_sellers()` only). Errors are raised, never `{"error":...}`.
  - Method-discovered `@mcp_tool` `get_collection_allocation` (`category=read`,
    `registry=mcp`) in `tools/allocation_lookup.py`. Required `seller_id` and
    `customer_identification`. Internal caller; enabled bound seller. Uses
    `_open_sheets_for_seller` (MUST NOT `_resolve_open_sheet_id_for_create`).
    Binding-only partner lookup (MUST NOT `resolve_customer_partner`). Unbound / no open
    sheet / no allocation → `{allocation: null}`. Multi-open leftover → existing
    multi-open `UserError`. Found →
    `{allocation:{...} (no residual_reason), vouchers:[...], invoices:[... + document_kind], receipts:[...]}`
    (`receipts` always present, empty list ok). Zero writes. Never
    attachment/`datas`/base64. MUST NOT `sudo()`.
  - **Never** `sudo()`; never add a DB `muk_mcp.tool` record for these tools.
  - Payment items omit `customer_identification`; helpers take top-level identification
    and replicate it per payment. Optional nested `attachment` per payment (`name`,
    `mimetype`, base64 `datas`); validate MIME vs content; create atomically inside the
    existing savepoint. Required nested `seller_confirmed` (typed
    `_REVIEW_EDITABLE_FIELDS`; nest `document_type` required; no
    `document_id`/attachment/base64). Optional nested `raw_ocr` (same nest shape).
    Voucher fields (`document_type` plus optional payment fields) MUST be derived from
    `seller_confirmed` (MUST NOT treat top-level `document_type`/`amount` as source of
    truth). Reject `unsupported` and non-positive `seller_confirmed` amount. Stamp
    `seller_*` always on all-new create; stamp `ocr_*` only when `raw_ocr` is present.
    Raw without seller → `UserError`, no writes. UI/ORM create without nests remains
    allowed. Malformed nests or seller≠derived current (minus `document_id`) →
    `UserError`, no writes. Parse nests on the fused create path after classify and
    before persist.
  - Receipt items require `document_kind` (`invoice`|`quotation`) and `values[]`
    (`minItems` 1; `{document_id, amount}` amount > 0). `applications[]` MAY be empty
    (on account). Each application: `external_document_id`, optional `number`,
    `balance_seen` > 0, `amount_applied` > 0 and `<= balance_seen`. Unique
    `document_kind` across receipts; unique `document_id` within a receipt's values;
    unique `external_document_id` within a receipt's applications and across the call
    (`UNIQUE(allocation, external_invoice_id)`). Per-receipt applied_total <=
    funded_total. Every value `document_id` MUST reference a payment in this call.
    Per-payment values across receipts MUST equal the `seller_confirmed` amount (full
    split). Unknown `document_id` / duplicate payment+kind → `UserError`, no writes.
    Flatten applications into allocation lines (`external_invoice_id` ←
    `external_document_id`, `document_kind` from the parent receipt) and values into
    receipt values. Rebuild receipts from explicit values (MUST NOT FIFO-compat from
    invoices). Stale `balance_seen` vs fresh connector `balance` → `UserError`, no
    writes.
  - Exact same-company `document_id` set MUST reuse rows and continue to allocation
    (MUST NOT voucher-only early-return). Partial overlap and other-company hits stay
    generic conflict with no writes. Exact reuse MUST NOT add, replace, or compare
    attachments and MUST ignore provenance nests (no backfill).
  - Handle `UniqueViolation` races with invalidate + classify (nests ignored). Hidden
    other-company / no same-company exact set → generic `UserError`
    `Payment document_id conflict could not be resolved.` (no ids). Keep global
    `UNIQUE(document_id)`.
- **Provenance / review history:** `ocr_*`/`seller_*` copies of
  `_REVIEW_EDITABLE_FIELDS` (`copy=False`). `write()` rejects those keys; `create()` may
  stamp. Snapshots append only from `_write_review_decision` (Document Review Approve
  including empty vals). Approve applies sanitized current `_REVIEW_EDITABLE_FIELDS`
  from client `vals`, then snapshots; empty/omitted vals leave current unchanged.
  `ocr_*`/`seller_*` stay create-only. No Reject; form `action_validate_seller` does not
  snapshot. Snapshot `decision` stays `approved`/`rejected` (historical `rejected` rows
  MAY remain; those keys are not voucher states). Snapshot ACL: read+gated create
  (`collection_review_snapshot`); write/unlink denied; no `sudo()` / no extra groups;
  **does** use the company `ir.rule`.
- **UI** may omit `document_id`; MCP may not. Seller domain on voucher/sheet views is
  the company enabled list; document-type choices are allowed ∪ current value. Payment
  Vouchers menu is sequence 10 (`view_mode` `list,form`). Stages kanban
  `view_collection_voucher_kanban` is `<delete>`d — do **not** re-add it. Form shows
  non-clickable statusbar and **Validate by Seller** when `draft`; no Reject, no
  Collections button, no History tab (`review_snapshot_ids` unbound). Allocations menu
  is sequence 30 under `menu_collection_root` (after sheets at 20). Collection Receipts
  menu is sequence 40. Receipt views are read-mostly: `state` is form-readonly (local
  Close marks `closed`; the form does not issue). The receipt form notebooks Values
  (`value_ids`) then Applied Debt (`line_ids`, computed applications with
  `amount_applied > 0`; `create`/`delete`/`edit` false). Applied Debt lists
  `invoice_number`, `due_date`, `invoice_amount`, `invoice_balance`, and
  `amount_applied`. Collection Receipts and the allocation Receipts list MUST NOT show
  `external_receipt_id`. Allocation form notebooks Vouchers, Customer Debt, Receipts,
  and Revisions. Customer Debt has **Add Debt** (saved writable only) and
  `create="false"` on the embedded list; identity/balance columns are readonly. Sheet
  form notebook is Allocations, Vouchers, and Debt (`allocation_ids`, `voucher_ids`,
  `debt_line_ids`); membership is via voucher `sheet_id`. Reassign header, kanban XMLID,
  and partner `group_expand` are dropped. Allocation form has no Validate/Reject; freeze
  fields `readonly` from `sheet_id.state`; statusbar `draft,confirmed`; search filters
  draft+confirmed. Sheet statusbar `open,submitted,proposal,closed,cancelled` with
  Confirm/Close/Cancel/Open by state; Document Review Open-only. Document Review OWL
  shows one editable control per field prefilled from OCR (current fallback); Approve
  rewrites current only. `reviewed_by` / `reviewed_at` stay on the model and leave the
  form. Print → Planilla de Cobranza is bound `qweb-pdf` (`web.external_layout`,
  `t-out`). Header **Export XLSX** is last object button before `state`
  (`action_print_xlsx` → `/web/content/{id}?download=true`). Recon fields sit in a
  second inner `<group>` on the Allocations page. Shared `_collection_report_data()`
  feeds both writers in every sheet state; print includes draft allocations/vouchers;
  `mismatch` when voucher SUM ≠ allocation `total_vouchers`. MUST NOT `sudo()`.
- **Odoo 19:** use `<list>` not `<tree>`; `models.Constraint` not `_sql_constraints`;
  `t-out` not `t-esc`; `@api.ondelete` for delete rules.

## Testing instructions

On an already-installed devel DB, default `invoke test -m collection` (`mode=init`)
reports **0 tests**. Use update mode:

```bash
invoke test -m collection --mode=update
invoke test -m collection --mode=update -d devel
```

| File                                                | Focus                                                                                                                                                                                                                                                                                                                                                                                                                           |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tests/test_collection_voucher.py`                  | Sequence, defaults `draft`, Validate by Seller, unlink, attachment reopen, new-work helper                                                                                                                                                                                                                                                                                                                                      |
| `tests/test_collection_sheet.py`                    | Sheet lifecycle, Confirm/Close/Cancel/Open, one-open, freeze, auto-assign, open cascade / non-open refuse                                                                                                                                                                                                                                                                                                                       |
| `tests/test_collection_payment.py`                  | Line fields, `document_id` uniqueness                                                                                                                                                                                                                                                                                                                                                                                           |
| `tests/test_collection_acl.py`                      | Internal ACL; required `company_id`; `ir.rule` hide-other-company                                                                                                                                                                                                                                                                                                                                                               |
| `tests/test_collection_allocation.py`               | UNIQUE(sheet, partner); draft default; freeze invert; residual both; draft unlink; revisions                                                                                                                                                                                                                                                                                                                                    |
| `tests/test_collection_allocation_debt_picker.py`   | Missing-debt picker: exclude existing, multi-select insert, preserve applied, empty connector, unsaved/frozen, company isolation, document_kind                                                                                                                                                                                                                                                                                 |
| `tests/test_collection_allocation_acl.py`           | Allocation/line `1,1,1,1`; picker transients `1,1,1,1`; revision `1,0,1,1`; company `ir.rule`; no sudo                                                                                                                                                                                                                                                                                                                          |
| `tests/test_collection_mail.py`                     | Chatter / tracking on vouchers and sheets                                                                                                                                                                                                                                                                                                                                                                                       |
| `tests/test_collection_ui.py`                       | View arch; Add Debt picker; Customer Debt `create="false"`; Collection Settings; menus 10/30/40; Receipts page; receipt Applied Debt; form does not issue                                                                                                                                                                                                                                                                       |
| `tests/test_collection_document_review.py`          | Queue `validated_seller`+proof; one editable OCR-prefilled OWL control; Approve rewrites current; no Reject; snapshots `decision` approved/rejected                                                                                                                                                                                                                                                                             |
| `tests/test_collection_company_settings.py`         | Catalog, empty sellers, defaults, Collection Settings fields                                                                                                                                                                                                                                                                                                                                                                    |
| `tests/test_collection_company_migration.py`        | Stamp/repair/seed/four-types; per-company `COL/` `CS/` `CA/`; `19.0.1.28.0` remap; `19.0.1.31.0` voucher remap; manifest `19.0.1.47.0`; keep `19.0.1.46.0` cash_on_hand recompute; leftover pin no `migrations/19.0.1.44.0/` / `19.0.1.45.0/` / `19.0.1.47.0/`; `19.0.1.40.0` union-all; keep 1.31–1.34 / 1.43.0; no 1.26–1.30 / 1.35 / 1.36 / 1.37 / 1.38 / 1.39 / 1.40.1 / 1.41.0 / 1.42.0 / 1.44.0 / 1.45.0 / 1.47.0 migrate |
| `tests/test_collection_allocation_document_kind.py` | Line `document_kind` default/selection/parent-arch `<list>`; MCP receipt kind; get returns kind                                                                                                                                                                                                                                                                                                                                 |
| `tests/test_collection_sheet_report_data.py`        | Recon fields, payload primitives, freeze Closed+Cancelled, Proposal editable, four-state PDF payload, mismatch, mixed currency, no sudo                                                                                                                                                                                                                                                                                         |
| `tests/test_collection_sheet_report.py`             | Bound `qweb-pdf` + A4 portrait; HTML names/banner/`t-out`; company-B AccessError                                                                                                                                                                                                                                                                                                                                                |
| `tests/test_collection_sheet_xlsx.py`               | Zip/`A6`/cached SUM; percent/100; `act_url`; XLSX last; four-state download; three notebook pages; no sudo                                                                                                                                                                                                                                                                                                                      |
| `tests/test_collection_mcp_tool.py`                 | MCP attachment + provenance nests on `create_collection_allocation`                                                                                                                                                                                                                                                                                                                                                             |
| `tests/test_collection_mcp_seller_lookup.py`        | MCP `get_seller_id` discovery, match, fail-closed, enabled-list                                                                                                                                                                                                                                                                                                                                                                 |
| `tests/test_collection_mcp_customer_list.py`        | MCP `list_collection_customers` auth, routing, normalized payload                                                                                                                                                                                                                                                                                                                                                               |
| `tests/test_collection_mcp_customer_debt.py`        | MCP `customer_debt` auth, routing, outstanding payload, fail-closed                                                                                                                                                                                                                                                                                                                                                             |
| `tests/test_collection_mcp_allocation.py`           | MCP `create_collection_allocation` persist draft, amend iff draft, replay, gates, UniqueViolation                                                                                                                                                                                                                                                                                                                               |
| `tests/test_collection_mcp_allocation_lookup.py`    | MCP `get_collection_allocation` discovery, auth, null, found, `receipts[]`, no-write                                                                                                                                                                                                                                                                                                                                            |
| `tests/test_collection_mcp_sheet_pdf.py`            | MCP `get_collection_sheet_pdf` discovery, seller-only schema, auth, null branches, base64 envelope, company scoping, no sudo                                                                                                                                                                                                                                                                                                    |
| `tests/test_collection_mcp_sheet_close.py`          | MCP `close_collection_sheet` discovery, seller-only schema, 0-open UserError, cash.collected, no sudo                                                                                                                                                                                                                                                                                                                           |
| `tests/test_collection_mcp_cash_declare.py`         | MCP `declare_collection_cash` discovery, submitted-only, 0-submitted UserError, no sudo                                                                                                                                                                                                                                                                                                                                         |
| `tests/test_collection_mcp_seller_deposit.py`       | MCP `create_seller_deposit` discovery, submitted-only, sentinel, `validated_seller` outcome, review-queue membership, Approve promote plus cash replacement, unreviewed deposit blocks Confirm, allocation still customer-required                                                                                                                                                                                              |
| `tests/test_collection_receipt.py`                  | Receipt uniqueness, values, totals, freeze, issued, local Close `closed`, ACL                                                                                                                                                                                                                                                                                                                                                   |
| `tests/test_collection_customer_binding.py`         | Customer binding UNIQUE / ACL `1,0,1,0` / company `ir.rule` / notebook                                                                                                                                                                                                                                                                                                                                                          |
| `tests/test_collection_customer_resolution.py`      | Lazy `resolve_customer_partner`; vat 1/0/>1; nested UniqueViolation                                                                                                                                                                                                                                                                                                                                                             |
| `tests/test_collection_mcp_partner_resolve.py`      | MCP allocation write: lazy resolve, invalid rollback, replay keeps first-call partner                                                                                                                                                                                                                                                                                                                                           |
| `tests/test_collection_seller_sync.py`              | Import create/match/bind, replace-all, fail-closed, idempotent                                                                                                                                                                                                                                                                                                                                                                  |
| `tests/test_collection_connector.py`                | Dispatcher allowlist including `create_receipt`; seller-binding uniqueness; `list_customers()` / `get_customer_debt()` / Import `list_sellers()`                                                                                                                                                                                                                                                                                |

Strict TDD is enabled in `openspec/config.yaml`. Add or update tests in the same change
as behavior.

Lint (scoped):

```bash
pre-commit run --files odoo/custom/src/private/collection/**
# from seedian root; or: invoke lint
```

## Code style

- AGPL-3.0-or-later headers on new `.py` / `__manifest__.py`.
- Follow parent pre-commit: Ruff, pylint-odoo, Prettier XML, OCA checks.
- Prefer batch `create([{...}, ...])`, savepoints around MCP create, no N+1 searches in
  loops.
- Commit prefix (OCA style): `[ADD|IMP|FIX|REF|REM|MIG] collection: …`

## Build / deploy notes

- Installable application (`application: True`).
- Image rebuild only if new apt/pip deps are added under parent
  `odoo/custom/dependencies/` (not typical for this addon).
- After XML/Python changes: module upgrade is required for the running container to see
  them.

## Pull request guidelines

- One focused concern per PR; keep diffs reviewable (~400 LOC soft budget).
- Required locally: scoped pre-commit + `invoke test -m collection --mode=update`.
- Link or update OpenSpec when requirements change; archive completed changes under
  `openspec/changes/archive/`.

## Troubleshooting

| Symptom                     | Likely cause                                                                            |
| --------------------------- | --------------------------------------------------------------------------------------- |
| MCP tool missing            | `muk_mcp` not installed / mixin not loaded; confirm `tools/` import                     |
| Access denied on MCP create | Caller not in `base.group_user`, missing ACL, or company `ir.rule`                      |
| Duplicate document errors   | Global `UNIQUE(document_id)` or company-scoped idempotency                              |
| Other-company MCP replay    | Classifier rejects visible other-company / hidden UniqueViolation                       |
| Sequence stuck at `/`       | Per-company `collection.voucher` / `collection.sheet` / `collection.allocation` missing |
| UI still shows old fields   | Forgot `-u collection` upgrade                                                          |
| Edits “disappear”           | Wrong container project name; use `seedian-odoo-1` from repo root                       |

## Additional notes

- Parent agents must not edit `odoo/custom/src/odoo/` or `OCA/` for this feature;
  declare deps via git-aggregate if needed.
- Prefer extending `tools/collection_voucher.py` helpers (`_collection_*`) over
  duplicating idempotency logic elsewhere. Those helpers are internal; do not
  re-register `create_collection_vouchers` as an MCP tool.
