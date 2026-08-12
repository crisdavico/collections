# AGENTS.md — collection

Agent operating manual for the **Collections** Odoo addon. Human docs:
[README.md](README.md). Parent Doodba context:
[seedian/AGENTS.md](../../../../../AGENTS.md).

Ground truth order: source under this directory →
`openspec/specs/collection-vouchers/spec.md` → this file → parent AGENTS.md.

## Project overview

- **What:** Manual payment vouchers for company sellers (cobranzas).
- **Stack:** Odoo 19, PostgreSQL 17, Doodba (`seedian` compose project).
- **Models:** `collection.voucher`, `collection.voucher.line`.
- **Integrations:** `mail.thread` / activities; MuK MCP tool `create_collection_voucher`
  on `muk_mcp.mixin`.
- **Attachments (in scope):** each `collection.voucher.line` MAY have one optional image
  or PDF (`fields.Binary` + filename via `ir.attachment`). See OpenSpec change
  `voucher-line-attachments` and `openspec/specs/collection-vouchers/spec.md`.
- **Out of scope (do not invent):** WhatsApp, HTTP public API, partner/CRM linkage,
  multi-file or non-image/non-PDF attachments, multi-currency UX, agent LLM code inside
  this addon.

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
| `models/collection_voucher.py`               | Header model, sequence on create, validate/reject, unlink guard |
| `models/collection_voucher_line.py`          | Payment lines + `UNIQUE(document_id)` constraint                |
| `tools/collection_voucher.py`                | `@mcp_tool` `create_collection_voucher` on `muk_mcp.mixin`      |
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
- **States:** voucher `new` → `validated` | `rejected`. Terminal voucher states are
  immutable. Delete only when voucher `state == 'new'` (`@api.ondelete`). Payment line
  `state` is `pending` | `approved` | `rejected` (default `pending`).
- **Currency:** company default; no multi-currency UX.
- **ACL:** internal users only; no extra groups or record rules.
- **Line attachment:** optional one image/PDF per line (`Binary` + filename,
  `attachment=True`, `copy=False`); server validates base64 and detected MIME; omit
  remains valid.
- **MCP:**
  - Method-discovered `@mcp_tool` (`category=write`, `registry=mcp`).
  - **Never** `sudo()`; never add a DB `muk_mcp.tool` record for this.
  - Require `customer_identification` + non-empty `payments`.
  - Each MCP payment requires non-empty `document_id` and `document_type`.
  - Optional nested `attachment` per payment (`name`, `mimetype`, base64 `datas`);
    validate MIME vs content; create atomically inside the existing savepoint.
  - Idempotency: all-new → create; full same-voucher match → replay; in-call duplicate /
    partial / cross-voucher → `UserError`, no writes.
  - Exact-retry replay MUST NOT add, replace, or compare line attachments.
  - Handle `UniqueViolation` races with invalidate + replay/reject.
- **UI lines** may omit `document_id`; MCP may not.
- **Odoo 19:** use `<list>` not `<tree>`; `models.Constraint` not `_sql_constraints`;
  `t-out` not `t-esc`; `@api.ondelete` for delete rules.

## Testing instructions

```bash
invoke test -m collection
invoke test -m collection -d devel
```

| File                                | Focus                                         |
| ----------------------------------- | --------------------------------------------- |
| `tests/test_collection_voucher.py`  | Sequence, defaults, state transitions, unlink |
| `tests/test_collection_payment.py`  | Line fields, `document_id` uniqueness         |
| `tests/test_collection_acl.py`      | Internal vs non-internal access               |
| `tests/test_collection_mail.py`     | Chatter / tracking                            |
| `tests/test_collection_ui.py`       | View arch expectations                        |
| `tests/test_collection_mcp_tool.py` | MCP create, replay, conflicts, ACL            |

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
