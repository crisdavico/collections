## Exploration: collection-sheets

### Current State

`collection.voucher` is a standalone one-payment model (`mail.thread` + activities).
There is no grouping container, no `seller_id`, and no list Action binding. Sequence
`collection.voucher` assigns `COL/%(year)s/` with padding 4 and `company_id=False` on
create; callers cannot forge `create_date`. Ownership today is only
`reviewed_by = Many2one("res.users")` (nullable, no domain). SQL uses Odoo 19
`models.Constraint`; `UNIQUE(document_id)` already allows multiple NULLs (PostgreSQL),
proven in `test_collection_payment.py`. ACL is a single `ir.model.access.csv` row: full
CRUD for `base.group_user`, no extra groups or record rules.

MCP `create_collection_vouchers` on `muk_mcp.mixin` requires `customer_identification` +
non-empty `payments`. Flow: parse → in-call duplicate reject → lookup by `document_id` →
exact set replay (ignore customer and attachments, no writes) / partial conflict reject
/ all-new savepoint create. Never `sudo()`. Schema tests assert required keys are only
those two fields.

UI is Collections → Payment Vouchers (kanban/list/form). No wizards, no
`ir.actions.server`, no `collection.sheet`. Manifest version `19.0.1.9.0`. OpenSpec
archive under this addon is empty (only `.gitkeep`); patterns live in
`openspec/specs/collection-vouchers/spec.md` and `AGENTS.md`.

Nebula `register_latest_collection_voucher` currently posts
`{customer_identification, payments}` only. `ContextSchema` has `phone` and no seller.
That consumer is **out of scope** for this change; after MCP requires `seller_id`,
Nebula creates will fail until a follow-up.

### Affected Areas

- `models/collection_voucher.py` — add nullable `seller_id`, `sheet_id`; same-seller /
  assignability constraints; keep lifecycle unchanged
- `models/collection_sheet.py` (new) — sequence-named container, required `seller_id`,
  inverse `voucher_ids`, stored `date_from`/`date_to`, no `state`
- `models/__init__.py` — import the new model
- `data/ir_sequence_data.xml` — add `collection.sheet` sequence `CS/%(year)s/`
- `security/ir.model.access.csv` — one `base.group_user` CRUD row for `collection.sheet`
- `views/collection_views.xml` — voucher `seller_id`/`sheet_id`; sheet
  list/form/search/menu; list Action to create a sheet
- `tools/collection_voucher.py` — top-level required `seller_id`; validate internal
  user; apply only on all-new create; replay unchanged
- `__manifest__.py` — data file list if a dedicated sheet view XML is split; bump
  version in apply
- `tests/test_collection_mcp_tool.py` — schema required `seller_id`; persist on create;
  replay must not mutate legacy `seller_id`
- `tests/test_collection_ui.py` — voucher seller widgets; sheet menu/views; Action
  binding
- `tests/test_collection_acl.py` — sheet CRUD for internal vs portal
- `tests/test_collection_voucher.py` / new `tests/test_collection_sheet.py` — nullable
  legacy seller, sheet create/membership/dates/unlink
- `openspec/specs/collection-vouchers/spec.md` — MODIFIED MCP + voucher UI/fields; ADDED
  sheet domain (later phases)
- Coordinated consumer (do not implement):
  `/home/crisd/projects/nebula/nebula-agent/src/agent/tools/collection_voucher.py`

Not in this change: Document Review OWL, voucher workflow, attachments, `received_date`,
extra groups, Nebula runtime context.

### Approaches

1. **Membership: Many2one `sheet_id` on voucher vs Many2many**

   - **Many2one `sheet_id` + inverse One2many `voucher_ids`** — one sheet per voucher is
     the FK. `ondelete="set null"` unassigns on sheet delete. Editable membership is
     writing `sheet_id` / `voucher_ids`.
     - Pros: matches “one sheet per voucher”; no join table; delete-unassign is native;
       lowest coupling
     - Cons: moving a voucher between sheets is a write, not a dual membership (desired)
     - Effort: Low
   - **Many2many** — needs a uniqueness constraint to fake 1:N and custom unlink to
     unassign.
     - Pros: none for this product
     - Cons: extra table, easy to violate one-sheet, higher coupling
     - Effort: Medium
   - **Recommend Many2one.**

2. **Same-seller + one-sheet: Python constraint vs SQL Constraint vs both**

   - **Python `@api.constrains` on voucher `sheet_id`/`seller_id`** — assigned voucher
     MUST have `seller_id`; MUST equal `sheet.seller_id`; unassigned NULL seller remains
     legal. Sheet `seller_id` is `required=True` (no legacy sheets).
     - Pros: clear UserError; can see related records; Odoo-idiomatic for cross-table
       rules
     - Cons: not enforced if SQL is used behind the ORM
     - Effort: Low
   - **SQL `models.Constraint` only** — one-sheet is already the Many2one. Same-seller
     is cross-table; CHECK cannot see `collection_sheet.seller_id` without a trigger.
     - Pros: DB-hard for simple CHECKs
     - Cons: cannot express same-seller without non-Odoo triggers
     - Effort: High if triggers
   - **Both** — Python for messages + optional SQL CHECK that assigned rows have
     non-null `seller_id` (`CHECK(sheet_id IS NULL OR seller_id IS NOT NULL)`).
     - Pros: cheap extra guard for the assignability half
     - Cons: still need Python for seller match
     - Effort: Low–Medium
   - **Recommend Python constraints + optional SQL CHECK for assigned ⇒ seller present.
     Do not add DB triggers.** One-sheet is the Many2one; do not add `UNIQUE(sheet_id)`
     (that would allow only one voucher per sheet).

3. **Create sheet from multi-select: server action vs wizard vs object method only**

   - **`ir.actions.server` bound to `collection.voucher` list
     (`binding_view_types=list`)** calling `action_create_collection_sheet()` —
     validate: non-empty selection, every voucher has `seller_id`, all same seller, all
     `sheet_id` empty, any `state` allowed; create sheet with that `seller_id`; assign
     members; return form of the new sheet.
     - Pros: no extra model; matches “Action over unassigned same-seller vouchers”; Odoo
       19 Action menu pattern
     - Cons: no extra prompt (none required; name is sequenced)
     - Effort: Low
   - **Transient wizard** — only useful if the user must pick extra fields.
     - Pros: confirmation UI
     - Cons: extra model/ACL/views for no product field
     - Effort: Medium
   - **Unbound object method** — callable from tests but hidden from list Action.
     - Pros: smallest XML
     - Cons: misses the approved UI
     - Effort: Low
   - **Recommend bound `ir.actions.server` + method on `collection.voucher`. No
     wizard.**

4. **Nullable legacy `seller_id` vs required new creates**

   - **ORM field `required=False` (SQL NULL) + view `required="1"` + MCP request
     required** — same split as `document_id` (UI omit allowed there; MCP required).
     Existing rows stay NULL; no backfill; no `NOT NULL` migration.
     - Pros: upgrade-safe; UI/MCP gates new work; RPC/tests can still create
       legacy-shaped rows
     - Cons: ORM create without seller still possible (allowed by product for
       existing-style rows)
     - Effort: Low
   - **Field `required=True`** — PostgreSQL `NOT NULL` fails on existing NULL vouchers.
     - Pros: hard required
     - Cons: contradicts “existing remain nullable, not backfilled”
     - Effort: High (forced backfill)
   - **Recommend nullable ORM field; require in voucher form/new UI and MCP all-new
     path. Domain `[('share', '=', False)]`. Sheet `seller_id` MAY be `required=True`
     (no legacy sheets). Do not copy `create_uid` as seller.**

5. **MCP `seller_id`: top-level vs per-payment**
   - **Top-level required `seller_id` (int)** — validate browsable internal user
     (`exists()` and `share` is False / `base.group_user`) before idempotency lookup.
     All-new: stamp that id on every created voucher inside the existing savepoint.
     Exact replay and UniqueViolation replay: ignore `seller_id` (same as
     customer/attachments); do not write matching rows, including legacy NULL sellers.
     Partial/in-call duplicate still reject with no writes. Attachment atomicity
     unchanged.
     - Pros: matches approved contract; one seller per call; schema change is one
       required property
     - Cons: breaking for Nebula until follow-up
     - Effort: Low–Medium (tests)
   - **Per-payment `seller_id`** — mixed sellers in one call.
     - Pros: none vs approved decisions
     - Cons: extra schema; fights later same-seller sheets; replay semantics messier
     - Effort: Medium
   - **Recommend top-level `seller_id` only.**

### Recommendation

Implement **`collection.sheet` as a no-workflow grouping model** with sequence code
`collection.sheet` / prefix `CS/%(year)s/` (copy voucher sequence XML). Membership is
**Many2one `sheet_id` on the voucher** (`ondelete="set null"`) plus inverse
`voucher_ids`. Store **`seller_id → res.users`** on both; voucher field nullable; sheet
field required and readonly after create. Enforce same-seller and “assigned ⇒ has
seller” in **Python constraints** (optional SQL CHECK for the latter). Create sheets
from a **list-bound server action** over unassigned same-seller vouchers in any state.
Compute stored **`date_from`/`date_to` as `fields.Date`** from min/max member
`create_date` (UTC calendar date of the ORM datetime; empty sheet ⇒ both empty). MCP:
**require top-level `seller_id`**, validate internal user, apply only on all-new create,
preserve savepoint + `document_id` replay. ACL: one `base.group_user` row for sheets.
**Do not implement Nebula**; record it as a breaking-consumer follow-up.
`openspec/config.yaml` still lists nebula-agent under `apply.roots` from an older change
— this change must not treat that as permission to edit Nebula.

### Risks

- **Breaking MCP for Nebula**: current payload has no `seller_id`; all-new creates from
  the agent will UserError until a later consumer change. Exact replay of
  already-created MCP vouchers can still succeed without mutating them, but new batches
  cannot.
- **UI required vs ORM nullable**: form `required="1"` does not block RPC/import creates
  without seller. That is the intended legacy hole; tests must not accidentally require
  ORM `required=True`.
- **`date_from`/`date_to` timezone**: `create_date` is UTC. Using `.date()` /
  `fields.Date.to_date` is UTC calendar date, which may differ from company/user local
  date near midnight. Pin this in design; do not invent a `received_date`.
- **Internal-user definition**: use `share=False` (and preferably
  `has_group("base.group_user")`) so portal/public ids are rejected. `reviewed_by`
  currently has no domain; do not copy that looseness onto `seller_id`.
- **Review budget**: new model + views + MCP schema/tests + sheet tests will likely
  exceed the 400-line authored-diff guard; `sdd-tasks` should forecast chained PRs.
- **Empty sheets**: editable membership can leave a sheet with no vouchers; dates clear.
  Product does not forbid this.
- **Document Review**: out of scope; seller will be absent from the OWL queue until a
  later change.

### Ready for Proposal

Yes. Product decisions are consistent with the current addon. Orchestrator should tell
the user: proceed to **sdd-propose** for `collection-sheets` in the collection OpenSpec
store; keep Nebula as a documented follow-up consumer; do not backfill `seller_id`; do
not add sheet workflow or extra ACL groups.
