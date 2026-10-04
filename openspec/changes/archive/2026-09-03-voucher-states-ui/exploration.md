## Exploration: voucher-states-ui

Settled product rules (Draft → Validated by Seller → Validated by Collections; no
Reject; Document Review is the only path to Validated by Collections) map onto current
code without a product fork. This note records the live surfaces, the remap, and the one
implementation coupling (snapshot `decision` vs voucher `state`).

### Current State

`collection.voucher.state` is a required Selection with `pending` / `approved` /
`rejected`, default `pending`, `tracking=True`, `group_expand=True`
(`models/collection_voucher.py` 53–64). ORM/UI create uses that default. MCP fused
create `_collection_create_vouchers` (`tools/collection_voucher.py` 552–554) stamps
`"state": "pending"` and returns `{id, name, state, document_id}` as-is.

Form header buttons `action_approve` / `action_reject` run only from `pending` and stamp
`reviewed_by` / `reviewed_at` (`316–336`). `_intercept_state_write` (`381–398`) rewrites
raw `approved`/`rejected` writes through those actions (kanban drag) and blocks reopen
to `pending` unless `message_main_attachment_id` is in the same vals. Attachment
replacement `_vals_with_review_reset_on_new_attachment` (`731–747`) sets `state` to
`pending` and clears reviewer columns.

Document Review queues `state == "pending"` plus designated proof on the sheet
(`get_review_queue` 635–649; `_is_review_eligible` 826–828). Approve/reject both go
through `_write_review_decision(status)` (`774–783`), which writes voucher `state` to
the same string and appends a snapshot whose `decision` Selection is
`approved`/`rejected` (`collection_voucher_review_snapshot.py` 38–43). OWL
`DocumentReviewAction.reject()` RPCs `action_review_reject`; the template button is
`t-on-click="reject"` / "Rechazar" (`document_review_action.xml` 579–597).

Unlink is `@api.ondelete` `_unlink_if_pending` (`550–552`) plus allocation detach.
Allocation MCP gate `_collection_allocation_vouchers` refuses
`voucher.state == "rejected"` (`tools/collection_allocation.py` 424–425).

Views (`views/collection_views.xml`): stages kanban XMLID
`view_collection_voucher_kanban` (`default_group_by="state"`, draggable); reassign
kanban `view_collection_voucher_reassign_kanban` is a distinct view. Action
`action_collection_voucher` `view_mode` is `kanban,list,form`. Form statusbar
`pending,approved,rejected` (no `clickable="false"`). History notebook page binds
`review_snapshot_ids`. Search has state filters `filter_pending` / `filter_approved` /
`filter_rejected` and only one type filter (`filter_unsupported`); `create_date` is a
search field plus group-by, not a date filter. List visible order today is
`name, partner_id, seller_id, sheet_id(optional=hide), create_date, state, document_type, amount`
(plus optional reviewed columns; `currency_id` `column_invisible`). Menu
`menu_collection_voucher` `sequence=10`; Configuration `sequence=100`. Chatter tracking
exists on `state` and `partner_id` only — not `seller_id`, `sheet_id`, `document_type`,
or `amount`.

Manifest is `19.0.1.30.0`. SQL remap pattern lives in
`migrations/19.0.1.28.0/post-migrate.py` (CASE then leftover-key collapse, before ORM).
Tests hardcode the old keys across voucher, review, UI, mail, MCP allocation, sheet
report, payment, ACL, and migration (`test_manifest_version_is_1_30_0`). Main specs to
delta: `collection-vouchers` (lifecycle), `document-review` (queue / approve-reject /
History visible), `collection-allocations` (not-rejected gate).
`collection-sheet-report` only names the old voucher keys in a print-includes-all
sentence. Leftover prose: `AGENTS.md` ("pending → approved | rejected"),
`readme/DESCRIPTION.md`. Nebula does not branch on these Odoo keys (out of scope). MCP
payloads echo `voucher.state`; consumers will see new keys after remap.

### Affected Areas

- `models/collection_voucher.py` — Selection keys/default; `action_approve` →
  `action_validate_seller` (draft only); drop `action_reject`; intercept; unlink;
  attachment reopen; review queue/eligibility/approve; drop `action_review_reject`;
  tracking on `seller_id`, `sheet_id`, `document_type`, `amount`
- `models/collection_voucher_review_snapshot.py` — keep rows; `decision` Selection stays
  historical `approved`/`rejected` unless decoupled write is chosen
- `tools/collection_voucher.py` — MCP stamp `validated_seller` instead of `pending`
- `tools/collection_allocation.py` — drop `state == "rejected"` gate
- `views/collection_views.xml` — delete stages kanban + drop `kanban` from `view_mode`;
  list/search/form/statusbar; drop History page; keep reassign kanban and menu
  `sequence=10`
- `static/src/document_review/document_review_action.esm.js` — drop `reject()`
- `static/src/document_review/document_review_action.xml` — drop Rechazar button
- `__manifest__.py` — `19.0.1.30.0` → `19.0.1.31.0`
- `migrations/19.0.1.31.0/post-migrate.py` — SQL CASE remap (1.28.0 pattern)
- Tests listed above, plus UI lock for voucher menu `sequence=10` vs config `100`
- OpenSpec mains: `collection-vouchers`, `document-review`, `collection-allocations`
  (and a one-line state-name fix in `collection-sheet-report`)
- `AGENTS.md`, `readme/DESCRIPTION.md` — leftover old keys (docs follow apply; this
  change must not edit them in explore)

### Approaches

1. **In-place Selection remap (settled)** — Replace keys on the same field; SQL remap
   existing rows before ORM; rename form approve to Validate by Seller; Review Approve
   writes `validated_collections`; delete Reject / stages kanban / History tab.

   - Pros: Matches settled rules; one field; same 1.28.0 migrate shape; no dual
     vocabulary in voucher.state
   - Cons: Wide test/spec blast; leftover `ir.ui.view` for deleted kanban if XML record
     is removed without an explicit `<delete>`
   - Effort: Medium (behavior is localized; tests/docs are the bulk)

2. **Decouple snapshot `decision` from voucher `state` (implementation only)** — Review
   Approve writes voucher `validated_collections` and still snapshots
   `decision="approved"` (existing Selection). Alternative: extend snapshot Selection
   with `validated_collections` and leave old `rejected` rows as-is.
   - Pros: A avoids migrating snapshot rows; B makes decision == new voucher state for
     new reviews
   - Cons: A keeps a second vocabulary; B still leaves historical `rejected`
   - Effort: Low (one write site: `_write_review_decision` / `_append_review_snapshot`)

No product fork. Do not keep old keys with UI-only labels.

### Recommendation

Use approach 1. For snapshots, use 2A: keep `decision` as `approved`/`rejected`
historical codes; new Review Approve still records `approved` while voucher `state`
becomes `validated_collections`. Snapshots stay in DB and leave the form.

Also: SQL remap `pending`→`draft`, `approved`→`validated_collections`,
`rejected`→`draft` in `migrations/19.0.1.31.0/post-migrate.py` before any ORM browse;
drop `group_expand` on `state` with the stages kanban; set statusbar `clickable` false;
explicit `<delete>` of `view_collection_voucher_kanban` plus `view_mode` `list,form`;
intercept must refuse raw `validated_collections` and route `validated_seller` only
through `action_validate_seller`; attachment reopen writes `validated_seller`. Lock
`menu_collection_voucher.sequence == 10` before Configuration `100` in UI tests.

### Risks

- Upgrade: leftover `pending`/`approved`/`rejected` in DB will crash Selection browse if
  SQL does not run first (same class of bug 1.28.0 solved)
- Leftover stages kanban `ir.ui.view` / `view_mode` still listing `kanban` after XML
  removal
- `_write_review_decision` currently sets voucher `state` and snapshot `decision` to the
  same string — must split or Selection write fails
- MCP `vouchers[].state` values change; Nebula is out of scope but any other consumer
  that compared `pending`/`approved` will drift
- Wide RED surface: UI, voucher lifecycle, review, mail tracking labels, MCP
  rejected-voucher test, sheet-report mixed-state print, manifest `1.31.0`
- Review-budget: model + views + OWL + migration + many tests will likely exceed 400
  authored lines — `sdd-tasks` should forecast chained PRs
- `openspec/config.yaml` proposal rule still mentions coordinated Nebula work; this
  change must not reopen Nebula

### Ready for Proposal

Yes. Settled 3-state rules map onto current approve/reject, review queue, MCP stamp,
allocation gate, stages kanban, History tab, unlink, attachment reopen, and the 1.28.0
SQL-first migrate pattern. Orchestrator should run `sdd-propose` with those rules locked
and snapshot `decision` decoupled as recommended.
