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
  `collection.sheet` (`open`/`proposal`/`closed`/`cancelled` grouping per seller;
  chatter + activities); `collection.allocation` (one per `(sheet_id, partner_id)`;
  `draft` / `confirmed`; chatter + activities) plus `collection.allocation.line` and
  immutable `collection.allocation.revision`; `collection.connector` (company-scoped
  seller source); `collection.connector.seller.binding` (1:1 external seller ↔
  `res.users`); `collection.connector.customer.binding` (1:1 external customer ↔
  `res.partner`).
- **Integrations:** `mail.thread` / activities on vouchers and sheets; MuK MCP tools on
  `muk_mcp.mixin`: write `create_collection_allocation`; read `get_seller_id` plus
  `list_collection_customers` plus `customer_debt` plus `get_collection_allocation`.
  Coordinated Nebula first-party tool `register_latest_collection_voucher` lives in
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

| Path                                              | Role                                                                                                                                    |
| ------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `__manifest__.py`                                 | Module metadata `19.0.1.34.0`; depends `base`, `mail`, `muk_mcp`, `web`                                                                 |
| `models/res_company.py`                           | Collection Settings fields + `_assert_new_work`; Import sync; seq copy; type seed                                                       |
| `models/res_config_settings.py`                   | Related writable Collection Settings + Import action                                                                                    |
| `models/collection_connector.py`                  | Company-scoped connector + `_dispatch` allowlist (`list_customers`, `get_customer_debt`, `create_receipt`)                              |
| `models/collection_connector_seller_binding.py`   | 1:1 external seller ↔ `res.users`; UNIQUE + related stored `company_id`; stores `commission_percent`; Import overwrite                  |
| `models/collection_connector_customer_binding.py` | 1:1 external customer ↔ `res.partner`; UNIQUE + related stored `company_id`                                                             |
| `models/collection_document_type.py`              | Catalog `code`/`name`; `UNIQUE(code)` Constraint                                                                                        |
| `models/collection_voucher.py`                    | Voucher model, sequence on create, Validate by Seller, draft-only unlink, provenance copies, `allocation_id`; freeze non-open writes    |
| `models/collection_voucher_review_snapshot.py`    | Immutable Document Review snapshots (`UNIQUE(voucher_id, revision)`)                                                                    |
| `models/collection_sheet.py`                      | Sheet model, `open`/`proposal`/`closed`/`cancelled`, Confirm/Close/Cancel/Open; one-open; freeze; cascade open unlink                   |
| `models/collection_sheet_report.py`               | Second `_inherit`: recon fields, `_collection_report_data()`, `action_print_xlsx`; freeze Closed+Cancelled                              |
| `models/collection_allocation.py`                 | Allocation header; UNIQUE(sheet, partner); draft iff Open/Proposal/Cancelled; freeze when sheet Closed/Cancelled                        |
| `models/collection_allocation_line.py`            | Invoice snapshot lines; related stored `sheet_id`/`partner_id`; required `document_kind`; related stored currency/company; CHECK/UNIQUE |
| `models/collection_allocation_revision.py`        | Immutable revisions; gated create; parent-unlink; UNIQUE(`request_id`)                                                                  |
| `models/collection_receipt.py`                    | ERP receipt header; UNIQUE(allocation, kind); `draft`/`issued`; freeze; `collection_receipt_issuing`                                    |
| `models/collection_receipt_value.py`              | Voucher amounts on a receipt; CHECK amount > 0; UNIQUE(receipt, voucher)                                                                |
| `tools/collection_voucher.py`                     | Internal `_collection_*` helpers on `muk_mcp.mixin` (not an MCP tool)                                                                   |
| `tools/collection_allocation.py`                  | `@mcp_tool` `create_collection_allocation` (write) on `muk_mcp.mixin`                                                                   |
| `tools/allocation_lookup.py`                      | `@mcp_tool` `get_collection_allocation` (read) on `muk_mcp.mixin`                                                                       |
| `tools/seller_lookup.py`                          | `@mcp_tool` `get_seller_id` (read) on `muk_mcp.mixin`                                                                                   |
| `tools/customer_list.py`                          | `@mcp_tool` `list_collection_customers` (read) on `muk_mcp.mixin`                                                                       |
| `tools/customer_debt.py`                          | `@mcp_tool` `customer_debt` (read) on `muk_mcp.mixin`                                                                                   |
| `views/collection_views.xml`                      | List/search/form + menus/actions; no stages kanban; three-page notebook; `<delete>` reassign kanban; XLSX last before `state`           |
| `views/collection_allocation_views.xml`           | Allocation list/form/search; Customer Debt; Receipts page; parent-arch `document_kind`; `path`; menu sequence 30 after sheets           |
| `views/collection_receipt_views.xml`              | Read-mostly receipt `<list>`/`form`/`search`; issuance readonly; menu sequence 40                                                       |
| `report/collection_sheet_report_render.py`        | AbstractModel QWeb `_get_report_values`; `web.external_layout`; `t-out`                                                                 |
| `report/collection_sheet_xlsx.py`                 | xlsxwriter workbook from payload; cached SUM; percent/100                                                                               |
| `report/report_paperformat.xml`                   | A4 landscape paperformat for Planilla de Cobranza                                                                                       |
| `report/collection_sheet_report.xml`              | Bound `qweb-pdf` Print → Planilla de Cobranza                                                                                           |
| `report/collection_sheet_templates.xml`           | QWeb templates (`t-out`, `web.html_container` + `web.external_layout`)                                                                  |
| `views/res_config_settings_views.xml`             | Collection Settings UI; XMLID `action_collection_config_settings`                                                                       |
| `data/ir_sequence_data.xml`                       | Per-company seq XMLIDs on `base.main_company` (`COL/` + `CS/` + `CA/`)                                                                  |
| `data/collection_document_type_data.xml`          | Four catalog XMLID rows; seed empty company allow-lists                                                                                 |
| `security/collection_security.xml`                | Global `ir.rule` `[('company_id', 'in', company_ids)]`                                                                                  |
| `security/ir.model.access.csv`                    | Voucher/sheet/allocation/line/receipt/value CRUD; snapshot/revision gated create; catalog read; customer binding `1,0,1,0`              |
| `migrations/19.0.1.17.0/post-migrate.py`          | Stamp/repair/seed/four-types; per-company `COL/` `CS/` (do not add `CA` here)                                                           |
| `migrations/19.0.1.25.0/post-migrate.py`          | Copy per-company sequences including `CA/` via `_collection_copy_sequences()`                                                           |
| `migrations/19.0.1.28.0/post-migrate.py`          | SQL remap allocation state from sheet (`open`→`draft`, `closed`→`confirmed`); collapse leftover keys                                    |
| `migrations/19.0.1.31.0/post-migrate.py`          | SQL remap voucher state (`pending`→`draft`, `approved`→`validated_collections`, `rejected`→`draft`); no snapshot rewrite                |
| `migrations/19.0.1.32.0/post-migrate.py`          | DROP `residual_reason` on allocation+revision; DROP leftover line CHECKs; unlink inherit `document_kind` view                           |
| `migrations/19.0.1.33.0/post-migrate.py`          | Unlink reassign kanban XMLID from `ir_ui_view` + `ir_model_data`; no sheet-state remap                                                  |
| `migrations/19.0.1.34.0/post-migrate.py`          | Additive no-op; MUST NOT backfill receipts                                                                                              |
| `tests/test_collection_*.py`                      | TransactionCase coverage                                                                                                                |
| `openspec/specs/collection-vouchers/spec.md`      | Normative behavior                                                                                                                      |
| `readme/DESCRIPTION.md`                           | Source for generated `README.rst`                                                                                                       |

## Domain rules (do not break)

- **Collection Settings:** stored on `res.company` with related writable
  `res.config.settings`. Menu/action label is **Collection Settings**; keep XMLID
  `collection.action_collection_config_settings`. Fields: `enabled_seller_ids` (M2M
  internal users; empty = none for NEW work), `auto_create_sheet` (default True),
  `allowed_document_type_ids` (catalog M2M), keep `document_review_enabled`,
  `collection_connector_id` (company-scoped active connector). **Import** (Settings
  users) fetches `list_sellers()`, creates/matches users, upserts bindings (including
  overwrite of `commission_percent`), and **replaces** `enabled_seller_ids`. Catalog
  `collection.document.type` has four XMLID rows (`bank_transfer`, `check`,
  `cash_deposit`, `unsupported`); voucher `document_type` stays Selection.
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
  three sequences (`number_next=1` on copies) and unions all four types; new companies
  start with empty enabled sellers. Manifest `19.0.1.34.0`; migrate folders
  `migrations/19.0.1.17.0/` (COL/CS stamp/repair), `migrations/19.0.1.25.0/` (`CA/`
  copy), `migrations/19.0.1.28.0/` (allocation state remap; no `CA/`),
  `migrations/19.0.1.31.0/` (voucher state SQL remap; no snapshot `decision` rewrite),
  `migrations/19.0.1.32.0/` (DROP `residual_reason`; Customer Debt residual), and
  `migrations/19.0.1.33.0/` (unlink reassign XMLID; no sheet-state remap), and
  `migrations/19.0.1.34.0/` (additive; no receipt backfill). Do **not** add
  `collection.allocation` to `COLLECTION_SEQUENCE_CODES` in 1.17.0. Do **not** add
  `migrations/19.0.1.26.0/`, `migrations/19.0.1.27.0/`, `migrations/19.0.1.29.0/`, or
  `migrations/19.0.1.30.0/`. Do **not** add a second 1.31 migrate folder later.
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
- **Sheet lifecycle:** `collection.sheet` `state` is
  `open`/`proposal`/`closed`/`cancelled`; default `open`; Confirm/Close/Cancel/Open.
  Existing `open`/`closed` rows stay on upgrade (no remap). Raw `state` write is
  rejected except via Confirm/Close/Cancel/Open. Sheets inherit `mail.thread` +
  `mail.activity.mixin`; Confirm/Close/Cancel/Open SHOULD be tracked in chatter. Confirm
  runs only from `open` (every member `validated_collections`; empty members pass),
  writes `proposal`, and MUST NOT confirm allocations. `action_close` (from `proposal`)
  dispatches connector `create_receipt` for each draft receipt with ≥1 value **while the
  sheet is still proposal** (context `collection_receipt_issuing` stamps
  `external_receipt_id` + `issued`), then confirms every allocation and closes. Missing
  or failed dispatch MUST raise and roll back Close. Zero receipts / zero-value receipts
  skip dispatch; Close still confirms. Cancel (from `proposal` or `closed`) writes
  `cancelled` and drafts allocations (skip iff mid-flight via
  `collection_allocation_audited_state`, recheck after both writes). Open (from
  `cancelled`) writes `open` and leaves allocations `draft`. Unlink **open** sheets:
  unlink draft allocations first (vouchers unassigned). Unlink **proposal**, **closed**,
  or **cancelled** refused even when empty (`sheet_id` `ondelete="restrict"`). Recon
  inputs (`commission_percent` 0–100, `cash_on_hand`, `commission_withheld`) live on
  `models/collection_sheet_report.py` (second `_inherit`); Closed and Cancelled refuse
  those writes; Proposal remains editable; Open-from-Cancelled keeps stored values.
- **Allocations:** `UNIQUE(sheet_id, partner_id)`. Selection `draft` | `confirmed`;
  default `draft` (`draft` iff sheet `open`/`proposal`/`cancelled`, `confirmed` iff
  sheet `closed`). Drop Validate/Reject. Freeze `line_ids` / `voucher_ids` /
  `receipt_ids` / `partner_id` / `sheet_id` when the sheet is **closed** or
  **cancelled**. Close confirms; Cancel drafts; Confirm does not confirm allocations.
  O2M `Command.DELETE` MUST unassign vouchers. Residual is `total_debt − total_applied`
  (negative allowed) in both `draft` and `confirmed`. Allocation and revision MUST NOT
  persist `residual_reason`. Revisions are immutable, gated by
  `collection_allocation_revision`, `UNIQUE(request_id)`; direct revision unlink stays
  `UserError`; draft parent-unlink uses `collection_allocation_parent_unlink`. Delete
  **draft** even with revisions; refuse **confirmed**. Related stored `currency_id` on
  line/revision; related stored `company_id` required precompute index on
  allocation/line/revision. Line `document_kind` is required Selection
  `invoice`/`quotation` (default `invoice`; `_init_column` backfill). Parent-arch
  `document_kind` immediately before `invoice_number` on the Customer Debt `<list>`
  (MUST NOT rely on inherit). MCP `create_collection_allocation` MAY send
  `document_kind` on `invoices[]`; omitted kind defaults `invoice` on first persist and
  keeps stored kind on amend; payload kind wins when present. Get invoice rows include
  `document_kind`.
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
  Allocation and line: `group_user` `1,1,1,1`. Receipt and value: `group_user`
  `1,1,1,1`. Revision: `group_user` `1,0,1,1` (unlink for cascade; `@api.ondelete` is
  the lock). Never `sudo()`.
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
    `{customer:{external_customer_id,name,identification,customer_code}, summary:{total_balance,overdue_balance,open_balance,invoice_count}, invoices:[{external_invoice_id,number,issue_date,due_date,amount,balance,state,document_kind}]}`
    (no `source`). Payload keys and values unchanged. Outstanding invoices only
    (`balance > 0`, state `open`/`overdue`). MUST NOT create `res.partner` or customer
    bindings. MUST NOT import or open SQLite in this addon.
  - Method-discovered `@mcp_tool` `create_collection_allocation` (`category=write`,
    `registry=mcp`) in `tools/collection_allocation.py`. Required `seller_id`, top-level
    `customer_identification`, `request_id`, `payments[]` (`minItems` 1; items omit
    `customer_identification`; recheck in Python), and `invoices[]` (required; empty =
    on account). Optional ignored `total_debt`, `residual_reason`. Internal caller;
    `_collection_require_internal_seller` then `_assert_new_work` on the write path.
    Fail-closed: `auto_create_sheet` False → named UserError
    `"This company requires a collection sheet chosen in Odoo."` and zero writes. Lazy
    partner via `_collection_create_vouchers` / `resolve_customer_partner` (MAY create
    `res.partner` plus `collection.connector.customer.binding`); identity assert after
    create. Order: form → seller → `request_id` replay → `_assert_new_work` → auto-sheet
    gate → classify `document_id`s (all-new create / exact set reuse continues / else
    generic conflict) → voucher-set gates (all voucher states may allocate) → lock →
    hash (payload applied pairs only; MUST NOT include `residual_reason`) → ERP
    revalidate (expand outstanding zeros; subtract other **draft and confirmed**
    applications) → persist (`state` omitted so default `draft`; revision 1). Optional
    `residual_reason` is enum-checked then ignored. Advisory lock on create
    `(sheet, partner)`; `FOR UPDATE` on amend; amend only while **draft**; PUT voucher
    set MUST be a superset. Identical `request_id` and matching `content_hash` replay
    with zero writes. `UniqueViolation` → `invalidate_all()` → replay or generic
    conflict (no ids). Success:
    `{sheet_id, vouchers:[{id,name,state,document_id}] in submit order, allocation:{id,name,state,revision:int,total_vouchers,total_applied,residual}}`.
    MUST NOT `sudo()`. `_DISPATCH_OPS` includes `create_receipt` (Close uses the company
    active connector; Import still calls `list_sellers()` only). Errors are raised,
    never `{"error":...}`.
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
    existing savepoint. Optional nested `raw_ocr` and `seller_confirmed` (typed
    `_REVIEW_EDITABLE_FIELDS`; nest `document_type` required; no
    `document_id`/attachment/base64). Both nests omitted → empty provenance (UI/ORM
    create still allowed). One-sided, malformed, or seller≠top-level (minus
    `document_id`) → `UserError`, no writes. Parse on the fused create path only, after
    classify and before persist — never inside `_collection_parse_payment_vals`.
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
  including empty vals). No Reject; form `action_validate_seller` does not snapshot.
  Snapshot `decision` stays `approved`/`rejected` (historical `rejected` rows MAY
  remain; those keys are not voucher states). Snapshot ACL: read+gated create
  (`collection_review_snapshot`); write/unlink denied; no `sudo()` / no extra groups;
  **does** use the company `ir.rule`.
- **UI** may omit `document_id`; MCP may not. Seller domain on voucher/sheet views is
  the company enabled list; document-type choices are allowed ∪ current value. Payment
  Vouchers menu is sequence 10 (`view_mode` `list,form`). Stages kanban
  `view_collection_voucher_kanban` is `<delete>`d — do **not** re-add it. Form shows
  non-clickable statusbar and **Validate by Seller** when `draft`; no Reject, no
  Collections button, no History tab (`review_snapshot_ids` unbound). Allocations menu
  is sequence 30 under `menu_collection_root` (after sheets at 20). Collection Receipts
  menu is sequence 40. Receipt views are read-mostly: `state` and `external_receipt_id`
  are form-readonly (ERP Close issues; the form does not). Allocation form notebooks
  Vouchers, Customer Debt, Receipts, and Revisions. Sheet form notebook is Allocations,
  Vouchers, and Debt (`allocation_ids`, `voucher_ids`, `debt_line_ids`); membership is
  via voucher `sheet_id`. Reassign header, kanban XMLID, and partner `group_expand` are
  dropped. Allocation form has no Validate/Reject; freeze fields `readonly` from
  `sheet_id.state`; statusbar `draft,confirmed`; search filters draft+confirmed. Sheet
  statusbar `open,proposal,closed,cancelled` with Confirm/Close/Cancel/Open by state;
  Document Review Open-only. `reviewed_by` / `reviewed_at` stay on the model and leave
  the form. Print → Planilla de Cobranza is bound `qweb-pdf` (`web.external_layout`,
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

| File                                                | Focus                                                                                                                                                                        |
| --------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tests/test_collection_voucher.py`                  | Sequence, defaults `draft`, Validate by Seller, unlink, attachment reopen, new-work helper                                                                                   |
| `tests/test_collection_sheet.py`                    | Sheet lifecycle, Confirm/Close/Cancel/Open, one-open, freeze, auto-assign, open cascade / non-open refuse                                                                    |
| `tests/test_collection_payment.py`                  | Line fields, `document_id` uniqueness                                                                                                                                        |
| `tests/test_collection_acl.py`                      | Internal ACL; required `company_id`; `ir.rule` hide-other-company                                                                                                            |
| `tests/test_collection_allocation.py`               | UNIQUE(sheet, partner); draft default; freeze invert; residual both; draft unlink; revisions                                                                                 |
| `tests/test_collection_allocation_acl.py`           | Allocation/line `1,1,1,1`; revision `1,0,1,1`; company `ir.rule`; no sudo                                                                                                    |
| `tests/test_collection_mail.py`                     | Chatter / tracking on vouchers and sheets                                                                                                                                    |
| `tests/test_collection_ui.py`                       | View arch; Collection Settings; seller domains; Payment Vouchers menu 10; no stages kanban; allocations menu 30; receipts menu 40; Receipts page; form does not issue        |
| `tests/test_collection_document_review.py`          | Queue `validated_seller`+proof; Approve → `validated_collections`; no Reject; snapshots `decision` approved/rejected                                                         |
| `tests/test_collection_company_settings.py`         | Catalog, empty sellers, defaults, Collection Settings fields                                                                                                                 |
| `tests/test_collection_company_migration.py`        | Stamp/repair/seed/four-types; per-company `COL/` `CS/` `CA/`; `19.0.1.28.0` remap; `19.0.1.31.0` voucher remap; manifest `19.0.1.34.0`; keep 1.31–1.33; no 1.26–1.30 migrate |
| `tests/test_collection_allocation_document_kind.py` | Line `document_kind` default/selection/parent-arch `<list>`; MCP omit → `invoice`; get returns kind                                                                          |
| `tests/test_collection_sheet_report_data.py`        | Recon fields, payload primitives, freeze Closed+Cancelled, Proposal editable, four-state PDF payload, mismatch, mixed currency, no sudo                                      |
| `tests/test_collection_sheet_report.py`             | Bound `qweb-pdf` + A4 landscape; HTML names/banner/`t-out`; company-B AccessError                                                                                            |
| `tests/test_collection_sheet_xlsx.py`               | Zip/`A6`/cached SUM; percent/100; `act_url`; XLSX last; four-state download; three notebook pages; no sudo                                                                   |
| `tests/test_collection_mcp_tool.py`                 | MCP attachment + provenance nests on `create_collection_allocation`                                                                                                          |
| `tests/test_collection_mcp_seller_lookup.py`        | MCP `get_seller_id` discovery, match, fail-closed, enabled-list                                                                                                              |
| `tests/test_collection_mcp_customer_list.py`        | MCP `list_collection_customers` auth, routing, normalized payload                                                                                                            |
| `tests/test_collection_mcp_customer_debt.py`        | MCP `customer_debt` auth, routing, outstanding payload, fail-closed                                                                                                          |
| `tests/test_collection_mcp_allocation.py`           | MCP `create_collection_allocation` persist draft, amend iff draft, replay, gates, UniqueViolation                                                                            |
| `tests/test_collection_mcp_allocation_lookup.py`    | MCP `get_collection_allocation` discovery, auth, null, found, `receipts[]`, no-write                                                                                         |
| `tests/test_collection_receipt.py`                  | Receipt uniqueness, values, totals, freeze, issued, Close dispatch, ACL                                                                                                      |
| `tests/test_collection_customer_binding.py`         | Customer binding UNIQUE / ACL `1,0,1,0` / company `ir.rule` / notebook                                                                                                       |
| `tests/test_collection_customer_resolution.py`      | Lazy `resolve_customer_partner`; vat 1/0/>1; nested UniqueViolation                                                                                                          |
| `tests/test_collection_mcp_partner_resolve.py`      | MCP allocation write: lazy resolve, invalid rollback, replay keeps first-call partner                                                                                        |
| `tests/test_collection_seller_sync.py`              | Import create/match/bind, replace-all, fail-closed, idempotent                                                                                                               |
| `tests/test_collection_connector.py`                | Dispatcher allowlist including `create_receipt`; seller-binding uniqueness; `list_customers()` / `get_customer_debt()` / Import `list_sellers()`                             |

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
