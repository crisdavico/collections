# AGENTS.md — collection

Agent operating manual for the **Collections** Odoo addon. Human docs:
[README.md](README.md). Parent Doodba context:
[seedian/AGENTS.md](../../../../../AGENTS.md).

Ground truth order: source under this directory →
`openspec/specs/collection-vouchers/spec.md` → this file → parent AGENTS.md.

## Project overview

- **What:** Manual payment vouchers for company sellers (cobranzas).
- **Stack:** Odoo 19, PostgreSQL 17, Doodba (`seedian` compose project).
- **Models:** `collection.voucher` (standalone per payment); `collection.sheet`
  (`open`/`closed` grouping per seller; chatter + activities).
- **Integrations:** `mail.thread` / activities on vouchers and sheets; MuK MCP tools on
  `muk_mcp.mixin`: write `create_collection_vouchers` and read `get_seller_id`.
  Coordinated Nebula first-party tool `register_latest_collection_voucher` lives in
  `/home/crisd/projects/nebula/nebula-agent`.
- **Attachments (in scope):** each `collection.voucher` MAY have one optional image or
  PDF designated proof (`message_main_attachment_id` via chatter / `ir.attachment`).
  There is no Binary `attachment` field.
- **Out of scope (do not invent):** WhatsApp connector inside this addon (MCP `mobile`
  argument **is allowed**), HTTP public API, partner/CRM linkage, multi-file or
  non-image/non-PDF attachments, multi-currency UX, agent LLM code inside this addon.

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

| Path                                           | Role                                                                               |
| ---------------------------------------------- | ---------------------------------------------------------------------------------- |
| `__manifest__.py`                              | Module metadata `19.0.1.17.0`; depends `base`, `mail`, `muk_mcp`                   |
| `models/res_company.py`                        | Collection Settings fields + `_assert_new_work`; seq copy; type seed               |
| `models/res_config_settings.py`                | Related writable Collection Settings                                               |
| `models/collection_document_type.py`           | Catalog `code`/`name`; `UNIQUE(code)` Constraint                                   |
| `models/collection_voucher.py`                 | Voucher model, sequence on create, approve/reject, unlink guard, provenance copies |
| `models/collection_voucher_review_snapshot.py` | Immutable Document Review snapshots (`UNIQUE(voucher_id, revision)`)               |
| `models/collection_sheet.py`                   | Sheet model, `open`/`closed`, Close/Reopen, one-open, freeze                       |
| `tools/collection_voucher.py`                  | `@mcp_tool` `create_collection_vouchers` on `muk_mcp.mixin`                        |
| `tools/seller_lookup.py`                       | `@mcp_tool` `get_seller_id` (read) on `muk_mcp.mixin`                              |
| `views/collection_views.xml`                   | List/search/kanban/form + menus/actions                                            |
| `views/res_config_settings_views.xml`          | Collection Settings UI; XMLID `action_collection_config_settings`                  |
| `data/ir_sequence_data.xml`                    | Per-company seq XMLIDs on `base.main_company` (`COL/` + `CS/`)                     |
| `data/collection_document_type_data.xml`       | Four catalog XMLID rows; seed empty company allow-lists                            |
| `security/collection_security.xml`             | Global `ir.rule` `[('company_id', 'in', company_ids)]`                             |
| `security/ir.model.access.csv`                 | Voucher/sheet CRUD; snapshot gated create; catalog read                            |
| `migrations/19.0.1.17.0/post-migrate.py`       | Stamp/repair/seed/four-types; per-company sequences                                |
| `tests/test_collection_*.py`                   | TransactionCase coverage                                                           |
| `openspec/specs/collection-vouchers/spec.md`   | Normative behavior                                                                 |
| `readme/DESCRIPTION.md`                        | Source for generated `README.rst`                                                  |

## Domain rules (do not break)

- **Collection Settings:** stored on `res.company` with related writable
  `res.config.settings`. Menu/action label is **Collection Settings**; keep XMLID
  `collection.action_collection_config_settings`. Fields: `enabled_seller_ids` (M2M
  internal users; empty = none for NEW work), `auto_create_sheet` (default True),
  `allowed_document_type_ids` (catalog M2M), keep `document_review_enabled`. Catalog
  `collection.document.type` has four XMLID rows (`bank_transfer`, `check`,
  `cash_deposit`, `unsupported`); voucher `document_type` stays Selection.
- **New-work helper:** `res.company._assert_new_work(seller, document_type=None)`
  (`@api.private`). Seller is required; seller MUST be in `enabled_seller_ids` (empty
  list rejects); if `document_type` is not None it MUST be an allowed code. Raise
  `UserError`; never `sudo()`. Called on NEW voucher/sheet create and voucher
  `seller_id` / `document_type` write. Skip Approve/Reject/Close/Reopen and same-company
  MCP exact replay. Seller-only voucher write passes `document_type=None` so type is not
  re-checked.
- **Sequence:** per company (never `company_id=False` thief rows). Codes
  `collection.voucher` → `COL/<year>/<number>` and `collection.sheet` →
  `CS/<year>/<number>`. Always `with_company(record.company_id).next_by_code(...)`.
  XMLIDs bind to `base.main_company`. `res.company.create` copies both sequences
  (`number_next=1` on copies) and unions all four types; new companies start with empty
  enabled sellers. Manifest `19.0.1.17.0`; migrate folder `migrations/19.0.1.17.0/`.
- **No `received_date`:** registration time is ORM `create_date` only; strip forged
  `create_date` / `write_date` on create; views must not expose `received_date`.
- **States:** voucher `pending` → `approved` | `rejected`. Terminal voucher states are
  immutable. Delete only when voucher `state == 'pending'` (`@api.ondelete`).
- **Sheet lifecycle:** `collection.sheet` `state` is `open` or `closed`; default `open`;
  Close / Reopen actions. Existing rows become `open` on upgrade. Raw `state` write is
  rejected except via Close/Reopen. Sheets inherit `mail.thread` +
  `mail.activity.mixin`; Close/Reopen SHOULD be tracked in chatter.
- **One-open:** at most one open sheet per `(company_id, seller_id)` on NEW ops only
  (sheet create, Reopen, list Action, auto-assign). Same seller MAY have one open sheet
  in company A and one in B. Leftover `>1` open in that company remains Closeable. No
  UNIQUE SQL. Advisory lock
  `pg_advisory_xact_lock(hashtext('collection.sheet.open.' || company_id), seller_id)`.
- **Closed freeze:** no add/remove/reassign of membership; voucher `unlink` still
  unassigns (`ondelete="set null"`).
- **Auto-assign:** ORM `voucher.create` assigns only when company `auto_create_sheet` is
  ON, `seller_id` is set, and `sheet_id` is omitted (0 create open in that company / 1
  use / `>1` UserError). OFF skips create **and** assign (voucher stays unassigned).
  Later `seller_id` write does not assign. Auto-created sheets stamp the voucher
  company.
- **List Action:** still create-new-sheet even when auto is OFF; reject if that seller
  already has an open sheet **in the selection company**; selection must be one company;
  sheet gets that company. Helper still runs via `sheet.create`.
- **Currency:** company default; no multi-currency UX.
- **ACL:** internal users only (`base.group_user`); no extra groups. Required
  `company_id` (default `env.company`) on voucher/sheet; snapshot related stored
  `company_id` from `voucher_id.company_id` (`required=True`, `precompute=True`). Global
  `ir.rule` `[('company_id', 'in', company_ids)]` on voucher, sheet, and snapshot
  (`security/collection_security.xml`). Catalog is read-only for `base.group_user`.
  Never `sudo()`.
- **Attachment:** optional one image/PDF designated proof per voucher
  (`message_main_attachment_id`, chatter `ir.attachment`, `copy=False` on rotation);
  extras do not steal proof; server validates base64 and detected MIME on MCP nest; omit
  remains valid. Document Review serves `/web/content/{id}` (no Binary
  `field=attachment`).
- **MCP:**
  - Method-discovered `@mcp_tool` `create_collection_vouchers` (`category=write`,
    `registry=mcp`).
  - Method-discovered `@mcp_tool` `get_seller_id` (`category=read`, `registry=mcp`) in
    `tools/seller_lookup.py`. Required `mobile` (WhatsApp/mobile string; **no
    connector** in this addon). Unique internal match → `{seller_id}` only.
    **Unfiltered** (no enabled-seller or company allow-list). Does not write vouchers,
    fill invoke context, or replace write-tool connector `seller_id`. Leave
    `seller_lookup.py` unchanged unless a later change explicitly filters it.
  - **Never** `sudo()`; never add a DB `muk_mcp.tool` record for these tools.
  - Require `customer_identification` + non-empty `payments`.
  - Each MCP payment requires non-empty `document_id` and `document_type`.
  - Optional nested `attachment` per payment (`name`, `mimetype`, base64 `datas`);
    validate MIME vs content; create atomically inside the existing savepoint.
  - Optional nested `raw_ocr` and `seller_confirmed` (typed `_REVIEW_EDITABLE_FIELDS`;
    nest `document_type` required; no `document_id`/attachment/base64). Both nests
    omitted → empty provenance (UI/ORM create still allowed). One-sided, malformed, or
    seller≠top-level (minus `document_id`) → `UserError`, no writes. Seller-confirmed
    MUST equal top-level; current initializes from seller; raw persists as submitted.
    Parse on the create path only, after the existing-document check and before the
    savepoint — never inside `_collection_parse_payment_vals`.
  - One voucher per payment. Response `{vouchers:[{id,name,state,document_id},...]}` (no
    `sheet_id`).
  - All-new create inherits ORM helper + auto-assign (`seller_id` set, `sheet_id`
    omitted). Stamp `env.company`.
  - Idempotency: all-new → create N; **same-company** exact set → replay ALL vouchers
    (skip seller/type/sheet/nests, including disabled seller or disallowed type);
    visible other-company hit → generic `UserError` (no id/name); in-call duplicate /
    same-company partial overlap → `UserError`, no writes. Docs on different vouchers
    **in the same company** succeed as exact replay. Multi-company readers who can see
    company B still MUST NOT replay B when creating in A.
  - Exact-retry replay MUST NOT add, replace, or compare attachments, MUST NOT attach or
    mutate sheets, and MUST ignore provenance nests (no backfill).
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
- **Odoo 19:** use `<list>` not `<tree>`; `models.Constraint` not `_sql_constraints`;
  `t-out` not `t-esc`; `@api.ondelete` for delete rules.

## Testing instructions

On an already-installed devel DB, default `invoke test -m collection` (`mode=init`)
reports **0 tests**. Use update mode:

```bash
invoke test -m collection --mode=update
invoke test -m collection --mode=update -d devel
```

| File                                         | Focus                                                                   |
| -------------------------------------------- | ----------------------------------------------------------------------- |
| `tests/test_collection_voucher.py`           | Sequence, defaults, state transitions, unlink, new-work helper          |
| `tests/test_collection_sheet.py`             | Sheet lifecycle, one-open `(company, seller)`, freeze, auto-assign gate |
| `tests/test_collection_payment.py`           | Line fields, `document_id` uniqueness                                   |
| `tests/test_collection_acl.py`               | Internal ACL; required `company_id`; `ir.rule` hide-other-company       |
| `tests/test_collection_mail.py`              | Chatter / tracking on vouchers and sheets                               |
| `tests/test_collection_ui.py`                | View arch; Collection Settings labels; seller domains                   |
| `tests/test_collection_document_review.py`   | Queue on designated proof; `/web/content/{id}`; snapshots               |
| `tests/test_collection_company_settings.py`  | Catalog, empty sellers, defaults, Collection Settings fields            |
| `tests/test_collection_company_migration.py` | Stamp/repair/seed/four-types; per-company `COL/` `CS/`                  |
| `tests/test_collection_mcp_tool.py`          | MCP create, same-company replay, other-company reject, provenance nests |
| `tests/test_collection_mcp_seller_lookup.py` | MCP `get_seller_id` discovery, match, fail-closed, unfiltered           |

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

| Symptom                     | Likely cause                                                        |
| --------------------------- | ------------------------------------------------------------------- |
| MCP tool missing            | `muk_mcp` not installed / mixin not loaded; confirm `tools/` import |
| Access denied on MCP create | Caller not in `base.group_user`, missing ACL, or company `ir.rule`  |
| Duplicate document errors   | Global `UNIQUE(document_id)` or company-scoped idempotency          |
| Other-company MCP replay    | Classifier rejects visible other-company / hidden UniqueViolation   |
| Sequence stuck at `/`       | Per-company `collection.voucher` / `collection.sheet` missing       |
| UI still shows old fields   | Forgot `-u collection` upgrade                                      |
| Edits “disappear”           | Wrong container project name; use `seedian-odoo-1` from repo root   |

## Additional notes

- Parent agents must not edit `odoo/custom/src/odoo/` or `OCA/` for this feature;
  declare deps via git-aggregate if needed.
- Prefer extending `tools/collection_voucher.py` helpers (`_collection_*`) over
  duplicating idempotency logic elsewhere.
