## Exploration: draft-until-close

Product intent is settled (user plan `draft_until_sheet_close_15295379`):
`collection.allocation` is `draft` while the sheet is `open` and `confirmed`
only when the sheet is `closed`. Validate/Reject go away. Draft allocations,
pending vouchers on them, and open sheets become deletable; close freezes.
Nebula-agent is out of scope for this change (deferred copy/eval follow-up
only). Do not extend archived `inline-collection-allocation`.

### Current State

**Allocation header** (`models/collection_allocation.py`, manifest
`19.0.1.27.0`):

- Selection is `confirmed` | `validated` | `rejected`, default `confirmed`.
- Freeze `_FROZEN_FIELDS` (`line_ids` / `voucher_ids` / `partner_id` /
  `sheet_id`) when `state != "confirmed"`. Form
  `readonly="state != 'confirmed'"`.
- Raw `state` write without `collection_allocation_audited_state` routes to
  `action_validate` / `action_reject` (from `confirmed` only) or raises.
- Residual `>= 0` and reason-if-positive only while `confirmed`
  (`_check_residual` skips `validated`/`rejected`; tests drive residual
  negative after Validate).
- `_unlink_if_no_revisions`: any `revision_ids` blocks unlink. Unlink without
  revisions unassigns vouchers (`allocation_id` `ondelete="set null"`) and
  cascades lines.

**Revisions** (`models/collection_allocation_revision.py`):

- Create gated by `collection_allocation_revision`. `write` always refused.
- `_unlink_forbidden` always raises. ACL `1,0,1,0` so cascade unlink of a
  parent would hit AccessError even if the gate were opened. Tests assert
  internal-user unlink is `AccessError`.

**MCP write** (`tools/collection_allocation.py`):

- `create_collection_allocation` does not set `state`; default implied
  `confirmed` + `revision` 1. Amend requires `existing.state == "confirmed"`
  (`validated`/`rejected` → “already reviewed”). Revalidation subtracts other
  `confirmed`+`validated` applications (rejected does not). SUPERSET amend
  while confirmed is allowed even on an open sheet.

**Sheets** (`models/collection_sheet.py`):

- `action_close` / `action_reopen` write only sheet `state`. They do not
  touch allocations.
- `_unlink_if_no_allocations`: any `allocation_ids` refuses. Empty closed
  sheets currently unlink and unassign members
  (`test_unlink_closed_sheet_unassigns_vouchers`). `sheet_id` on allocation
  is `ondelete="restrict"`.

**Vouchers** (`models/collection_voucher.py`):

- `_unlink_if_pending` (keep) plus `_unlink_if_unallocated` (any
  `allocation_id` refuses, including pending).
- `_allocation_is_confirmed_or_unset`: membership write only when current and
  target are confirmed or unset. `_ensure_source_allocation_detachable` and
  `_target_allocation_for_partner` also require `confirmed` (residual
  projection on detach). Validated/rejected sources refuse partner moves.

**UI** (`views/collection_allocation_views.xml`): Validate/Reject header
buttons, statusbar `confirmed,validated,rejected`, search filters, form
`reviewed_by` / `reviewed_at`, membership readonly when not confirmed.

**Specs to modify (no new capability):** `collection-allocations` (lifecycle,
freeze invert, draft unlink, residual/revalidation, MCP persist `draft`),
`collection-vouchers` (membership/unlink invert + residual guard),
`collection-sheets` (close/reopen sync; open-sheet delete cascades drafts;
closed-sheet delete refused).

CodeGraph MCP/CLI did not surface `models/collection_allocation.py` (index
miss / name collision with voucher `action_reject`). Source above was read
from disk.

### Affected Areas

- `models/collection_allocation.py` — selection default `draft`; drop
  Validate/Reject intercept; freeze when `confirmed`; residual on both
  states; sheet iff-constraint; draft unlink despite revisions.
- `models/collection_allocation_revision.py` — gated `@api.ondelete` so
  parent-delete may cascade; direct unlink stays forbidden.
- `models/collection_sheet.py` — close confirms allocations; reopen returns
  them to draft; open unlink deletes draft allocations first; refuse closed
  unlink.
- `models/collection_voucher.py` — drop allocated-cannot-delete; pending +
  draft/unset deletable with residual projection; membership helper invert
  to draft-or-unset.
- `tools/collection_allocation.py` — persist `draft`; amend only while
  `draft`; revalidation domain `draft`+`confirmed`; tool description.
- `tools/allocation_lookup.py` — open-sheet payload `state: "draft"` (no
  `validated`).
- `views/collection_allocation_views.xml` — drop Validate/Reject/filters;
  statusbar `draft,confirmed`; `readonly="state == 'confirmed'"`; leave
  `reviewed_by`/`reviewed_at` off the form (keep on model).
- `security/ir.model.access.csv` — revision ACL `1,0,1,1`.
- `__manifest__.py` + `migrations/19.0.1.28.0/post-migrate.py` — bump from
  `19.0.1.27.0`; remap state from sheet; no `CA/` sequence work.
- `AGENTS.md` — lifecycle/ACL/MCP/UI bullets (today still say default
  `confirmed` and revision `1,0,1,0`).
- Tests: `test_collection_allocation.py`,
  `test_collection_allocation_acl.py`, `test_collection_mcp_allocation.py`,
  `test_collection_mcp_allocation_lookup.py`, `test_collection_sheet.py`,
  `test_collection_voucher.py` (partner-write / non-confirmed source),
  `test_collection_ui.py`, `test_collection_company_migration.py`.
- OpenSpec deltas later: the three capabilities above. Strict TDD
  (`openspec/config.yaml`).

### Approaches

1. **Invert-in-place lifecycle (recommended)** — Keep the same models.
   Default `draft`. Sheet Close/Reopen are the only audited allocation-state
   writers (reuse `collection_allocation_audited_state`). Invert freeze,
   form readonly, amend gate, membership helper, and residual domain. Replace
   `_unlink_if_no_revisions` with refuse-if-confirmed. Gated revision
   unlink + ACL unlink so cascade is not AccessError. Open-sheet unlink
   unlinks draft allocations first (vouchers set-null, not destroyed).
   - Pros: Matches settled product; smallest surface; same MCP contract
     keys; existing revision/idempotency path stays; no sudo.
   - Cons: Large test rewrite; close/reopen must skip the iff-constraint
     mid-flight; ACL unlink looks like “users can delete revisions” until
     `@api.ondelete` is understood.
   - Effort: Medium (wide test/UI/MCP rewrite, concentrated model diffs).

2. **Keep Validate/Reject as unused aliases** — Leave selection keys and
   buttons, map them in migration only.
   - Pros: Softer DB remap.
   - Cons: Violates product; freeze/amend logic stays ambiguous; UI and
     specs stay wrong.
   - Effort: Low but rejected.

3. **Soft-cancel drafts instead of unlink** — Flag drafts cancelled; never
   delete revision rows.
   - Pros: Avoids revision ACL/ondelete dance.
   - Cons: Violates delete rules; UNIQUE `(sheet, partner)` would still
     block a replacement create; not what Close/Reopen/delete specify.
   - Effort: Medium and rejected.

### Recommendation

Use **approach 1**. Product is not reopened.

Implementation notes for propose/design (not new product):

- **Iff-constraint:** `@api.constrains("state", "sheet_id")` — `draft` iff
  sheet `open`, `confirmed` iff sheet `closed`. Skip while
  `collection_allocation_audited_state` (or a dedicated sync context) so
  Close/Reopen can two-step without a mid-write violation. Order: Close →
  confirm allocations then close sheet (membership stays frozen once
  confirmed). Reopen → reopen sheet then draft allocations (membership
  stays frozen until draft). Then let the constrain run.
- **Allocation `write` intercept:** Stop routing to Validate/Reject. Refuse
  raw `state` writes except the audited context from Close/Reopen.
- **Revision cascade:** Same pattern as create: context e.g.
  `collection_allocation_parent_unlink`. `_unlink_forbidden` no-ops only
  then. Direct unlink still UserError. ACL `1,0,1,1` so ORM cascade is not
  AccessError. Do not `sudo()`.
- **Draft allocation unlink:** Unassign is automatic (`ondelete="set null"`).
  Cascade lines. Delete revision snapshots under the parent gate. Confirmed
  still refused (even with zero revisions).
- **Open sheet unlink:** Unlink draft allocations first (they must all be
  draft while open), then the sheet. Closed sheets refused even when empty
  (stricter than today’s empty-closed unlink).
- **Voucher pending unlink:** Allowed if allocation unset or `draft`. If
  `draft`, project residual as today (`residual - amount`); `< 0` refuses;
  do not rewrite invoice lines. Confirmed allocation refuses. Approved/
  rejected vouchers still pending-only blocked.
- **Membership:** Rename/invert `_allocation_is_confirmed_or_unset` to
  draft-or-unset. Target search `state="draft"`. Confirmed (closed sheet)
  cannot attach/detach. Closed-sheet partner freeze stays.
- **MCP:** First persist stays `revision` 1 but `state` `draft`. Amend iff
  `draft` (closed/confirmed refuses; replace “already reviewed”).
  Revalidation `("allocation_id.state", "in", ("draft", "confirmed"))`.
- **Migration:** `19.0.1.28.0`. SQL remap from sheet (`open` → `draft`,
  `closed` → `confirmed`) so dropped selection keys never linger. Prefer
  SQL at the start of `post-migrate.py` (existing 1.25.0 style) so ORM does
  not browse stale `validated`/`rejected`. Collapse those keys; chatter
  history remains. `reviewed_by`/`reviewed_at` stay on the model, leave the
  form. Do not add `CA/` sequence work. Update
  `test_collection_company_migration.py` (today asserts no `19.0.1.27.0/`
  folder).
- **Residual:** Apply for both remaining states (equivalent to “while draft
  and after confirm”). MCP residual check already runs before persist.
- **Deferred (not this change):** Nebula `_EXISTING_ALLOCATION_MESSAGE`,
  PRD/eval “confirmed allocation” wording, parse `state: "draft"`. Agent
  amend still out of scope.

### Risks

- Close/Reopen two-step vs iff-constraint: without a skip-context, the first
  write violates `draft`↔`open` / `confirmed`↔`closed`.
- Revision ACL unlink (`1,0,1,1`) plus a leaky `@api.ondelete` gate would
  let UI delete snapshots; keep the gate tight and rewrite ACL tests
  (`AccessError` → `UserError` on direct unlink).
- Pending voucher delete on a fully applied draft can trip residual `< 0`;
  operators must delete the whole draft allocation instead — document in
  specs so tests do not auto-edit lines.
- Closed empty sheets become non-deletable (`test_unlink_closed_sheet_*`
  flips). Reopen-then-delete remains the escape.
- CodeGraph index missed `collection_allocation.py`; apply agents should
  Read that file, not trust explore-by-name.
- Authored diff will likely exceed the 400-line review budget (tests + three
  specs + views). `sdd-tasks` should forecast chained PRs
  (`delivery_strategy: auto-chain` in `state.yaml`).
- `AGENTS.md` still documents `19.0.1.26.0` while the manifest is
  `19.0.1.27.0`; this change should land the lifecycle bullets at
  `19.0.1.28.0`.

### Ready for Proposal

Yes. Orchestrator should run `sdd-propose` for `draft-until-close` with
modified capabilities `collection-allocations`, `collection-vouchers`, and
`collection-sheets`. Strict TDD. Apply root is the collection git repo
only; do not implement Nebula in this change.
