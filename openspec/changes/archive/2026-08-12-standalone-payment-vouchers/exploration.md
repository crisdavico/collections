## Exploration: standalone-payment-vouchers

### Current State

Payment registration is a **header + lines** split.

`collection.voucher` is the chatter/activity/sequence header: `name` via `ir.sequence`
code `collection.voucher` (`COL/%(year)s/`), required `customer_identification`, company
`currency_id`, `state` `new|validated|rejected` (default `new`, `group_expand=True`),
`payment_ids` One2many. Create strips forged `create_date`/`write_date`.
`action_validate` / `action_reject` run only from `new`; validate additionally refuses
when Document Review is ON and any **attached** line is still `pending`. Unlink is
allowed only when header `state == 'new'`. There is **no `write()` override**, so kanban
drag (`records_draggable="1"`, `default_group_by="state"`) can write `state` without
going through those actions.

`collection.voucher.line` holds the payment: `document_type`, nullable unique
`document_id` (`UNIQUE(document_id)` — UI may omit; MCP may not), type-specific fields,
optional Binary image/PDF + filename + `attachment_rotation`, and review `state`
`pending|approved|rejected` with `reviewed_by` / `reviewed_at`. Review queue, approve
(with field corrections), reject, rotation, `FOR UPDATE` eligibility, attachment-replace
reset, and aggregate header effects all live on the **line**. Last attached-line approve
MAY `action_validate()` the parent; line reject immediately `action_reject()`s a `new`
parent. When Document Review is OFF, those review RPCs refuse; header Validate/Reject
still exist.

UI is dual: Collections → Payment Vouchers (kanban/list/form, create enabled, three
stacked typed `payment_ids` tables) and Collections → Payment Lines (read-only list,
`create`/`edit` false). `unsupported` lines persist (MCP) but are hidden from the typed
form tables and browsed via Payment Lines. Document Review OWL hard-codes
`LINE_MODEL = "collection.voucher.line"` and
`/web/content?model=collection.voucher.line&field=attachment`. Menu
`menu_collection_document_review` is blacklisted when the company flag is OFF.

MCP `create_collection_voucher` on `muk_mcp.mixin` (method-discovered, no `sudo()`, no
DB tool row) creates **one header + N lines** in a savepoint. Idempotency is by line
`document_id`: all-new → create; exact set on **one** header → replay that voucher
(ignore customer/attachments); in-call duplicate, partial overlap, or docs spanning
**multiple headers** → `UserError`, no writes. Response is a single
`{id, name, state, payments: [{id, document_id}, ...]}`.

Nebula `register_latest_collection_voucher` maps the latest OCR batch to **one** MCP
call named `create_collection_voucher` and formats success from a **single** voucher
`id`/`name`/`state`. Its main spec requires “exactly one voucher” for the whole batch.
Tests and `tests/integration_tests/test_graph.py` hard-code that tool name.

ACL: `base.group_user` full CRUD on both models; no record rules. Manifest `19.0.1.8.0`.
Existing migration `19.0.1.7.0` only renamed line `review_status` → `state`.
`openspec/config.yaml` still says collection-addon-only apply roots
(`strict_tdd: true`). Leftover `openspec/changes/document-review-feature-flag/`
duplicates an already-archived change; it does not couple to this work — do not modify
it.

### Affected Areas

- `models/collection_voucher.py` — flatten: absorb line fields, sequence, chatter,
  attachment, review audit, `pending|approved|rejected`, unlink/approve/reject, audited
  kanban writes
- `models/collection_voucher_line.py` — remove model; move review
  queue/approve/reject/rotation/locks/attachment validation here onto voucher
- `tools/collection_voucher.py` — rename MCP to `create_collection_vouchers`; N
  standalone creates in one savepoint; replay returns **all** matching vouchers; drop
  header+lines create/replay
- `views/collection_views.xml` — drop Payment Lines menu/action/views and typed
  `payment_ids` embeds; one create/edit-enabled kanban/list/form grouped by new
  lifecycle
- `views/collection_document_review_views.xml` — client action stays; queue target
  becomes `collection.voucher`
- `static/src/document_review/document_review_helpers.esm.js` — `LINE_MODEL` and
  attachment URL model
- `static/src/document_review/document_review_action.esm.js` (+ `.xml`) — ORM calls,
  copy (“líneas”), payload `voucher_name` (now the record name)
- `security/ir.model.access.csv` — drop line ACL
- `data/ir_sequence_data.xml` — keep code `collection.voucher`; now one number **per
  payment**
- `models/ir_ui_menu.py`, `models/res_company.py`, `models/res_config_settings.py`,
  `views/res_config_settings_views.xml` — flag/menu hide stay; review RPCs still refuse
  when OFF
- `__manifest__.py`, `__init__.py`, `models/__init__.py` — drop line import; version
  bump
- `tests/test_collection_*.py` (all eight) — header/line, aggregate validate, dual
  menus, MCP single-voucher replay, OWL model strings
- `migrations/` — **no** conversion script (locked destructive reset); drop leftover
  line-table assumptions
- `AGENTS.md`, `openspec/specs/collection-vouchers/spec.md`,
  `openspec/specs/document-review/spec.md` — header/line, aggregate state, MCP name,
  dual menus
- `openspec/config.yaml` — apply root currently collection-only; this change also owns
  Nebula
- Nebula `src/agent/tools/collection_voucher.py` — `MCP_TOOL_NAME`, success formatter
  for a voucher **list**
- Nebula `tests/unit_tests/test_collection_voucher.py`,
  `tests/unit_tests/test_agent_tools.py`, `tests/integration_tests/test_graph.py`
- Nebula `openspec/specs/collection-voucher-registration/spec.md` — “one voucher per
  batch” and exact MCP name

### Approaches

1. **Standalone `collection.voucher` per payment (locked)** — Delete
   `collection.voucher.line`. One model owns former line fields plus customer, sequence,
   chatter, activities, attachment, review audit, and `pending → approved/rejected`. One
   Payment Vouchers kanban/list/form (create/edit on). Kanban groups by `state`; drag
   and header Approve/Reject both record reviewer/time; Approve/Reject remain when
   Document Review is OFF. MCP
   `create_collection_vouchers(customer_identification, payments)` atomically creates
   one voucher per payment. Exact `document_id` set replay returns **all** those
   vouchers; partial overlap and in-call duplicates reject with no writes. Destructive
   reset: discard legacy header/line rows; no chatter/SQL conversion. Coordinated Nebula
   rename + tests in this change.

   - Pros: Matches how operators and Nebula already think (one proof = one payment);
     chatter/audit per payment; drops aggregate header/line coupling and the extra
     Payment Lines menu; MCP idempotency stays on `document_id` without a parent
     grouping key
   - Cons: Breaking MCP name/shape; two git roots must ship together; sequence consumed
     per payment not per batch; large test/spec rewrite; existing devel/prod header+line
     data discarded
   - Effort: High

2. **Keep header+line; flatten UI only** — Leave models/MCP; hide Payment Lines; put
   line fields on the header form somehow.

   - Pros: Smaller schema/MCP blast; existing idempotency/replay tests survive
   - Cons: Chatter still on the batch header; review still on lines; dual `state`
     machines remain; does not match the locked product
   - Effort: Medium

3. **Keep a batch header as optional grouping** — Standalone payments plus a parent
   “deposit slip” for MCP batches.

   - Pros: Preserves today’s “one MCP call = one grouping record”
   - Cons: Reintroduces header/line coupling, aggregate validate/reject, and dual menus
     in another form; extra model for little operator value
   - Effort: High

4. **Data-preserving SQL migration (lines → vouchers)** — Same target model as (1) but
   convert rows, chatter, and attachments.
   - Pros: Keeps historical payments
   - Cons: Explicitly rejected; chatter/attachment `res_model` rewrite is error-prone;
     locked plan is reset/reinstall
   - Effort: High

### Recommendation

Use **approach 1** (locked). Do not reopen grouping, conversion, or UI-only flatten.

Implementation notes for proposal/design (not alternatives):

- Map today’s header `new/validated/rejected` → voucher `pending/approved/rejected`.
  Delete only from `pending`.
- Intercept kanban `state` writes (today they bypass `action_validate`) so drag is the
  same audited Approve/Reject path as the buttons.
- Document Review queue: `state == pending` AND attachment present (drop
  `voucher_id.state == 'new'`). OWL `LINE_MODEL` → `collection.voucher`. Review RPCs
  still refuse when the company flag is OFF; form/kanban Approve/Reject do not.
- MCP: today’s “cross-voucher” error **disappears** as a success path (a batch is N
  vouchers). Keep in-call duplicate + **partial overlap** reject. Exact replay = every
  submitted `document_id` already exists → return that full voucher list, ignore
  customer and attachment nests (same as today).
- Nebula: keep `register_latest_collection_voucher` as the first-party tool; switch MCP
  name; format a list of identities; update its OpenSpec (“one voucher covering the
  batch” is now “one voucher per payment, one atomic call”).
- `openspec/config.yaml` apply roots and SDD edit-authority must include `nebula-agent`
  for this change, or tasks will block on `edit_authority_missing`.
- Blast radius will exceed the 400-line review budget; later `sdd-tasks` should forecast
  chained PRs (Odoo model/UI vs MCP vs Document Review vs Nebula).

### Risks

- Odoo and Nebula must deploy together: old `create_collection_voucher` vs new
  `create_collection_vouchers` fail-closed on either side; Nebula MCP tool cache is
  process-lifetime.
- Kanban drag today writes `state` raw; without a write/action gate, audited
  reviewer/time will be skipped.
- Destructive reset discards header chatter, line attachments, and review audit;
  operators must accept `resetdb` / reinstall, not an in-place upgrade of
  `collection_voucher_line`.
- `UNIQUE(document_id)` moving to `collection.voucher` plus N `next_by_code` calls in
  one savepoint needs UniqueViolation race handling like today’s MCP path.
- Config.yaml still scopes apply to the collection addon only; Nebula work in this
  change needs an explicit second git-root grant.
- Leftover `openspec/changes/document-review-feature-flag/` can confuse status/dispatch
  if treated as active; ignore it.

### Ready for Proposal

Yes. Locked approach is confirmed against current code and specs. Orchestrator should
run `sdd-propose` for `standalone-payment-vouchers` (destructive flatten, MCP rename +
list replay, Nebula coordinated, no conversion script).
