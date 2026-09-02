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
  `collection.sheet` (`open`/`closed` grouping per seller; chatter + activities);
  `collection.allocation` (one per `(sheet_id, partner_id)`; `confirmed` / `validated` /
  `rejected`; chatter + activities) plus `collection.allocation.line` and immutable
  `collection.allocation.revision`; `collection.connector` (company-scoped seller
  source); `collection.connector.seller.binding` (1:1 external seller ↔ `res.users`);
  `collection.connector.customer.binding` (1:1 external customer ↔ `res.partner`).
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

| Path                                              | Role                                                                                                                           |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `__manifest__.py`                                 | Module metadata `19.0.1.27.0`; depends `base`, `mail`, `muk_mcp`                                                               |
| `models/res_company.py`                           | Collection Settings fields + `_assert_new_work`; Import sync; seq copy; type seed                                              |
| `models/res_config_settings.py`                   | Related writable Collection Settings + Import action                                                                           |
| `models/collection_connector.py`                  | Company-scoped connector + `_dispatch` allowlist (`list_customers`, `get_customer_debt`)                                       |
| `models/collection_connector_seller_binding.py`   | 1:1 external seller ↔ `res.users`; UNIQUE + related stored `company_id`                                                        |
| `models/collection_connector_customer_binding.py` | 1:1 external customer ↔ `res.partner`; UNIQUE + related stored `company_id`                                                    |
| `models/collection_document_type.py`              | Catalog `code`/`name`; `UNIQUE(code)` Constraint                                                                               |
| `models/collection_voucher.py`                    | Voucher model, sequence on create, approve/reject, unlink guard, provenance copies, `allocation_id`; `partner_id.group_expand` |
| `models/collection_voucher_review_snapshot.py`    | Immutable Document Review snapshots (`UNIQUE(voucher_id, revision)`)                                                           |
| `models/collection_sheet.py`                      | Sheet model, `open`/`closed`, Close/Reopen, one-open, freeze; `allocation_ids`; unlink restrict when allocated                 |
| `models/collection_allocation.py`                 | Allocation header; UNIQUE(sheet, partner); freeze; DELETE sanitizer; residual while confirmed                                  |
| `models/collection_allocation_line.py`            | Invoice snapshot lines; related stored currency/company; CHECK/UNIQUE                                                          |
| `models/collection_allocation_revision.py`        | Immutable revisions; gated create; UNIQUE(`request_id`)                                                                        |
| `tools/collection_voucher.py`                     | Internal `_collection_*` helpers on `muk_mcp.mixin` (not an MCP tool)                                                          |
| `tools/collection_allocation.py`                  | `@mcp_tool` `create_collection_allocation` (write) on `muk_mcp.mixin`                                                          |
| `tools/allocation_lookup.py`                      | `@mcp_tool` `get_collection_allocation` (read) on `muk_mcp.mixin`                                                              |
| `tools/seller_lookup.py`                          | `@mcp_tool` `get_seller_id` (read) on `muk_mcp.mixin`                                                                          |
| `tools/customer_list.py`                          | `@mcp_tool` `list_collection_customers` (read) on `muk_mcp.mixin`                                                              |
| `tools/customer_debt.py`                          | `@mcp_tool` `customer_debt` (read) on `muk_mcp.mixin`                                                                          |
| `views/collection_views.xml`                      | List/search/kanban/form + menus/actions; reassign kanban XMLID; allocations-only notebook + counted Vouchers stat button       |
| `views/collection_allocation_views.xml`           | Allocation list/form/search; `path`; menu sequence 30 after sheets                                                             |
| `views/res_config_settings_views.xml`             | Collection Settings UI; XMLID `action_collection_config_settings`                                                              |
| `data/ir_sequence_data.xml`                       | Per-company seq XMLIDs on `base.main_company` (`COL/` + `CS/` + `CA/`)                                                         |
| `data/collection_document_type_data.xml`          | Four catalog XMLID rows; seed empty company allow-lists                                                                        |
| `security/collection_security.xml`                | Global `ir.rule` `[('company_id', 'in', company_ids)]`                                                                         |
| `security/ir.model.access.csv`                    | Voucher/sheet/allocation/line CRUD; snapshot/revision gated create; catalog read; customer binding `1,0,1,0`                   |
| `migrations/19.0.1.17.0/post-migrate.py`          | Stamp/repair/seed/four-types; per-company `COL/` `CS/` (do not add `CA` here)                                                  |
| `migrations/19.0.1.25.0/post-migrate.py`          | Copy per-company sequences including `CA/` via `_collection_copy_sequences()`                                                  |
| `tests/test_collection_*.py`                      | TransactionCase coverage                                                                                                       |
| `openspec/specs/collection-vouchers/spec.md`      | Normative behavior                                                                                                             |
| `readme/DESCRIPTION.md`                           | Source for generated `README.rst`                                                                                              |

## Domain rules (do not break)

- **Collection Settings:** stored on `res.company` with related writable
  `res.config.settings`. Menu/action label is **Collection Settings**; keep XMLID
  `collection.action_collection_config_settings`. Fields: `enabled_seller_ids` (M2M
  internal users; empty = none for NEW work), `auto_create_sheet` (default True),
  `allowed_document_type_ids` (catalog M2M), keep `document_review_enabled`,
  `collection_connector_id` (company-scoped active connector). **Import** (Settings
  users) fetches `list_sellers()`, creates/matches users, upserts bindings, and
  **replaces** `enabled_seller_ids`. Catalog `collection.document.type` has four XMLID
  rows (`bank_transfer`, `check`, `cash_deposit`, `unsupported`); voucher
  `document_type` stays Selection.
- **New-work helper:** `res.company._assert_new_work(seller, document_type=None)`
  (`@api.private`). Seller is required; seller MUST be in `enabled_seller_ids` (empty
  list rejects); if `document_type` is not None it MUST be an allowed code. Raise
  `UserError`; never `sudo()`. Called on NEW voucher/sheet create and voucher
  `seller_id` / `document_type` write. Skip Approve/Reject/Close/Reopen and same-company
  MCP exact replay. Seller-only voucher write passes `document_type=None` so type is not
  re-checked.
- **Sequence:** per company (never `company_id=False` thief rows). Codes
  `collection.voucher` → `COL/<year>/<number>`, `collection.sheet` →
  `CS/<year>/<number>`, and `collection.allocation` → `CA/<year>/<number>`. Always
  `with_company(record.company_id).next_by_code(...)`. XMLIDs bind to
  `base.main_company` (`seq_collection_allocation`). `res.company.create` copies all
  three sequences (`number_next=1` on copies) and unions all four types; new companies
  start with empty enabled sellers. Manifest `19.0.1.27.0`; migrate folders
  `migrations/19.0.1.17.0/` (COL/CS stamp/repair) and `migrations/19.0.1.25.0/` (`CA/`
  copy). Do **not** add `collection.allocation` to `COLLECTION_SEQUENCE_CODES` in
  1.17.0. Do **not** add `migrations/19.0.1.26.0/` or `migrations/19.0.1.27.0/`.
- **No `received_date`:** registration time is ORM `create_date` only; strip forged
  `create_date` / `write_date` on create; views must not expose `received_date`.
- **States:** voucher `pending` → `approved` | `rejected`. Terminal voucher states are
  immutable. Delete only when voucher `state == 'pending'` **and** `allocation_id` is
  unset (`@api.ondelete`). Write of `allocation_id` only when current and target are
  both `confirmed` or unset. Voucher `partner_id` write injects matching `allocation_id`
  into the same `super().write` vals (confirmed same-sheet attach when residual still
  holds; otherwise unallocated + chatter). Source projected residual `< 0` refuses the
  move. Voucher-side `@api.constrains("partner_id", "allocation_id")`.
- **Sheet lifecycle:** `collection.sheet` `state` is `open` or `closed`; default `open`;
  Close / Reopen actions. Existing rows become `open` on upgrade. Raw `state` write is
  rejected except via Close/Reopen. Sheets inherit `mail.thread` +
  `mail.activity.mixin`; Close/Reopen SHOULD be tracked in chatter. Unlink with no
  allocations still unassigns members (`ondelete="set null"`). Unlink MUST fail when
  allocations exist (`sheet_id` `ondelete="restrict"`).
- **Allocations:** `UNIQUE(sheet_id, partner_id)`. Default `confirmed`; back-office
  Validate/Reject via context `collection_allocation_audited_state`. Freeze `line_ids` /
  `voucher_ids` / `partner_id` / `sheet_id` when not `confirmed`. O2M `Command.DELETE`
  MUST unassign vouchers (copy sheet sanitizer). Residual `>= 0` and `residual_reason`
  when residual `> 0` only while `confirmed` (currency compare). Revisions are
  immutable, gated by `collection_allocation_revision`, `UNIQUE(request_id)`; unlink
  allocation with revisions is refused. Related stored `currency_id` on line/revision;
  related stored `company_id` required precompute index on allocation/line/revision.
- **One-open:** at most one open sheet per `(company_id, seller_id)` on NEW ops only
  (sheet create, Reopen, list Action, auto-assign). Same seller MAY have one open sheet
  in company A and one in B. Leftover `>1` open in that company remains Closeable. No
  UNIQUE SQL. Advisory lock
  `pg_advisory_xact_lock(hashtext('collection.sheet.open.' || company_id), seller_id)`.
- **Closed freeze:** no add/remove/reassign of membership, including voucher
  `partner_id`; voucher `unlink` still unassigns (`ondelete="set null"`). Reuses
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
  binding, customer binding, allocation, line, and revision
  (`security/collection_security.xml`). Catalog is read-only for `base.group_user`.
  Connector/seller binding: `group_user` read, `group_system` write. Customer binding:
  `group_user` `1,0,1,0` (read+create; no write/unlink), `group_system` `1,1,1,1`.
  Allocation and line: `group_user` `1,1,1,1`. Revision: `group_user` `1,0,1,0`. Never
  `sudo()`.
- **Attachment:** optional one image/PDF designated proof per voucher
  (`message_main_attachment_id`, chatter `ir.attachment`, `copy=False` on rotation);
  extras do not steal proof; server validates base64 and detected MIME on MCP nest; omit
  remains valid. Document Review serves `/web/content/{id}` (no Binary
  `field=attachment`).
- **MCP:**
  - `create_collection_vouchers` is **not** an MCP tool. Internal `_collection_*`
    helpers remain on `muk_mcp.mixin` in `tools/collection_voucher.py` and are reused by
    `create_collection_allocation`. They MUST NOT be `@mcp_tool` and MUST NOT have a
    `muk_mcp.tool` row.
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
    `{customer:{external_customer_id,name,identification,customer_code}, summary:{total_balance,overdue_balance,open_balance,invoice_count}, invoices:[{external_invoice_id,number,issue_date,due_date,amount,balance,state}]}`
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
    generic conflict) → voucher-set gates → lock → hash (includes `residual_reason`) →
    ERP revalidate → residual → persist. Advisory lock on create `(sheet, partner)`;
    `FOR UPDATE` on amend; PUT voucher set MUST be a superset. Identical `request_id`
    and matching `content_hash` replay with zero writes. `UniqueViolation` →
    `invalidate_all()` → replay or generic conflict (no ids). Success:
    `{sheet_id, vouchers:[{id,name,state,document_id}] in submit order, allocation:{id,name,state,revision:int,total_vouchers,total_applied,residual}}`.
    MUST NOT `sudo()`. MUST NOT change `_DISPATCH_OPS`. Errors are raised, never
    `{"error":...}`.
  - Method-discovered `@mcp_tool` `get_collection_allocation` (`category=read`,
    `registry=mcp`) in `tools/allocation_lookup.py`. Required `seller_id` and
    `customer_identification`. Internal caller; enabled bound seller. Uses
    `_open_sheets_for_seller` (MUST NOT `_resolve_open_sheet_id_for_create`).
    Binding-only partner lookup (MUST NOT `resolve_customer_partner`). Unbound / no open
    sheet / no allocation → `{allocation: null}`. Multi-open leftover → existing
    multi-open `UserError`. Found →
    `{allocation:{... + residual_reason}, vouchers:[...], invoices:[...]}`. Zero writes.
    Never attachment/`datas`/base64. MUST NOT `sudo()`.
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
  stamp. Snapshots append only from `_write_review_decision` (Document Review approve
  including empty vals, and reject). Form `action_approve`/`action_reject` do not
  snapshot. Snapshot ACL: read+gated create (`collection_review_snapshot`); write/unlink
  denied; no `sudo()` / no extra groups; **does** use the company `ir.rule`.
- **UI** may omit `document_id`; MCP may not. Seller domain on voucher/sheet views is
  the company enabled list; document-type choices are allowed ∪ current value.
  Allocations menu is sequence 30 under `menu_collection_root` (after sheets at 20).
  Sheet form notebook is Allocations-only (`allocation_ids`) plus a counted Vouchers
  stat button; membership is via voucher `sheet_id`. Open-sheet header **Reassign
  Customers** follows Document Review (`invisible="not id or state != 'open'"`) and
  opens `view_collection_voucher_reassign_kanban` grouped by Customer. `partner_id` uses
  `group_expand="_read_group_partner_ids"` (method, not `True`); identity unless
  readable context `collection_reassign_sheet_id`. Do **not** edit
  `view_collection_voucher_kanban`. Allocation form Validate/Reject are header object
  buttons gated `state != 'confirmed'`, same pattern as voucher Approve/Reject.
- **Odoo 19:** use `<list>` not `<tree>`; `models.Constraint` not `_sql_constraints`;
  `t-out` not `t-esc`; `@api.ondelete` for delete rules.

## Testing instructions

On an already-installed devel DB, default `invoke test -m collection` (`mode=init`)
reports **0 tests**. Use update mode:

```bash
invoke test -m collection --mode=update
invoke test -m collection --mode=update -d devel
```

| File                                             | Focus                                                                                                                        |
| ------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------- |
| `tests/test_collection_voucher.py`               | Sequence, defaults, state transitions, unlink, new-work helper                                                               |
| `tests/test_collection_sheet.py`                 | Sheet lifecycle, one-open `(company, seller)`, freeze, auto-assign gate, unlink empty vs allocated                           |
| `tests/test_collection_payment.py`               | Line fields, `document_id` uniqueness                                                                                        |
| `tests/test_collection_acl.py`                   | Internal ACL; required `company_id`; `ir.rule` hide-other-company                                                            |
| `tests/test_collection_allocation.py`            | UNIQUE(sheet, partner); freeze; DELETE sanitizer; residual; validate/reject; revisions                                       |
| `tests/test_collection_allocation_acl.py`        | Allocation/line `1,1,1,1`; revision `1,0,1,0`; company `ir.rule`; no sudo                                                    |
| `tests/test_collection_mail.py`                  | Chatter / tracking on vouchers and sheets                                                                                    |
| `tests/test_collection_ui.py`                    | View arch; Collection Settings; seller domains; allocations menu 30; sheet notebook; reassign kanban; partner `group_expand` |
| `tests/test_collection_document_review.py`       | Queue on designated proof; `/web/content/{id}`; snapshots                                                                    |
| `tests/test_collection_company_settings.py`      | Catalog, empty sellers, defaults, Collection Settings fields                                                                 |
| `tests/test_collection_company_migration.py`     | Stamp/repair/seed/four-types; per-company `COL/` `CS/` `CA/`; manifest `19.0.1.27.0`                                         |
| `tests/test_collection_mcp_tool.py`              | MCP attachment + provenance nests on `create_collection_allocation`                                                          |
| `tests/test_collection_mcp_seller_lookup.py`     | MCP `get_seller_id` discovery, match, fail-closed, enabled-list                                                              |
| `tests/test_collection_mcp_customer_list.py`     | MCP `list_collection_customers` auth, routing, normalized payload                                                            |
| `tests/test_collection_mcp_customer_debt.py`     | MCP `customer_debt` auth, routing, outstanding payload, fail-closed                                                          |
| `tests/test_collection_mcp_allocation.py`        | MCP `create_collection_allocation` inline payments, replay, amend, gates, UniqueViolation                                    |
| `tests/test_collection_mcp_allocation_lookup.py` | MCP `get_collection_allocation` discovery, auth, null, found, no-write                                                       |
| `tests/test_collection_customer_binding.py`      | Customer binding UNIQUE / ACL `1,0,1,0` / company `ir.rule` / notebook                                                       |
| `tests/test_collection_customer_resolution.py`   | Lazy `resolve_customer_partner`; vat 1/0/>1; nested UniqueViolation                                                          |
| `tests/test_collection_mcp_partner_resolve.py`   | MCP allocation write: lazy resolve, invalid rollback, replay keeps first-call partner                                        |
| `tests/test_collection_seller_sync.py`           | Import create/match/bind, replace-all, fail-closed, idempotent                                                               |
| `tests/test_collection_connector.py`             | Dispatcher allowlist; seller-binding uniqueness; `list_customers()` / `get_customer_debt()`                                  |

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
