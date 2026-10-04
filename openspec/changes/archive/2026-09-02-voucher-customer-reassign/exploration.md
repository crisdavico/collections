## Exploration: voucher-customer-reassign

### Current State

`collection.voucher.partner_id` is a required, tracked, indexed Many2one (`res.partner`,
label Customer, `ondelete="restrict"`). It has **no** `group_expand`, **no** `readonly`,
and `write()` does not branch on it. Kanban drop of a grouped Many2one in Odoo 19 is
`record.update({partner_id: value}, {save: true})` — so a customer-grouped kanban **is**
the reassignment if `partner_id` is in the arch and not readonly.

Voucher `write()` today:

- Blocks provenance keys; routes `state` through Approve/Reject; splits
  `message_main_attachment_id` per-record.
- Calls `_ensure_sheet_membership_unlocked` **only when `sheet_id` is in vals** (closed
  message: `"Closed collection sheets cannot change membership. Reopen first."`).
- Calls `_ensure_allocation_membership_writable` **only when `allocation_id` is in
  vals** (current and target must be `confirmed` or unset).
- Then `return super().write(vals)` with no partner/allocation follow-up.

Closed freeze is therefore **sheet membership only**.
`test_freeze_rejects_add_remove_and_reassign` writes `sheet_id` / `voucher_ids`, never
`partner_id`. A closed-sheet customer change currently succeeds.

Allocation side:

- `UNIQUE(sheet_id, partner_id)`.
- Freeze `_FROZEN_FIELDS = {line_ids, voucher_ids, partner_id, sheet_id}` when
  `state != confirmed`.
- `@api.constrains("partner_id", "voucher_ids")` `_check_voucher_partners` — fires on
  allocation `partner_id` / `voucher_ids` (inverse `allocation_id`), **not** on
  `collection.voucher.partner_id`. Bug 1 is real; no test currently writes voucher
  `partner_id` while allocated.
- Residual is stored computed `sum(voucher.amount) - sum(line.amount_applied)`.
  `_check_residual` (confirmed only): residual must not be negative; `residual_reason`
  required when residual `> 0`. Detaching a voucher from a fully applied allocation
  (`residual == 0`, applied == vouchers) **always** drives residual negative unless
  invoice lines are revised (out of scope).

Sheet UI:

- Header: Close / Reopen / `action_open_document_review`
  (`invisible="not id or not document_review_enabled"`), then statusbar.
- Button box: counted `action_open_vouchers` (`view_mode="list,kanban,form"`, domain
  `sheet_id`, **no** `views` list — uses the **state** kanban).
- `_ensure_saved_sheet` refuses NewId. `action_open_vouchers` does **not** require
  `state == open`.

Existing Payment Vouchers kanban (`view_collection_voucher_kanban`):
`default_group_by="state"`, `records_draggable="1"`, `t-name="card"`,
`class="o_kanban_mobile"`, `partner_id` twice (root + card), create enabled. Frozen by
`test_kanban_groups_by_state_and_shows_card_fields`,
`test_customer_field_is_partner_id_without_domain` (kanban count **2**),
`test_state_group_expand_shows_all_columns` (`state.group_expand` is `True` — valid
**only** for Selection).

Odoo 19 `group_expand` (container `/opt/odoo/custom/src/odoo/odoo/orm/`):

- Selection: `group_expand=True` is rewritten to `_default_group_expand`.
- Many2one: `group_expand` must be a **method name or callable**. `True` fails
  `assert callable(group_expand)`.
- Signature: `(self, groups, domain)` → same comodel recordset. Identity =
  `return groups`.
- Kanban uses `formatted_read_group` / `web_read_group` with context `read_group_expand`
  (existing voucher test uses `formatted_read_group`).
- Drag disabled if the grouped field is readonly on the field **or** every arch node of
  that field is readonly.
- `group_create` / `group_delete` / `group_edit` / `groups_draggable` / `quick_create`
  match the plan’s attribute names. `canCreateGroup` additionally requires Many2one
  **and** `default_group_by` matching the active groupby.

Manifest is `19.0.1.25.0`; version test is `test_manifest_version_is_1_25_0`. Search
view groups by `state` / `create_date` / `document_type` / `sheet_id`, not `partner_id`.
No `migrations/19.0.1.26.0/` needed if no stored field.

Settled product vs spec: closed freeze in `collection-sheets` is membership (`sheet_id`
/ members). Open-only **customer** reassignment is a **new** voucher/sheet requirement;
reusing the existing closed-membership UserError string is acceptable if specs say so.
“Any voucher state may move” matches current `write()` (terminal states do not freeze
`partner_id`).

### Affected Areas

- `models/collection_voucher.py` — `partner_id.group_expand`; `write()` partner_id
  branch (closed sheet, allocation detach/attach, residual, chatter); voucher-side
  `@api.constrains("partner_id", "allocation_id")`.
- `models/collection_sheet.py` — new `action_open_voucher_reassign` next to
  `action_open_vouchers` / `_ensure_saved_sheet`.
- `views/collection_views.xml` — **new** `view_collection_voucher_reassign_kanban`;
  header button after Document Review. Do **not** edit `view_collection_voucher_kanban`.
- `__manifest__.py` — `19.0.1.25.0` → `19.0.1.26.0`.
- `tests/test_collection_ui.py` — new kanban arch + header button; keep state-kanban
  asserts; add `formatted_read_group` expand for empty allocation-customer columns
  (`read_group_expand=True`).
- `tests/test_collection_sheet.py` — action shape, unsaved, closed-sheet refuse; extend
  freeze to `partner_id`.
- `tests/test_collection_voucher.py` — partner write + allocation follow-up / residual /
  constrain.
- `tests/test_collection_allocation.py` — freeze/residual/confirmed-or-unset still
  apply; add voucher-`partner_id` mismatch cases (none today).
- `tests/test_collection_company_migration.py` — rename
  `test_manifest_version_is_1_25_0`.
- OpenSpec `collection-vouchers` / `collection-sheets` / `collection-allocations` — new
  reassign UI + partner match on voucher write; closed freeze extended to customer;
  residual behavior on detach/attach.
- Out of scope (do not touch): Document Review OWL, creating allocations, revising
  `line_ids`, MCP, existing state kanban.

CodeGraph MCP often ranked `tools/collection_voucher.py` for allocation/XML queries;
those files were Read/Grep’d after targeted `codegraph_explore` misses. Odoo 19
`group_expand` / kanban drag were confirmed from the running image
(`/opt/odoo/custom/src/odoo/...`), not guessed.

### Approaches

1. **Plan-as-written (new kanban + `write()` follow-up)** — Sheet-open action with
   custom kanban grouped by `partner_id`; columns = allocation customers ∪ stray voucher
   customers via `group_expand="_read_group_partner_ids"`; drop writes `partner_id`;
   `write()` detaches confirmed source (residual-safe) and attaches confirmed same-sheet
   target when residual still OK, else unallocated; voucher-side partner constrain; new
   view; manifest 1.26.0.

   - Pros: Matches settled UX; native Odoo drag; fixes both pre-existing bugs for every
     `partner_id` write (form included); leaves frozen state kanban alone; no stored
     field / no migrate folder; `action_open_vouchers` pattern exists.
   - Cons: Must **merge `allocation_id` into the same `super().write` vals** as
     `partner_id` or the new constrain fires mid-move. Fully applied source allocations
     **block** the whole drop (residual would go negative; line revision is out of
     scope). Empty target allocation without `residual_reason` cannot accept a
     positive-amount voucher (leave unallocated).
   - Effort: Medium

2. **`group_expand=True` on `partner_id`** — Copy the Selection pattern used on `state`.

   - Pros: One-liner.
   - Cons: Odoo 19 only rewrites `True` on **Selection**. Many2one `True` hits
     `assert callable(group_expand)`. Would also expand globally, not sheet-scoped.
   - Effort: Low (and wrong)

3. **Wizard / explicit Customer Many2one instead of drag** — Server method picks target
   partner.

   - Pros: Easier residual messaging; no `group_expand`.
   - Cons: Reopens a settled product decision; more UI than a header kanban.
   - Effort: Medium

4. **Custom OWL board** — Bypass native kanban grouping.

   - Pros: Full control of empty columns.
   - Cons: Out of scope; duplicates Document Review’s OWL surface; larger review budget.
   - Effort: High

5. **Constrain-only (no allocation follow-up)** — Voucher-side partner match without
   detach/attach.
   - Pros: Fixes silent mismatch.
   - Cons: Makes allocated customer edits impossible; does not deliver the kanban goal.
   - Effort: Low

### Recommendation

**Approach 1 (plan-as-written), with two implementation constraints that the plan
implied but did not spell as write-ordering:**

1. When `partner_id` changes, compute target `allocation_id` (`False` or the unique
   confirmed same-sheet allocation for that partner) **before** `super().write`, and
   write `partner_id` + `allocation_id` together. Per-record `super().write` when
   outcomes differ (same pattern as `message_main_attachment_id`). Do not `sudo()`.
2. Project residual **before** write: source `residual - amount < 0` (confirmed,
   currency compare) → `UserError` (block entire move). Target attach only if confirmed,
   same sheet, and projected residual still satisfies `_check_residual` (including
   `residual_reason` when projected residual `> 0`); otherwise leave unallocated and
   `message_post` the outcome.

`group_expand` method: identity `return groups` when `collection_reassign_sheet_id` is
missing/invalid/unreadable; else `search` allocation ∪ voucher partners on that sheet,
`order` = `res.partner` `_order`. Context-gated so Payment Vouchers is unchanged.

Action: `ensure_one` + `_ensure_saved_sheet` + `UserError` if `state != 'open'`; `views`
list `(reassign kanban, form)` — **do not** combine `view_mode` + `view_id` (would still
resolve the state kanban). Context: `collection_reassign_sheet_id` +
`group_by: partner_id`. Header button after `action_open_document_review`,
`invisible="not id or state != 'open'"`. New kanban: `records_draggable="1"`,
create/quick_create/group_create/group_delete/group_edit `"0"`, `groups_draggable="0"`,
`class="o_kanban_mobile"`, `t-name="card"`, `partner_id` present and **not** readonly.

Tests RED first (`openspec/config.yaml` `strict_tdd: true`). Extend UI/sheet/voucher
tests; do not weaken state-kanban freezes. Expand coverage via
`with_context(read_group_expand=True).formatted_read_group` (same as
`test_state_group_expand_shows_all_columns`); `web_read_group` is the web RPC wrapper of
that path.

### Risks

- **Residual vs “any voucher may move”:** confirmed fully applied allocations cannot
  drop their vouchers without revising lines (out of scope). Specs must say the move is
  refused, not silently unallocated.
- **Constrain vs write order:** voucher-side
  `@api.constrains("partner_id", "allocation_id")` is required (allocation constrain
  does not see voucher `partner_id` writes) but will reject a two-step
  detach-then-partner write; same-vals write is mandatory.
- **Existing kanban freeze:** editing `view_collection_voucher_kanban` or putting
  `partner_id` readonly on a shared view disables drag or breaks UI tests. New XMLID
  only.
- **`group_expand=True` on Many2one:** would crash at expand time. Method name +
  identity fallback only.
- **Closed freeze string reuse:** operators see a membership error on customer change;
  specs must extend closed freeze to `partner_id`, not only `sheet_id`.
- **Review size:** models + new view + several test files + spec deltas likely near the
  400-line budget; keep OWL/MCP/line revision out.
- **Empty target column attach:** allocation with no vouchers, residual 0, no
  `residual_reason` cannot take a positive-amount voucher without violating
  `_check_residual`; follow the plan (leave unallocated + chatter).

### Ready for Proposal

**Yes** — product decisions match the codebase; both named bugs are confirmed; Odoo 19
kanban/`group_expand` support the planned UI. Tell the user the proposal can proceed on
the closed-source plan, provided design/tasks lock **same-write
`partner_id`+`allocation_id`**, **source residual block vs target unallocated**, **new
kanban XMLID**, and **manifest 19.0.1.26.0 / `test_manifest_version_is_1_25_0` rename**.
Do not reopen columns, drag-as-write, open-only guardrail, or out-of-scope items.
