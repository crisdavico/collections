## Exploration: two-step-seller-close-and-seller-deposit

Settled design: `/home/crisd/.claude/plans/cash-banked-and-cash-ancient-volcano.md`. Do
not reopen product choices. Line numbers below are live source, not the plan's citations
when those drifted. CodeGraph was queried first with `projectPath` on both addon roots;
blast-radius line numbers were stale versus verbatim bodies, so truncated symbols were
confirmed with Read.

Git: `git rev-parse --show-toplevel` from either addon cwd returns the parent Doodba
repo `/home/crisd/projects/seedian/seedian`. Both addons still have a local
`.codegraph/` index. Indexes were used; they were not rebuilt.

### Current State

Seller Close is already shipped (`19.0.1.42.0`) as **one atomic MCP write**.
`close_collection_sheet` requires both amounts and `action_seller_close` writes them
together with `state='submitted'`. Confirm already runs from `submitted`, not `open`.
AGENTS.md's sheet-lifecycle paragraph still claims `submitted` is dormant — that prose
is stale; the MCP section of the same file is current.

**Seller close requires both amounts (confirmed)**

- `tools/collection_sheet_close.py:26-29` schema `required` includes `seller_id`,
  `cash_on_hand`, `commission_withheld`.
- Same file `:51-55` signature, `:73-78` normalize-or-UserError, `:88`
  `action_seller_close(cash_on_hand=cash, commission_withheld=withheld)`.
- `models/collection_sheet.py:226-242` `action_seller_close`: lock, re-read, refuse
  non-`SELLER_SHEET_STATES`, then write `{"state": "submitted"}` plus any non-None
  amounts. Keyword defaults are `None`; `_dispatch_submitted_state_write:255-266` and
  `tests/common_connector.py:273,291` already call it argument-free.
- `action_confirm:268-283` already requires `submitted` (every member
  `validated_collections`). There is **no** `cash_declared_at` today.

**Declaration window is open-only (confirmed; this is the backwards part)**

- `models/collection_sheet_report.py:31` `_SELLER_DECLARATION_FIELDS`.
- `:69-79` refuses those writes when `sheet.state not in SELLER_SHEET_STATES`.
- `models/collection_common.py:41` `SELLER_SHEET_STATES = frozenset({"open"})`.
- After `submitted`, the declaration is uncorrectable.
- Form `views/collection_views.xml:512-516` `readonly="state != 'open'"` on both
  Monetary fields.
- `tests/test_collection_sheet_report_data.py:291-299` asserts submitted freezes
  declarations while `commission_percent` stays writable.

**Named sheet-state sets (load-bearing for U4/U5c)**

| Set                           | Live                              | File                      |
| ----------------------------- | --------------------------------- | ------------------------- |
| `SELLER_SHEET_STATES`         | `{"open"}`                        | `collection_common.py:41` |
| `ADMIN_EDITABLE_SHEET_STATES` | `{"open", "submitted"}`           | `:42`                     |
| `DRAFT_SHEET_STATES`          | open/submitted/proposal/cancelled | `:43`                     |
| `FROZEN_SHEET_STATES`         | `{"closed", "cancelled"}`         | `:45`                     |

`submitted` is **not** frozen. Receipt-value writes and sheet membership writes are
legal on a submitted sheet. That is why a deposit can land on the frozen seller sheet
and why replacement can mutate receipts before Confirm.

**Tendered vs collected (echeck / retention confirmed missing)**

- `collected_total` = sum of **all** `_collection_report_voucher_blocks`
  (`collection_sheet_report.py:102, 270-313`). Every catalog code, including `echeck`,
  `retention_certificate`, and `cash`, feeds Total Cobrado.
- `_collection_report_tendered:345-367` only buckets `cash_deposit`, `check`,
  `bank_transfer`, plus the `cash_on_hand` field. No `echeck`, no
  `retention_certificate`, no `cash` vouchers (cash enters tendered only via the
  declaration field — intentional), no future `seller_deposit`.
- Algebra at `:370-393`: `net_due = collected − withheld`,
  `difference = tendered − net_due`. Leave this ladder alone.
- `mismatch:106-109` compares allocation `total_vouchers` to `collected_total`. A
  `seller_deposit` with `allocation_id = False` would inflate collected and pin
  `mismatch` True unless U3 excludes it from voucher blocks.
- XLSX recon header `report/collection_sheet_xlsx.py:685-716` cross-links
  deposits/checks/transfers to voucher-block SUMs; formula ladder `:744-780`. QWeb table
  `report/collection_sheet_templates.xml:382-423`.

**Core vs satellite receipt-value invariants (confirmed)**

Core `models/collection_receipt_value.py`:

- `_check_same_allocation:53-61` — **allocation** boundary
  (`voucher.allocation_id != receipt.allocation_id`).
- `_check_voucher_split_cap:63-80` — one batched `search`, then **skips** values whose
  receipt allocation ≠ voucher allocation (`:72-73`). Weaker cap.
- `_amount_positive:44-47` `CHECK(amount > 0)` — exact-cent slicing is load-bearing
  (U5a).
- `currency_id` related from receipt (`:32-35`); cap compares `voucher.currency_id`
  (`:77`). Pre-existing disagreement, newly reachable.

Satellite `collection_receipt_proposal/models/collection_receipt_value.py`:

- `_check_same_allocation:12-31` — **sheet** boundary (correct invariant).
- `_check_voucher_split_cap:33-57` — sheet-wide, **one search per voucher** (N+1). Lift
  semantics, not this loop.
- File must survive for `_proposal_card_payload:59-77`.

Core has **no** `receipt_value_ids`. Reverse o2m exists only as `proposal_value_ids` on
`collection_receipt_proposal/models/collection_voucher.py:12-17`.
`proposal_free_amount:22-34` is `amount − assigned` with no replaced term.

Receipt totals depends-redeclaration lives only in the satellite
`collection_receipt_proposal/models/collection_receipt.py:17-39`. Core
`_compute_totals:103-110` still
`@api.depends("value_ids.amount", "line_ids.amount_applied")`. Comment at satellite
`:17-24` is accurate: writing an existing `amount_applied` raises "Cannot convert
collection.receipt.line_ids to SQL" without the field-level `depends=`.
`models/__init__.py:5` imports that file.

Leave in satellite (do **not** lift): `_check_voucher_allocation_partner` /
`_proposal_allocation_owner_ok` (`collection_voucher.py:37-64`) and
`collection.allocation._check_voucher_partners` (`collection_allocation.py:454-462`).
Those relax partner identity for largest-share owner.

**Board primitives (U5a move + U6 lock)**

On `collection_receipt_proposal/models/collection_sheet.py`:

- `_proposal_shrink_value:453-463` — unlinks when remainder rounds `<= 0`; grow only
  adds `amount` → silent sub-cent leak (plan U5a).
- `_proposal_grow_value:466-486`.
- `_proposal_receipt_get_or_create` on allocation `:185-192`.
- `_proposal_fifo_key` on allocation `:164-166`
  `(due_date or date.max, invoice_number or "")`.
- `_proposal_transfer_plan:292-349` — pool path uses `proposal_free_amount` as maximum
  (`:312-319`).
- `_proposal_sync_voucher_owner:489-515` — empty `candidates` sets
  `allocation_id = False` (`:499-502`). Called unconditionally after transfer (`:384`).
- Pool at `_proposal_board_payload:183-187` — `proposal_free_amount > 0`. Replaced cash
  with zero values reappears at full amount. Excess deposit also appears.
- Pool payload `:86-100` includes `partner_id` / `partner_name`. A sentinel deposit
  would **not** be a blank customer; it would name the sentinel. Drag hazard is
  unchanged.

**Voucher create / membership (U5c path)**

- `partner_id` `required=True` `models/collection_voucher.py:38-45`. Sentinel partner
  avoids a NOT NULL migration.
- `_apply_open_sheet_auto_assign:237-253` only when `seller_id` set **and** `sheet_id`
  omitted; resolves via `_resolve_open_sheet_id_for_create` which only sees
  `SELLER_SHEET_STATES` (`open`). Deposit MCP **must** pass `sheet_id`.
- `_ensure_sheet_membership_unlocked:377-391` uses `_sheet_is_frozen:373-375` = not in
  `ADMIN_EDITABLE_SHEET_STATES`. `submitted` is allowed.
- `_write_review_decision:645-653` writes `validated_collections` under
  `collection_audited_state`. `document_review_enabled` defaults `False`
  (`res_company.py:28`). Trigger replacement on **that write**, not on
  `action_review_approve`.
- Catalog: `collection_common.py:14-22` seven codes; XML
  `data/collection_document_type_data.xml` seven XMLID rows. No `seller_deposit`.
- `_assert_new_work` `res_company.py:65-68` rejects unknown codes against
  `allowed_document_type_ids`. Existing companies need `migrations/19.0.1.43.0/` calling
  `_collection_enable_all_document_types`.
- Manifest `19.0.1.42.0`. Leftover pin:
  `tests/test_collection_company_migration.py:196-218` forbids `migrations/19.0.1.42.0/`
  (and several other folders). Going to `.43.0` keeps that pin. Do **not** add
  `19.0.1.42.0/`.
- Inline `"open"` leftover scanner `:29-60` + assertion `:793-801`. New
  `state == "open"` gates in `models/` or `tools/` fail CI. Named frozenset
  `SELLER_DECLARATION_STATES = frozenset({"submitted"})` is the house pattern;
  `"submitted"` itself does not trip this regex, but new `"open"` checks would.
- `SEVEN_TYPE_CODES:15-19`, `CATALOG_XMLIDS` in
  `test_collection_company_settings.py:9-22` (`len == 7` at `:35-39`), voucher selection
  `test_collection_voucher.py:361-378`.

**MCP gates that block a no-customer deposit (confirmed)**

`create_collection_allocation` cannot create a remittance:

1. Schema required `customer_identification` `:118-124`.
2. `len(vouchers.partner_id) != 1` refused `:704-705`.
3. Sheet must be in `SELLER_SHEET_STATES` (`open`) `:711-717`.
4. Binding must exist and match voucher partner `:725-736`.

`get_collection_sheet_pdf` `tools/sheet_report.py:110-116` uses
`_open_sheets_for_seller` (`collection_sheet.py:110-118`, domain `SELLER_SHEET_STATES`).
A submitted sheet returns `{sheet: null}`. Widen **at this call site only** — not inside
`_open_sheets_for_seller`, which also backs `_raise_if_seller_has_open_sheet` /
one-open.

**Cancel / freeze (no reversal)**

- `action_cancel:324-334` writes `cancelled` **before** drafting allocations.
- `cancelled ∈ FROZEN_SHEET_STATES` then blocks receipt-value writes
  (`collection_receipt_value.py:82-87`, `raise_if_sheet_frozen`).
- Reversing on Cancel is both blocked and wrong (money is in the bank).

**Out of scope (confirmed)**

- `collection_connector.py:99-101` `create_receipt` dispatches a raw recordset. Adapter
  stub `tests/common_connector.py:188-191`. No ERP serialization; replacement is
  Odoo-internal. Note in connectors spec as follow-up. Do not touch
  `_sqlite_create_receipt`.
- Nebula is out of this change. U4 **is** a hard MCP contract break: Nebula's
  `close_collection_sheet` currently sends the two amounts (`nebula-agent` AGENTS.md
  verified 2026-09-07). Record a follow-up; do not implement the agent here. Additive
  tools (`declare_collection_cash`, `create_seller_deposit`) and PDF widening are also
  agent follow-ups.

**Stale leftovers to ignore**

`openspec/changes/2026-09-04-document-review-editable-ocr` and
`openspec/changes/expose-allocatable-customer-debt`. Archived seller-close change is
`openspec/changes/archive/2026-09-07-seller-close-submitted-sheet/` — that exploration
is pre-ship; live code has moved on.

**Edit-authority**

`collection/openspec/config.yaml` `apply.roots` is only `…/private/collection`. U1
deletes satellite constraint methods + `collection_receipt.py`; U6 edits the board.
Those paths sit in `collection_receipt_proposal` (its own `apply.roots`). Propose/tasks
MUST name the sibling root so apply can grant consent rather than block.

### Affected Areas

**collection (core)**

- `models/collection_common.py` — eighth catalog code; `SELLER_DECLARATION_STATES`.
- `models/collection_receipt_value.py` — lift sheet boundary + sheet-wide cap (delete
  `:72-73` filter; keep batched search).
- `models/collection_receipt.py` — field-level `depends=` from satellite.
- `models/collection_voucher.py` — `receipt_value_ids`, `replaced_amount`; write-hook on
  `validated_collections`.
- `models/collection_sheet.py` — drop amount writes from `action_seller_close`; add
  `action_declare_cash`; Confirm gate on `cash_declared_at`;
  `_submitted_sheets_for_seller`.
- `models/collection_sheet_report.py` — invert declaration window to `submitted`;
  exclude remittance from collected/mismatch; tendered buckets for `seller_deposit` +
  echeck + retention; `cash_banked`; keep `cash_on_hand` column name, change `string=`
  only.
- `models/collection_cash_replacement.py` — **new** immutable ledger (pattern:
  `collection_allocation_revision.py:56-73`).
- `models/__init__.py` — new model.
- `tools/collection_sheet_close.py` — drop amounts; return `cash.collected`.
- `tools/sheet_report.py` — PDF for submitted at call site.
- `tools/collection_seller_deposit.py` — **new** MCP write.
- `tools/collection_cash_declare.py` — **new** MCP write (name as propose settles; plan:
  `declare_collection_cash`).
- `tools/__init__.py` — import new mixins.
- `data/collection_document_type_data.xml` — eighth XMLID + sentinel partner
  (`noupdate`).
- `data/` company XMLID or setting to resolve the sentinel.
- `migrations/19.0.1.43.0/post-migrate.py` — union-all types. **Not** `19.0.1.42.0/`.
- `__manifest__.py` → `19.0.1.43.0`.
- `views/collection_views.xml` — recon readonly `submitted`; deposit
  `voucher_number`/`voucher_date` on Current + OCR + Seller Confirmed (`:187-228` and
  provenance twins). Do **not** add a second `partner_id`
  (`test_collection_ui.py:476-501`).
- `security/ir.model.access.csv` + `security/collection_security.xml` — ledger
  `1,0,1,0` + global company `ir.rule` (`test_collection_acl.py:137`,
  `test_collection_allocation_acl.py:168`).
- `AGENTS.md` — seven→eight catalog rows; version; **fix stale** `:200-201` (“submitted
  dormant / no Seller Close”).
- Specs: `collection-sheets`, `collection-sheet-report` (`:12-15, 37-40, 51-62`
  declaration window), `collection-receipts` (`:31-47` value boundary),
  `collection-vouchers`, `collection-connectors` (known follow-up). Tests listed in the
  plan U1–U5c (rewrite `test_collection_receipt.py:170-199` so mismatch raises from the
  intended constraint).

**collection_receipt_proposal (sibling, mandatory)**

- Delete constraint overrides in `models/collection_receipt_value.py:12-57`.
- Delete `models/collection_receipt.py` + `models/__init__.py:5` after the depends lift.
- Move split requirements from `openspec/specs/receipt-proposal-splits/spec.md:13-51`
  into core `collection-receipts`.
- U6: `proposal_free_amount` subtract `replaced_amount`; guard `_proposal_transfer_plan`
  and `_proposal_sync_voucher_owner` against remittance; assert replaced cash keeps
  `allocation_id`.
- Re-run `invoke test -m collection_receipt_proposal --mode=update` **and** collection
  after U1.

### Approaches

1. **Settled design (two-step close + remittance voucher + immutable ledger)** — Split
   freeze vs declaration; eighth code `seller_deposit` on a seeded sentinel partner;
   value-preserving cash→deposit replacement on receipts (quotation then invoice); lift
   sheet-wide receipt-value invariants into core; lock the board (U6) before the engine
   (U5b).

   - Pros: Matches the user's plan; no `partner_id` nullability change;
     `CHECK(amount > 0)` and recon algebra survive; replacement is auditable; deposits
     do not double-count collection.
   - Cons: MCP contract break for Nebula close; sibling edit-authority; several work
     units near the 400-line PR budget.
   - Effort: High (eight work units, two addons, migration `19.0.1.43.0`).

2. **Keep atomic close; only invert the declaration window** — Still require amounts on
   `close_collection_sheet`, but allow rewriting them on `submitted`.

   - Pros: Smaller MCP delta.
   - Cons: Seller still cannot know cash total until freeze; does not model the bank
     deposit or the phantom echeck/retention shortfall as a remittance. Rejected by the
     settled plan.
   - Effort: Low.

3. **Optional `partner_id` instead of a sentinel** — Drop `required=True` so deposits
   have no customer.
   - Pros: No dummy partner in the Planilla.
   - Cons: NOT NULL migration, spec inversion, blank board-pool rows, UNIQUE(sheet,
     partner) unused. Plan already rejected this.
   - Effort: Medium, with worse fallout than a sentinel.

### Recommendation

Propose the **settled design** as-is (Approach 1). Correct line numbers and stale
AGENTS.md claims in the proposal; do not substitute a different product.

Propose work units in plan order: **U1 → U2 → U3 → U4 → U5a → U6 → U5b → U5c**. U6 is
mandatory before U5b. Delivery strategy is `auto-chain` / `stacked-to-main`; keep units
as separate reviewable PRs (U4/U5a/U5b/U5c are each ~300–350 authored lines).

Keep column `cash_on_hand`. Add `SELLER_DECLARATION_STATES` as a named frozenset. Widen
PDF at `get_collection_sheet_pdf` only. Trigger replacement on `validated_collections`
write. Round slices; skip zeros; unlink only when the slice equals `value.amount`.
`cash_banked` from `seller_deposit` vouchers, never from the ledger.

### Risks

- **Nebula MCP break (follow-up, not this change):** dropping amounts from
  `close_collection_sheet` plus two new write tools. Agent will fail until updated.
- **Edit authority:** U1 satellite deletes and U6 live outside `collection`
  `apply.roots`. Apply will `blocked(edit_authority_missing)` unless the sibling root is
  granted.
- **Silent test coverage loss:**
  `test_over_split_zero_duplicate_or_mismatched_allocation_refused`
  (`test_collection_receipt.py:170-199`) can stay green under a sheet-wide cap while no
  longer exercising `_check_same_allocation`. Split the test.
- **N+1 if U1 copies the satellite cap loop** instead of deleting core `:72-73` only.
- **Sub-cent leak** if shrink unlinks a rounded-zero remainder while grow adds the
  unrounded slice (`_proposal_shrink_value:459-461`).
- **Board pool resurrection** if U5b ships without U6 (`proposal_free_amount` ignores
  `replaced_amount`; sync-owner clears `allocation_id`).
- **`cash_banked` slip:** summing `cash_deposit` (customer deposit) with
  `seller_deposit`.
- **Existing companies** missing `seller_deposit` on the allow-list if `19.0.1.43.0`
  migrate is skipped; `_assert_new_work` then rejects every deposit.
- **Leftover scanner** if U4 adds inline `"open"` state checks in `models/` or `tools/`.
- **400-line budget:** do not merge U4+U5 or U5b+U5c into one PR.

### Ready for Proposal

Yes. The design is settled and verified against live source. The orchestrator should run
**sdd-propose** for `two-step-seller-close-and-seller-deposit` with this exploration as
context: Approach 1, work-unit order U1–U4 then U5a/U6/U5b/U5c, sibling edit-authority,
Nebula follow-up, no interactive product questions.
