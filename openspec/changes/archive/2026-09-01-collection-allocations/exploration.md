## Exploration: collection-allocations

Closed product decisions from
`/home/crisd/.claude/plans/quiero-que-me-armes-tingly-penguin.md` are treated as chosen.
This change is Odoo `collection` only. Out of scope: Nebula FIFO conversation, ERP
write-back, retention certificates, collection sheet report tools.

### Current State

There is no `collection.allocation` (or line/revision) model, no MCP
`create_collection_allocation`, and no `CA/` sequence. Manifest is **`19.0.1.24.0`**.
The only MCP write tool is `create_collection_vouchers`. The connector is read-only:
`_DISPATCH_OPS = {test_connection, list_sellers, list_customers, get_customer_debt}`.

**Vouchers.** `collection.voucher` is one payment. `amount` is optional
`fields.Monetary()` (not required). `sheet_id` is `ondelete="set null"` with write
guards that freeze closed-sheet membership (`write` at line 258 via
`_ensure_sheet_membership_unlocked`). `@api.ondelete` currently only blocks non-pending
unlink. There is **no** ORM check that `voucher.company_id == sheet_id.company_id`
(migration 1.17.0 repairs leftovers; live writes can still mismatch). `partner_id` is
required, `ondelete="restrict"`. `check_company` is **not** set on `sheet_id`.
`_REVIEW_EDITABLE_FIELDS` includes `amount`, so Document Review can change a voucher
amount after it is already on an allocation.

**Sheets.** `collection.sheet` is `open`/`closed`, one-open per `(company, seller)` via
advisory lock `_lock_open_sheet_for_seller` (`pg_advisory_xact_lock(hashtext(...),
seller_id)`). `_sanitize_voucher_commands` rewrites `Command.DELETE` to
`Command.unlink` so the O2M widget cannot destroy vouchers. Sheet `unlink` sets
context `collection_sheet_unlinking` so membership freeze does not trap members;
voucher `sheet_id` then nulls. Tests `test_unlink_sheet_unassigns_vouchers` (line 409)
and `test_unlink_closed_sheet_unassigns_vouchers` (line 462) encode that behavior.

**Review snapshot template.** `collection.voucher.review.snapshot`: context-gated
create (`collection_review_snapshot`), `write` raises, `@api.ondelete` raises, ACL
`1,0,1,0`, related stored `company_id` with `precompute=True`,
`UNIQUE(voucher_id, revision)`. Append uses `FOR UPDATE` on the voucher
(`_lock_and_ensure_review_eligible`).

**MCP voucher create order.** Form (non-empty `payments`) →
`_collection_require_internal_seller` (internal user only; Enabled Seller is
`_assert_new_work` on ORM create) → parse vals → classify visible `document_id` (same-
company replay / other-company generic conflict / partial reject) → nest parse →
`_collection_create_vouchers` under `env.cr.savepoint()` (nested savepoint around
`resolve_customer_partner`) → `UniqueViolation` → `invalidate_all()` → reclassify
or generic conflict. Helper `_collection_require_internal_seller` lives on
`muk_mcp.mixin` (tools inherit it; do not redefine).

**Debt / partners.** MCP `customer_debt` is read-only: internal ACL, require seller,
`get_customer_debt`, strip `source`. `get_customer_debt` dispatches the **external**
seller id. Outstanding filter: `balance > 0` and state `open`/`overdue`.
`resolve_customer_partner` hits `collection.connector.customer.binding` by
`(connector_id, identification)` then **creates** partner + binding on miss via
`_resolve_unbound_customer_partner`. Allocation MUST NOT call this. Binding UNIQUE axes:
external id, identification, partner — all per connector. User ACL `1,0,1,0`.

**Sequences.** `COLLECTION_SEQUENCE_SPECS` has voucher `COL/%(year)s/` and sheet
`CS/%(year)s/`. XMLIDs `seq_collection_voucher` / `seq_collection_sheet` bind
`base.main_company`. `res.company.create` calls `_collection_copy_sequences()`
(templates from main company, `number_next=1`). Only migrate folder is
`migrations/19.0.1.17.0/`; `COLLECTION_SEQUENCE_CODES` there is orphan cleanup for
voucher/sheet only — do not add allocation to that tuple.

**Security.** `base.group_user` voucher/sheet `1,1,1,1`; snapshot `1,0,1,0`. Global
`ir.rule` `[('company_id', 'in', company_ids)]` on voucher, sheet, snapshot,
connector, seller binding, customer binding. Never `sudo()`. Related stored
`company_id` is required for the rule to classify other-company hits.

**UI.** Sheet form (`view_collection_sheet_form`) shows `voucher_ids` as a
`many2many` list **not** in a notebook. Menus: vouchers `sequence="10"`, sheets
`sequence="20"` under `menu_collection_root`. Sheet action already uses Odoo 19 `path`.

**Main specs.** `openspec/specs/collection-vouchers/spec.md` and
`openspec/specs/collection-connectors/spec.md` exist. **Contrary to the launch
briefing, `openspec/specs/collection-sheets/spec.md` also exists.** Its requirement
"Membership, dates, and deletion" currently **requires** deleting an open or closed
sheet to unassign members and not delete vouchers. The plan's
`allocation.sheet_id ondelete="restrict"` will make sheets with allocations undeletable;
propose MUST emit a **MODIFIED** collection-sheets delta (and keep unlink-unassigns
for sheets that have no allocations). There is no `collection-allocations` main spec
yet — plan unit 0 adds that capability plus voucher/sheet deltas.

### Affected Areas

- `models/collection_allocation.py` (new) — header: mail.thread + activities;
  `UNIQUE(sheet_id, partner_id)`; states `confirmed`/`validated`/`rejected`; computes;
  freeze `write`; Command.DELETE sanitizer; `@api.ondelete` if revisions exist
- `models/collection_allocation_line.py` (new) — ERP invoice snapshot +
  `amount_applied`; related stored `currency_id` (registry requires it for Monetary);
  CHECK / UNIQUE constraints via `models.Constraint`
- `models/collection_allocation_revision.py` (new) — immutable snapshot clone;
  `request_id` is the MCP idempotency key (`UNIQUE(request_id)`); `content_hash`;
  context-gated create
- `models/collection_voucher.py` — new `allocation_id` (`ondelete="set null"`,
  `check_company=True`); write guard next to `sheet_id`; extra `@api.ondelete` when
  allocated
- `models/collection_sheet.py` — inverse `allocation_ids`; unlink becomes restrict
  when allocations exist (PostgreSQL FK); sanitizer pattern copied onto allocation
- `models/res_company.py` — append
  `("collection.allocation", "Collection Allocation", "CA/%(year)s/", 4)`
- `data/ir_sequence_data.xml` — `seq_collection_allocation` on `base.main_company`
- `migrations/19.0.1.25.0/post-migrate.py` (new) — only
  `env["res.company"].search([])._collection_copy_sequences()` for existing companies
- `__manifest__.py` — `19.0.1.24.0` → `19.0.1.25.0`; new views/data imports
- `models/__init__.py`, `tools/__init__.py`, `tests/__init__.py` — register new
  modules
- `tools/collection_allocation.py` (new) — `@mcp_tool create_collection_allocation`
  (`category=write`, `registry=mcp`); reuse mixin helpers; binding-only partner
  lookup; fresh `get_customer_debt`; subtract other confirmed/validated applications
  of the same `external_invoice_id`
- `tools/collection_voucher.py` — unchanged contract; helper reuse only
- `tools/customer_debt.py` / `models/collection_connector.py` — **must stay
  read-only**; do not extend `_DISPATCH_OPS`; do not call
  `resolve_customer_partner` from allocation
- `security/ir.model.access.csv` — allocation/line `1,1,1,1`; revision `1,0,1,0`
- `security/collection_security.xml` — three company `ir.rule`s
- `views/collection_allocation_views.xml` (new) — list/form/search, `act_window`
  with `path`, menuitem `sequence="30"`
- `views/collection_views.xml` — wrap sheet `voucher_ids` + allocation list in
  `<notebook>` (`<list>` not `<tree>`)
- `tests/test_collection_allocation.py`, `test_collection_allocation_acl.py`,
  `test_collection_mcp_allocation.py` (new)
- `tests/test_collection_company_migration.py` — `test_manifest_version_is_1_24_0`
  (line 153) and sequence enum at lines 437–439
- `tests/test_collection_sheet.py` — unlink tests at 409 and 462; declare
  restrict-when-allocated
- `tests/test_collection_ui.py` — sheet form notebook + new menu
- `openspec/specs/collection-allocations/spec.md` (new, via later sdd-spec)
- `openspec/specs/collection-vouchers/spec.md` and
  `openspec/specs/collection-sheets/spec.md` — deltas in this change
- Optionally `openspec/specs/collection-connectors/spec.md` — ADDED scenario:
  allocation write path MUST NOT create partners/bindings (voucher create still MAY)

### Approaches

Product forks in the plan are **closed**. They are not reopened here.

1. **Closed plan (chosen)** — Persist seller-validated allocations in Odoo. One MCP
   write tool `create_collection_allocation`. Connector stays read-only. Initial
   state `confirmed`; back-office `validated`/`rejected`. `UNIQUE(sheet_id, partner_id)`;
   second collection amends and bumps `revision`. Money is fungible (no
   voucher↔invoice pairing). Idempotency key on
   `collection.allocation.revision.request_id`, not the header. Copy review-snapshot
   immutability, voucher MCP validation order, sheet advisory lock on create, and
   UniqueViolation invalidate-and-reclassify.
   - Pros: matches closed decisions; reuses proven patterns; company `ir.rule`
     can classify other-company `request_id` hits the same way as `document_id`
   - Cons: sheet unlink semantics change when allocations exist; Document Review
     amount edits can move totals on a validated allocation (constraint 4 only
     while `confirmed`, by design)
   - Effort: High (four stacked work units; strict TDD)

2. **No remaining product fork** — Alternatives (ERP write-back, FIFO in Odoo,
   `request_id` on the header, voucher↔invoice pairing, extra MCP writes) were
   rejected in the plan. Implementation details that remain specified, not optional:
   binding-only partner lookup; PUT-style voucher superset on amend; `content_hash`
   replay when `request_id` is regenerated; subtract other allocations' applied amounts
   before comparing to fresh ERP balance; new migrate `19.0.1.25.0` rather than
   editing `COLLECTION_SEQUENCE_CODES` in 1.17.0.
   - Pros: propose can treat these as requirements
   - Cons: none for this phase
   - Effort: n/a

### Recommendation

Implement the closed plan. Spec work (unit 0) MUST:

- **ADD** capability `collection-allocations` (models, MCP tool, states, amend,
  revalidation, residual, ACL).
- **MODIFY** `collection-vouchers` for `allocation_id`, unlink-when-allocated, and
  write freeze.
- **MODIFY** `collection-sheets` (the main spec **does exist**) so unlink still
  unassigns vouchers when there are **no** allocations, and MUST be refused when
  allocations exist (`ondelete="restrict"`). Also cover the sheet-form notebook.
- Keep connector `_DISPATCH_OPS` unchanged. State that allocation MUST resolve
  `customer_identification` only against an existing customer binding and MUST NOT
  call `resolve_customer_partner`.

Stack delivery as the plan's four units (OpenSpec → models/security/seq → MCP →
views). `openspec/config.yaml` `strict_tdd: true`. `state.yaml` delivery strategy is
`auto-chain` / `stacked-to-main`.

### Risks

- **Sheet deletion spec vs FK restrict.** Existing collection-sheets requirement and
  tests 409/462 will fail unless the delta and tests distinguish empty sheets vs
  sheets with allocations.
- **Manifest/sequence tests.** `test_manifest_version_is_1_24_0` and the two-code
  sequence enum in `test_new_company_copies_sequences_seeds_types_empty_sellers`
  must move to 1.25.0 / include `collection.allocation` / `CA`.
- **Optional voucher `amount`.** MCP must reject null/≤0 amounts or residual math is
  meaningless.
- **Fungible money + prior-allocation subtraction.** Without subtracting other
  confirmed/validated lines on the same `external_invoice_id`, a later sheet (or
  another seller) can re-apply the full ERP balance. This is the correctness core
  while the connector stays read-only.
- **Global `UNIQUE(request_id)` + company `ir.rule`.** Same pattern as voucher
  `document_id`: hidden other-company hit must UniqueViolation → generic error, never
  leak ids. Related stored `company_id` on revision is mandatory for step-3
  classification.
- **Header `request_id` would be wrong on amend** (late retry of revision 1 would
  become a third amend). Key stays on the revision row.
- **O2M `Command.DELETE`** on `voucher_ids` would unlink the voucher record. Copy
  sheet `_sanitize_voucher_commands`.
- **Residual constraint vs Document Review.** If residual `>= 0` is enforced after
  `validated`, OCR amount correction cannot approve. Plan: constrain only while
  `confirmed`; chatter tracks drift.
- **No voucher↔sheet company constraint today.** Allocation must assert
  `allocation.company_id` equals every voucher's company (and sheet company).
- **Superseded line detail is not kept** (totals + chatter only). Accept as specified.
- **Review budget.** Four stacked units already assumed; models+guards+security+seq
  is the likely 400-line risk slice.
- **UI tests** assert current sheet form shape (no notebook). Unit 3 must update
  `test_collection_ui.py`.

### Ready for Proposal

Yes. Orchestrator should run `sdd-propose` for `collection-allocations` using this
exploration and the closed plan. Call out that **`collection-sheets` main spec
exists** and must receive a deletion/notebook delta — do not create a second sheets
capability from scratch. Do not implement Nebula, ERP write-back, retentions, or
sheet-report tools in this change.
