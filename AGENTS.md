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
  (`open`/`closed` grouping per seller).
- **Integrations:** `mail.thread` / activities; MuK MCP tools on `muk_mcp.mixin`: write
  `create_collection_vouchers` and read `get_seller_id`. Coordinated Nebula first-party
  tool `register_latest_collection_voucher` lives in
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

| Path                                         | Role                                                            |
| -------------------------------------------- | --------------------------------------------------------------- |
| `__manifest__.py`                            | Module metadata; depends `base`, `mail`, `muk_mcp`              |
| `models/collection_voucher.py`               | Voucher model, sequence on create, approve/reject, unlink guard |
| `models/collection_sheet.py`                 | Sheet model, `open`/`closed`, Close/Reopen, one-open, freeze    |
| `tools/collection_voucher.py`                | `@mcp_tool` `create_collection_vouchers` on `muk_mcp.mixin`     |
| `tools/seller_lookup.py`                     | `@mcp_tool` `get_seller_id` (read) on `muk_mcp.mixin`           |
| `views/collection_views.xml`                 | List/search/kanban/form + menus/actions                         |
| `data/ir_sequence_data.xml`                  | Sequence `collection.voucher` → `COL/%(year)s/`                 |
| `security/ir.model.access.csv`               | Full CRUD for `base.group_user` only                            |
| `tests/test_collection_*.py`                 | TransactionCase coverage                                        |
| `openspec/specs/collection-vouchers/spec.md` | Normative behavior                                              |
| `readme/DESCRIPTION.md`                      | Source for generated `README.rst`                               |

## Domain rules (do not break)

- **Sequence:** new vouchers get `COL/<year>/<number>` via `ir.sequence` code
  `collection.voucher`.
- **No `received_date`:** registration time is ORM `create_date` only; strip forged
  `create_date` / `write_date` on create; views must not expose `received_date`.
- **States:** voucher `pending` → `approved` | `rejected`. Terminal voucher states are
  immutable. Delete only when voucher `state == 'pending'` (`@api.ondelete`).
- **Sheet lifecycle:** `collection.sheet` `state` is `open` or `closed`; default `open`;
  Close / Reopen actions. Existing rows become `open` on upgrade. Raw `state` write is
  rejected except via Close/Reopen.
- **One-open:** at most one open sheet per seller on NEW ops only (sheet create, Reopen,
  list Action, auto-assign). Leftover `>1` open remains Closeable. No UNIQUE SQL.
- **Closed freeze:** no add/remove/reassign of membership; voucher `unlink` still
  unassigns (`ondelete="set null"`).
- **Auto-assign:** ORM `voucher.create` assigns when `seller_id` is set and `sheet_id`
  is omitted (0 create open / 1 use / `>1` UserError). Null seller stays unassigned.
  Later `seller_id` write does not assign.
- **List Action:** still create-new-sheet; reject if the seller has any open sheet.
- **Currency:** company default; no multi-currency UX.
- **ACL:** internal users only; no extra groups or record rules.
- **Attachment:** optional one image/PDF designated proof per voucher
  (`message_main_attachment_id`, chatter `ir.attachment`, `copy=False` on rotation);
  extras do not steal proof; server validates base64 and detected MIME on MCP nest;
  omit remains valid. Document Review serves `/web/content/{id}` (no Binary
  `field=attachment`).
- **MCP:**
  - Method-discovered `@mcp_tool` `create_collection_vouchers` (`category=write`,
    `registry=mcp`).
  - Method-discovered `@mcp_tool` `get_seller_id` (`category=read`, `registry=mcp`) in
    `tools/seller_lookup.py`. Required `mobile` (WhatsApp/mobile string; **no
    connector** in this addon). Unique internal match → `{seller_id}` only. Does not
    write vouchers, fill invoke context, or replace write-tool connector `seller_id`.
  - **Never** `sudo()`; never add a DB `muk_mcp.tool` record for these tools.
  - Require `customer_identification` + non-empty `payments`.
  - Each MCP payment requires non-empty `document_id` and `document_type`.
  - Optional nested `attachment` per payment (`name`, `mimetype`, base64 `datas`);
    validate MIME vs content; create atomically inside the existing savepoint.
  - One voucher per payment. Response `{vouchers:[{id,name,state,document_id},...]}` (no
    `sheet_id`).
  - All-new create inherits ORM auto-assign (`seller_id` set, `sheet_id` omitted).
  - Idempotency: all-new → create N; exact set → replay ALL vouchers; in-call duplicate
    / partial overlap → `UserError`, no writes. Docs on different vouchers succeed as
    exact replay.
  - Exact-retry replay MUST NOT add, replace, or compare attachments, and MUST NOT
    attach or mutate sheets.
  - Handle `UniqueViolation` races with invalidate + replay/reject.
- **UI** may omit `document_id`; MCP may not.
- **Odoo 19:** use `<list>` not `<tree>`; `models.Constraint` not `_sql_constraints`;
  `t-out` not `t-esc`; `@api.ondelete` for delete rules.

## Testing instructions

```bash
invoke test -m collection
invoke test -m collection -d devel
```

| File                                         | Focus                                                  |
| -------------------------------------------- | ------------------------------------------------------ |
| `tests/test_collection_voucher.py`           | Sequence, defaults, state transitions, unlink          |
| `tests/test_collection_sheet.py`             | Sheet lifecycle, one-open, freeze, auto-assign         |
| `tests/test_collection_payment.py`           | Line fields, `document_id` uniqueness                  |
| `tests/test_collection_acl.py`               | Internal vs non-internal access                        |
| `tests/test_collection_mail.py`              | Chatter / tracking                                     |
| `tests/test_collection_ui.py`                | View arch; sheet statusbar, Close/Reopen, freeze       |
| `tests/test_collection_document_review.py`   | Queue on designated proof; `/web/content/{id}`         |
| `tests/test_collection_mcp_tool.py`          | MCP create, replay, inherit auto-assign, no `sheet_id` |
| `tests/test_collection_mcp_seller_lookup.py` | MCP `get_seller_id` discovery, match, fail-closed      |

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
- Required locally: scoped pre-commit + `invoke test -m collection`.
- Link or update OpenSpec when requirements change; archive completed changes under
  `openspec/changes/archive/`.

## Troubleshooting

| Symptom                              | Likely cause                                                      |
| ------------------------------------ | ----------------------------------------------------------------- |
| MCP tool missing                     | `muk_mcp` not installed / mixin not loaded; confirm               |
| `tools/` imported from `__init__.py` |
| Access denied on MCP create          | Caller not in `base.group_user` or missing ACL                    |
| Duplicate document errors            | `UNIQUE(document_id)` or idempotency conflict rules               |
| Sequence stuck at `/`                | Sequence `collection.voucher` missing; reinstall/upgrade data     |
| UI still shows old fields            | Forgot `-u collection` upgrade                                    |
| Edits “disappear”                    | Wrong container project name; use `seedian-odoo-1` from repo root |

## Additional notes

- Parent agents must not edit `odoo/custom/src/odoo/` or `OCA/` for this feature;
  declare deps via git-aggregate if needed.
- Prefer extending `tools/collection_voucher.py` helpers (`_collection_*`) over
  duplicating idempotency logic elsewhere.
