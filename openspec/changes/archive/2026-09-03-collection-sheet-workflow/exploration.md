# Exploration: collection-sheet-workflow

Tied to named change `collection-sheet-workflow`. Source of product decisions:
`~/.cursor/plans/collection-sheet-workflow_edec9c03.plan.md`. This exploration
recommends that plan; it does not invent a competing product.

Baseline: `origin/main` `68b6e2c`, manifest `19.0.1.32.0`. Working-tree production files
match HEAD (no unstaged model/view diffs). Parallel in-flight change `voucher-states-ui`
is in verify (`pass_with_warnings`); its production deltas are already on HEAD (voucher
Selection `draft` / `validated_seller` / `validated_collections`; stages kanban deleted;
Reassign kanban kept). Treat that as the new voucher baseline.

## Current State

### Sheet lifecycle (`models/collection_sheet.py`)

`collection.sheet.state` is a two-value Selection: `open` (default) or `closed`. Raw
`state` write is intercepted unless `collection_sheet_audited_state`; the only legal
targets today are `closed` → `action_close()` and `open` → `action_reopen()`. Any other
key raises `"Sheet state can only be changed via Close or Reopen."`

- `create()` one-open-checks only when the resulting state is `open`. Passing
  `state="closed"` on create skips that lock (plan: reject non-open creation).
- `action_close`: only from `open`; confirms every allocation
  (`collection_allocation_audited_state`), then writes `closed`.
- `action_reopen`: only from `closed`; one-open check; writes `open` then drafts
  allocations.
- `_open_sheets_for_seller` / `_resolve_open_sheet_id_for_create` /
  `_raise_if_seller_has_open_sheet` all filter `state == "open"` only.
- Membership freeze in `write()` and voucher helpers is `closed` only
  (`"Closed collection sheets cannot change membership. Reopen first."`).
- Unlink: `closed` refused even when empty; `open` unlinks draft allocations first
  (vouchers persist unassigned).
- Header helpers: `action_open_document_review` (saved sheet + company flag; **no**
  `state == open` check), `action_open_vouchers` (stat button),
  `action_open_voucher_reassign` (open + saved only).

### Allocation invariant (`models/collection_allocation.py`)

`draft` | `confirmed`; default `draft`. `_check_sheet_state_iff` (skipped during audited
writes): draft **iff** sheet `open`; confirmed **iff** sheet `closed`. Raw allocation
`state` write refused except Close/Reopen context. Frozen fields when confirmed:
`line_ids`, `voucher_ids`, `partner_id`, `sheet_id`. Totals already include stored
`total_debt`, `total_vouchers`, `total_applied`, `residual`
(`total_debt − total_applied`). There is no server-side sheet-state write guard on
**draft** allocations beyond the iff constraint.

### Debt lines (`models/collection_allocation_line.py`)

Snapshot rows (`external_invoice_id`, `document_kind`, balances, `amount_applied`).
Related stored `currency_id` / `company_id` from the allocation. **No** related
`sheet_id` or `partner_id`. **No** `write()` override — Closed/Cancelled RPC edits of
`amount_applied` would only be blocked today if the parent allocation is `confirmed`.

### Report freeze (`models/collection_sheet_report.py`)

Second `_inherit` of `collection.sheet`. Recon inputs (`commission_percent`,
`cash_on_hand`, `commission_withheld`) refuse writes when **any** record is `closed`.
Open sheets may edit. Reopen keeps stored values. `_collection_report_data()` and
`action_print_xlsx` have **no** state gate; bound qweb-pdf Print
(`report/collection_sheet_report.xml`, `binding_model_id` = `collection.sheet`) is
likewise state-agnostic.

### Voucher membership, reassign, follow (`models/collection_voucher.py`)

Already on the voucher-states-ui baseline: Selection `draft` / `validated_seller` /
`validated_collections`; `action_validate_seller`; Document Review is the only path to
`validated_collections`; unlink only `draft`.

Still present (this change removes):

- `_read_group_partner_ids` + `_readable_reassign_sheet` (context
  `collection_reassign_sheet_id`).
- `_prepare_partner_reassign_write` / `_vals_with_partner_allocation`: Customer change
  **auto-attaches** the unique draft same-sheet allocation, else unassigns and posts
  chatter.
- Closed-only freeze: `_ensure_sheet_membership_unlocked`,
  `_ensure_partner_reassign_unlocked`.

Kept: `_check_voucher_allocation_partner` (`UserError` if voucher customer ≠ allocation
customer). Plan: keep this constraint; drop auto-follow so an allocated voucher must be
unassigned before Customer can change.

### Sheet form (`views/collection_views.xml`)

Header today: Close (`state != 'open'`), Reopen (`state != 'closed'`), Document Review
(`not id or not document_review_enabled` — **also on closed**), Reassign Customers
(`not id or state != 'open'`), Export XLSX (unconditional). Statusbar `open,closed`, not
clickable.

Notebook: **Allocations only**. Embedded list `create="false" delete="false"` columns:
`name`, `partner_id`, `state`, `total_vouchers`, `total_applied`, `residual`. No
`total_debt`. `voucher_ids` is **not** on the form; counted Vouchers **stat button**
opens `action_open_vouchers`. Reassign kanban XMLID
`view_collection_voucher_reassign_kanban` still installed.

### Allocation form (`views/collection_allocation_views.xml`)

Readonly when `state == 'confirmed'` for sheet/partner, voucher M2M (`no_create` /
`no_create_edit`), and Customer Debt `line_ids`. No sheet-state modifiers
(`open`/`proposal`). Voucher membership is editable on any draft allocation, including
if later reached while the sheet is Proposal.

### MCP open-sheet lookup/create

`get_collection_allocation` (`tools/allocation_lookup.py`) uses
`_open_sheets_for_seller` only; never `_resolve_open_sheet_id_for_create`. No open sheet
→ `{allocation: null}`. Multi-open leftover → existing `UserError`. Found allocation on
that open sheet must be `draft`.

`create_collection_allocation` auto-assigns via voucher create →
`_resolve_open_sheet_id_for_create` (lock, reuse the single open sheet or create one).
`_collection_allocation_vouchers` then requires `sheet.state == "open"` in the current
company. Proposal/Closed/ Cancelled sheets are invisible to both lookup and create **as
long as those helpers keep filtering `open` only**. That is the settled MCP contract: a
seller MAY start a new Open sheet while an older one is in Proposal. Nebula stays out of
scope.

### Main specs that conflict

- `openspec/specs/collection-sheets/spec.md`: two states; Close/Reopen; Allocations-only
  notebook; Reassign header + kanban; Document Review on saved sheets including closed;
  closed-only freeze.
- `openspec/specs/collection-allocations/spec.md`: **Draft default and confirm-on-close
  invariant** (`draft` iff `open`, `confirmed` iff `closed`; Close confirms; Reopen
  drafts).
- `openspec/specs/collection-vouchers/spec.md`: **Partner write follows allocation**;
  **Context-gated partner group_expand**; closed-only `partner_id` freeze.
- `openspec/specs/collection-sheet-report/spec.md`: recon writable on open, frozen on
  closed; Reopen keeps values.
- `openspec/specs/document-review/spec.md`: queue eligibility is still worded `pending`
  in main spec; voucher-states-ui delta (in-flight) remaps queue to `validated_seller` +
  proof and drops Reject. Confirm gate in **this** change depends on that
  `validated_collections` terminal state.

### Tests that encode the old workflow

- `tests/test_collection_sheet.py` — Close/Reopen sync, one-open, closed freeze,
  reassign action, unlink.
- `tests/test_collection_ui.py` — statusbar `open,closed`; Close/Reopen; Document Review
  without Open-only; Reassign after Review; Allocations only (explicitly **forbids** a
  Vouchers notebook page); allocation columns include `state` + `total_applied`; partner
  `group_expand`.
- `tests/test_collection_allocation.py` — confirm-on-close / draft-on-reopen.
- `tests/test_collection_voucher.py` — partner-follow inject; group_expand.
- `tests/test_collection_document_review.py` — uses `action_close()` to leave Open;
  header review still available after close in some paths.
- `tests/test_collection_sheet_report_data.py` / `tests/test_collection_sheet_xlsx.py` /
  `tests/test_collection_mail.py` / `tests/test_collection_company_migration.py` —
  Close/Reopen and manifest version.

## Affected Areas

- `models/collection_sheet.py` — four-state Selection; audited `action_confirm` /
  `action_close` / `action_cancel` / `action_open`; drop `action_reopen`; Confirm review
  gate; freeze Proposal+Closed+ Cancelled membership; debt-line One2many; drop reassign
  action; one-open still counts `open` only; reject non-open create.
- `models/collection_allocation.py` — iff invariant: draft on Open/Proposal/Cancelled,
  confirmed only on Closed; writable only Open/Proposal; Close confirms; Cancel drafts;
  Confirm does **not** confirm allocations.
- `models/collection_allocation_line.py` — stored related `sheet_id` (+ read-only
  customer); `write`/`unlink` guards so Closed/Cancelled cannot change `amount_applied`
  via RPC.
- `models/collection_sheet_report.py` — freeze recon on Closed **and** Cancelled; keep
  editable on Open **and** Proposal.
- `models/collection_voucher.py` — drop group_expand / reassign context / auto
  allocation-follow; extend membership + business-field freeze to
  Proposal/Closed/Cancelled; chatter remains writable; keep partner/allocation
  constraint.
- `views/collection_views.xml` — header buttons per state; three notebook pages;
  Allocations columns; Vouchers tab (open existing in Open only; no
  create/remove/delete); Debt tab; `<delete>` reassign kanban; keep Export XLSX; leave
  bound Print.
- `views/collection_allocation_views.xml` — sheet-state readonly / Open-only voucher
  membership even off the sheet form.
- `tools/allocation_lookup.py` / `tools/collection_allocation.py` — **read-only check**:
  no semantic change if `_open_sheets_for_seller` stays `open`. Add regressions that
  Proposal does not block a new Open sheet.
- `__manifest__.py` — bump to `19.0.1.33.0` (1.33.0 unused; 1.31.0 is voucher-states-ui
  remap; 1.32.0 is residual_reason). No sheet-state SQL remap. Related stored line
  fields recompute on `-u`.
- `openspec/specs/collection-sheets/spec.md`, `collection-allocations/spec.md`,
  `collection-vouchers/spec.md`, `collection-sheet-report/spec.md`,
  `document-review/spec.md` (Open-only Review header) — delta specs in this change
  folder only.
- Tests listed above; plus allocation-line tests for the flat Debt relation; PDF/XLSX
  regressions in all four states.
- `AGENTS.md` / `readme/` fragments — workflow and notebook docs.
- **Do not edit** `openspec/changes/voucher-states-ui/**` or its SDD lock.

### File-level overlap with in-flight `voucher-states-ui`

| File                                             | voucher-states-ui                              | this change                                       |
| ------------------------------------------------ | ---------------------------------------------- | ------------------------------------------------- |
| `models/collection_voucher.py`                   | states, review, unlink                         | freeze, drop follow/reassign helpers              |
| `views/collection_views.xml`                     | voucher list/search/form, keep Reassign kanban | sheet header/notebook; **delete** Reassign kanban |
| `tests/test_collection_ui.py`                    | voucher filters, keep reassign asserts         | replace sheet notebook/button/reassign asserts    |
| `tests/test_collection_voucher.py`               | lifecycle                                      | partner-follow / freeze                           |
| `tests/test_collection_sheet.py`                 | seller-validate leftovers                      | lifecycle rewrite                                 |
| `tests/test_collection_document_review.py`       | queue `validated_seller`                       | Open-only Review; Confirm gate                    |
| `tests/test_collection_allocation.py`            | default voucher state                          | sheet iff + editability                           |
| `tests/test_collection_mail.py`                  | voucher tracking                               | sheet Confirm/Close/Cancel/Open tracking          |
| `tests/test_collection_sheet_report_data.py`     | print voucher keys                             | four-state recon freeze; print all states         |
| `__manifest__.py`                                | planned 1.31.0; tree is 1.32.0                 | **1.33.0** unless they take it first              |
| `openspec/specs/collection-vouchers/spec.md`     | MODIFIED lifecycle/UI                          | MODIFIED follow/group_expand/freeze               |
| `openspec/specs/collection-allocations/spec.md`  | drop rejected gate                             | MODIFIED confirm-on-close iff                     |
| `openspec/specs/document-review/spec.md`         | queue/Approve                                  | Open-only sheet header                            |
| `openspec/specs/collection-sheet-report/spec.md` | print keys                                     | recon freeze states                               |

Low overlap (this change owns): `collection_sheet.py`, `collection_allocation.py`,
`collection_allocation_line.py`, `collection_sheet_report.py` write guard,
`collection_allocation_views.xml`.

If voucher-states-ui still mutates overlapping files during remaining verify, rebase
this change on that HEAD; do not edit their artifacts.

## Approaches

1. **Plan four-state workflow (Open → Confirm → Proposal; Close / Cancel / Open)** —
   Extend Selection; audited actions; Confirm requires every member voucher
   `validated_collections`; allocations stay draft through Proposal and confirm only on
   Close; Cancel drafts and freezes; Open from Cancelled reuses one-open. Rebuild sheet
   notebook (Allocations / Vouchers / Debt). Remove Reassign UI + auto-follow; keep
   partner constraint. MCP open helpers unchanged.

   - Pros: Matches settled product; Proposal does not consume the one-open slot; review
     gate is a standard `UserError`; no row remap for existing Open/Closed.
   - Cons: Large spec+test+view blast; overlaps voucher-states-ui files; exceeds
     400-line review budget (chained PRs already in `state.yaml`
     `delivery_strategy: auto-chain`).
   - Effort: High

2. **Keep two states; tabs-only** — Add Vouchers/Debt pages and drop Reassign without
   Proposal/Cancelled.

   - Pros: Smaller diff.
   - Cons: Contradicts the source plan (no review gate, no Proposal edit window, MCP
     still blocked by a single Open sheet).
   - Effort: Medium

3. **Proposal as a flag on Open** — Boolean `is_proposal` while `state` stays
   `open`/`closed`.
   - Pros: Avoids Selection migration.
   - Cons: Breaks one-open (`_open_sheets_for_seller` would still see Proposal as open)
     unless every helper is special-cased; worse than four explicit states.
   - Effort: High (hidden complexity)

## Recommendation

Implement **approach 1** exactly as the source plan.

Concrete contracts for later spec/design (not product reopen):

- Selection keys: `open`, `proposal`, `closed`, `cancelled`. Default `open`. Existing
  Open/Closed rows stay as-is (no SQL remap).
- Transitions: Open `--Confirm-->` Proposal; Proposal `--Close-->` Closed; Proposal
  `--Cancel-->` Cancelled; Closed `--Cancel-->` Cancelled; Cancelled `--Open-->` Open.
  Reject all other raw writes. Drop `action_reopen` (Closed is not reopened in place).
- Confirm gate: `UserError` unless every `voucher_ids.state == validated_collections`
  (missing proof / disabled review / not yet reviewed all block). Empty `voucher_ids` is
  vacuously true — keep that unless spec later forbids empty Confirm.
- Allocations: draft on Open, Proposal, Cancelled; confirmed only on Closed. Writable
  only Open/Proposal. Close confirms all; Cancel drafts all (no-op if already draft).
  Confirm does not touch allocation `state`.
- Freeze: voucher membership + voucher business fields frozen in
  Proposal/Closed/Cancelled; allocations + debt `amount_applied` + recon editable in
  Open/Proposal; everything read-only in Closed/Cancelled except chatter and Print/XLSX.
- Unlink (plan-silent; recommended): refuse Proposal/Closed/Cancelled; Open still
  cascades draft allocations.
- Tabs: Allocations columns Reference, Customer, `total_debt`, `total_vouchers`,
  Residual (drop State and `total_applied`); draft add/edit/delete in Open/Proposal
  opening the allocation form. Vouchers: all `voucher_ids`; open/edit existing only in
  Open; no create/remove/delete from the tab. Debt: sheet One2many of lines; only
  `amount_applied` editable in Open/Proposal; create/delete off.
- Reassign: delete header button, kanban XMLID (upgrade `<delete>`), `group_expand`,
  auto-follow. Constraint remains.
- MCP: do not change `_open_sheets_for_seller` domain. Prove with tests that a Proposal
  sheet does not satisfy lookup/create open-sheet semantics.
- Manifest: `19.0.1.33.0`. If voucher-states-ui consumes 1.33.0 before this ships, use
  the next unused version. Related debt fields: ORM recompute on upgrade; no sheet-state
  migrate folder required.
- Strict TDD (`openspec/config.yaml`): failing lifecycle, review-gate, tab, and
  editability tests before production code.
- Nebula: out of scope.

## Risks

- Parallel `voucher-states-ui` still in verify; overlapping `collection_views.xml` /
  `collection_voucher.py` / UI tests may move underfoot. Reassign kanban is **kept** by
  that change and **deleted** by this one — sequence must be voucher-states-ui first,
  then this delete.
- Confirm gate depends on voucher-states-ui terminal state `validated_collections`. If
  that change rolled back, the gate has no baseline.
- `_check_sheet_state_iff` and dozens of Close/Reopen tests will fail in RED until the
  four-state model lands; apply must stay strictly TDD and chained.
- Draft allocations on Cancelled are frozen only if **sheet-state** guards are added;
  confirmed-only freeze is not enough.
- Allocation form reached from the menu can bypass sheet-tab modifiers unless
  server-side + allocation view both key off sheet state.
- Empty-voucher Confirm is vacuously allowed; product may want a later explicit refuse —
  flag in spec, do not invent a block now.
- 400-line review budget: High; `delivery_strategy` is already `auto-chain` /
  `stacked-to-main`.

## Ready for Proposal

Yes. Orchestrator should run `sdd-propose` (then spec/design/tasks) using this
exploration and the source plan as agreed behavior. Do not reopen four-state
transitions, tab columns, Reassign removal, MCP open-sheet semantics, or the
`19.0.1.33.0` bump. Name voucher-states-ui file overlap in the proposal risks. Do not
acquire or overwrite the voucher-states-ui SDD lock.
