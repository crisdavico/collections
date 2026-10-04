## Exploration: Seller Close for Collection Sheets (`submitted`)

CodeGraph was queried first (`projectPath` = this addon). Results truncated onto
`collection_voucher.py` and some blast-radius line numbers were stale versus the
verbatim bodies; remaining sites were confirmed with Read / ripgrep. Do not treat
CodeGraph blast-radius numbers as authoritative.

Settled product decisions in
`/home/crisd/.claude/plans/with-all-this-information-idempotent-lynx.md` are confirmed
by live code. Implement that approach. Do not reopen product choices.

### Current State

Four-state sheet today: `open` / `proposal` / `closed` / `cancelled`. `open` still means
both “seller live sheet” and “administration may edit.” Confirm is `open` → `proposal`
and requires every member `validated_collections`. MCP write/lookup resolve only
`state = 'open'`. After Confirm, the next seller voucher auto-creates a new open sheet
with no error.

**1. Sheet Selection, dispatcher, actions, one-open, lock, guards**

| Symbol                              | Plan       | Live                                                                                                                                     |
| ----------------------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `_STATE_WRITE_ACTIONS`              | `:11`      | `models/collection_sheet.py:11-16` — `proposal→action_confirm`, `closed→action_close`, `cancelled→action_cancel`, **`open→action_open`** |
| Selection                           | `:65`      | `:65-71` four keys, default `open`, `tracking=True`                                                                                      |
| `_open_sheets_for_seller`           | fn `:110`  | fn `:105`; domain `("state", "=", "open")` still `:110`                                                                                  |
| `_lock_open_sheet_for_seller`       | `:106`     | `:115-123` — `pg_advisory_xact_lock(hashtext('collection.sheet.open.' \|\| company_id), seller_id)`                                      |
| `_resolve_open_sheet_id_for_create` | `:127`     | `:131-138`                                                                                                                               |
| create-state guard                  | `:155`     | `:155`                                                                                                                                   |
| write dispatcher                    | `:179`     | `:179-185`; generic error names Confirm, Close, Cancel, or Open                                                                          |
| membership write                    | `:190`     | `:188-190` `sheet.state != "open"`; same stale membership copy                                                                           |
| unlink                              | `:209`     | `:207-211` refuse any non-`open`                                                                                                         |
| `action_confirm`                    | `:214`     | `:213-228` source **`open` only**                                                                                                        |
| `action_close`                      | —          | `:230-267` source `proposal`; receipts then confirm allocations                                                                          |
| `action_cancel`                     | —          | `:269-281` sources `proposal`/`closed` only                                                                                              |
| `action_open` one-open block        | `:286-293` | `:283-300` including `_raise_if_seller_has_open_sheet` `:286-293`                                                                        |

**2. Freeze and Document Review**

- `_sheet_is_frozen` `models/collection_voucher.py:373-374` — `sheet.state != "open"`
  (plan `:374`).
- Fans out at `_ensure_sheet_membership_unlocked` `:377`,
  `_ensure_partner_reassign_unlocked` `:393`, `_ensure_sheet_business_fields_unlocked`
  `:402`.
- `_closed_membership_user_error` `:367-370` — leave verbatim (pinned in `AGENTS.md` and
  `test_collection_company_migration.py:328-331`).
- `_require_review_sheet` function `:567`, **`sheet.state != "open"` at `:578`** (plan
  cited `:578` as the function).
- `action_open_document_review` function `:302`, **gate `:306-308`**.
- `test_review_rpcs_refuse_non_open_sheet` loops `proposal`/`closed`/`cancelled`
  (`:389-410`); inverse RED for `submitted` belongs in PR 3.

**3. MCP allocation lockout**

`tools/collection_allocation.py:710-713` —
`if sheet.state != "open" or sheet.company_id != self.env.company`. This is the seller
lockout once members sit on a non-open sheet. New MCP creates still go through
`_resolve_open_sheet_id_for_create` and will open a **new** `open` sheet after close.
Keep this check on `SELLER_SHEET_STATES`.

**4. Recon fields**

`models/collection_sheet_report.py`:

- `_SHEET_STATE_LABELS` `:20-25` — four Spanish labels; add `"submitted": "Rendida"`.
- `_RECON_INPUT_FIELDS` `:30-32` — one set of three; split per plan.
- `cash_on_hand` / `commission_withheld` `tracking=True` (`:55`, `:60`).
  `commission_percent` has **no** tracking.
- `write` `:69-75` freeze iff `state in FROZEN_SHEET_STATES` **before**
  `super().write()` — this is what makes a combined audited
  `{state, cash_on_hand, commission_withheld}` write legal while still `open`.
- `_assert_recon_write_refused` `tests/test_collection_sheet_report_data.py:193-203` —
  split in PR 3.
- Four-state label count `:331` (`len(set(labels)) == 4`).

**5. Views**

`views/collection_views.xml`:

- Confirm starts `:419` — insert **Seller Close** immediately before it.
- Cancel `:433-437` `('proposal', 'closed')` → add `submitted`.
- Open `:439-443` → Reinstate / `action_reinstate`.
- Document Review `:445-450` `state != 'open'` → admin-editable set.
- statusbar `:460` `open,proposal,closed,cancelled`.
- readonly `:510` allocations `not in ('open', 'proposal')`; `:530` vouchers
  `!= 'open'`; `:556` debt `not in ('open', 'proposal')`.
- recon fields `:501-503` — **no** `readonly` (pre-existing UX bug; plan adds attrs).
- XLSX is last object button (`tests/test_collection_ui.py:1127-1128`).
- Sibling inherit xpath is `action_open_document_review` **after**, proposal-only —
  Seller Close before Confirm does not collide.

`views/collection_allocation_views.xml:137` `readonly="sheet_id.state != 'open'"` vs
`_membership_is_frozen` (`FROZEN_SHEET_STATES` only). Plan: widen minimally;
whitelist/blacklist mismatch is a pre-existing wart.

UI tests to retarget: `:1043` four-state statusbar name; `:1122` / `:1658-1660` /
`:1687-1689` exact Document Review invisible string; `:1561` `assertIn("!=",)` →
`not in`.

**6. Named sets**

`models/collection_common.py:41-43` today:

```
DRAFT_SHEET_STATES = frozenset({"open", "proposal", "cancelled"})
CONFIRMED_SHEET_STATE = "closed"
FROZEN_SHEET_STATES = frozenset({"closed", "cancelled"})
```

No `SELLER_SHEET_STATES` / `ADMIN_EDITABLE_SHEET_STATES`. `collection_sheet.py` does
**not** import these; it still uses `"open"` literals. Allocation error copy
`models/collection_allocation.py:353-358` enumerates “open, proposal, or cancelled”.
`raise_if_sheet_frozen` `:69-72` already uses `FROZEN_SHEET_STATES`.

Do **not** touch `_OUTSTANDING_INVOICE_STATES` (`models/collection_connector.py:19`).
`tools/customer_debt.py:85` is `if state == "open":` on **invoice** rows (plan `:85`
drifted off the constant).

**7. Tests / helpers / call-site count**

Live `action_confirm` mentions: **83 across 14 test files**, not plan’s “163 / 12
files”. Combined `action_confirm|close|cancel|open` ≈ 213 textual hits. Use ripgrep at
apply time; do not bake 163 into tasks.

`_force_sheet_state` **already exists** on `TestCollectionSheet`
(`tests/test_collection_sheet.py:131-133`). `tests/common_connector.py` is the fake
connector fixture, not a sheet helper — putting `force_sheet_state` / `advance_sheet_to`
there works as a shared import but is semantically odd. Hand-rolled audited bypasses
still match the plan: `test_collection_company_migration.py:624-636`,
`test_collection_mcp_allocation_lookup.py:500-504`,
`test_collection_document_review.py:66-74` and `:400-402`,
`test_collection_allocation.py:509-511`. Report data has its own `_advance` (`:180-183`
calls `action_confirm()` from `open`). Disabled-seller confirm is `:1311-1320` (plan
`:1310` is the blank line after the create-reject test).

**8. Doc / version tests**

`tests/test_collection_company_migration.py`:

- `:160-175` pins `"version": "19.0.1.41.0"` and leftover migrate tuple (includes
  `19.0.1.41.0`; **add `19.0.1.42.0`**). Additive Selection key: **no** migrate folder
  (precedent `migrations/19.0.1.33.0/` unlinks XMLID only, no sheet-state remap).
- leftover scanner `:282-302` (two-state statusbar / Close-or-Reopen /
  `action_reopen()`).
- four-state AGENTS `:304-332` and readme `:334-346` — rename to five-state and extend
  literals.

Manifest live `19.0.1.41.0`. `tools/__init__.py` currently imports `sheet_report`; PR 6
must add `collection_sheet_close`.

**9. MCP PDF as close-tool model**

`tools/sheet_report.py` is the 1:1 pattern: `@mcp_tool`, `seller_id` only,
`_collection_require_internal_seller`, `_open_sheets_for_seller`, `check_access`, no
`sudo()`, identity dict `:69-77`. Differences for close: `category="write"`, take
`_lock_open_sheet_for_seller` first, **0 open → `UserError` not `{sheet: null}`**,
amounts via `_collection_normalize_amount` (`tools/collection_voucher.py:168`). Factor
`_collection_sheet_identity` and reuse from the PDF tool. Tests: clone
`tests/test_collection_mcp_sheet_pdf.py` including `test_tool_source_never_sudoes`
(`:273-283`).

**10. Bare `"open"` outside `collection_common.py`**

Production models still compare `state` to `"open"` in `collection_sheet.py`,
`collection_voucher.py`, `collection_allocation.py` (error copy),
`collection_sheet_report.py` (labels), `tools/collection_allocation.py:710`. That is
exactly PR 1’s source-scan target. Invoice `open` in connector/customer_debt must stay
exempt.

**Archive precedent**

`openspec/changes/archive/2026-09-03-collection-sheet-workflow/` — four Selection keys,
audited dispatcher, MCP stays on `open`, Review Open-only, no SQL remap, leftover
scanner. Fifth state repeats that pattern.

**Same-domain in-flight (do not edit)**

- `openspec/changes/expose-allocatable-customer-debt/` — apply; additive `customer_debt`
  fields. Weak overlap (do not touch `_OUTSTANDING_INVOICE_STATES`).
- `openspec/changes/2026-09-04-document-review-editable-ocr/` — apply; Review OWL/OCR.
  Overlaps `_require_review_sheet` / header invisible — coordinate, do not edit that
  folder.

**Sibling**

`collection_receipt_proposal/tests/common.py:185-188` `_confirm()` marks vouchers
`validated_collections` then **`sheet.action_confirm()` from `open`**. Board is
`proposal`-only; inherit button after Document Review. `openspec/config.yaml`
`apply.roots` is **only** this collection repo. PR 5’s one-line sibling fix is a
**delivery-risk / edit-authority consent** item.

### Affected Areas

- `models/collection_common.py` — introduce `SELLER_SHEET_STATES` /
  `ADMIN_EDITABLE_SHEET_STATES`; widen draft/admin sets in later PRs.
- `models/collection_sheet.py` — Selection, dispatcher (two actions → `submitted`;
  **remove `"open"` entry**), `action_seller_close`, rename `action_open` →
  `action_reinstate`, Confirm source, Cancel sources, membership/unlink gates.
- `models/collection_voucher.py` — `_sheet_is_frozen` → not in admin-editable;
  `_require_review_sheet`.
- `models/collection_allocation.py` — `DRAFT_SHEET_STATES` + error copy `:355-358`.
- `models/collection_sheet_report.py` — labels; split recon field sets;
  freeze-before-super.
- `tools/collection_allocation.py:710` — keep seller-axis.
- `tools/sheet_report.py` + new `tools/collection_sheet_close.py` + `tools/__init__.py`.
- `views/collection_views.xml`, `views/collection_allocation_views.xml`.
- `tests/test_collection_*.py`, especially sheet / UI / report / mail / migration / MCP
  PDF clone / document review.
- `AGENTS.md`, `readme/DESCRIPTION.md` (oca-gen-addon-readme).
- `__manifest__.py` → `19.0.1.42.0`.
- Specs (main, not deltas): `collection-sheets`, `collection-sheet-report`,
  `collection-vouchers`, `document-review`, `collection-allocations`.
- Sibling `collection_receipt_proposal/tests/common.py` (outside apply.roots).

### Approaches

1. **Named state sets + fifth key `submitted` (settled plan)** — extend
   `collection_common.py`, editable-iff not frozen-iff, six stacked PRs to main,
   transitional Confirm `open|submitted` in PR 3 then drop `open` in PR 5.

   - Pros: matches four-state archive; fail-closed on new states; keeps MCP seller
     lockout on `open`; reviewable slices under 400-line budget.
   - Cons: ~test churn; sibling repo needs a consented one-line fix; Confirm remains
     unreachable when Document Review is off (pre-existing, flagged out of scope).
   - Effort: High (tests), Medium (production code).

2. **Flag or extra boolean on `open`** — rejected by the four-state archive and this
   plan (`open` would still match `_open_sheets_for_seller`).
   - Pros: smaller Selection.
   - Cons: every helper would special-case; seller lockout would leak.
   - Effort: Medium, wrong product.

### Recommendation

Implement the settled plan. Live code confirms the technique and almost every cited
line; record the drift table above rather than a competing design.

PR sequence (unchanged): (1) name sets + shared test helper, zero behavior; (2) dormant
`submitted` + docs/version `19.0.1.42.0`; (3) admin-editable `submitted` + recon split +
transitional Confirm; (4) `action_seller_close` + dispatcher + header; (5) Confirm
`submitted`-only + migrate call sites **atomically with sibling `_confirm()`**; (6)
Reinstate + MCP close tool.

Canonical spec headings for later `MODIFIED` deltas (match exactly):

- `collection-sheets`: Open/closed lifecycle; At most one open sheet per seller (new
  operations); Closed sheet membership freeze; Confirm review gate; Four-state sheet
  editability; Collection Sheets UI; Saved-sheet header action opens Document Review;
  Membership, dates, and deletion.
- `collection-sheet-report`: Sheet reconciliation inputs; PDF and XLSX available in all
  sheet states; Read-only MCP tool get_collection_sheet_pdf.
- `collection-vouchers`: Sheet-state voucher field guards; Create auto-assign to open
  sheet.
- `document-review`: Sheet identifier required on review operations (sheet MUST be
  `open` today).
- `collection-allocations`: Draft default and confirm-on-close invariant; MCP open sheet
  is state open only; Cancelled and Closed allocation write guards.

### Risks

- **`apply.roots` excludes `collection_receipt_proposal`.** PR 5 cannot land that
  `_confirm()` fix without edit-authority consent or a separate change in that git repo.
  Every sibling test funnels through `tests/common.py:188`.
- **Call-site count drift (83 confirm mentions / 14 files, not 163 / 12).** Budget the
  mechanical PR 5 from a fresh ripgrep, not the plan’s 163.
- **In-flight Review OCR change** may touch the same `_require_review_sheet` / header
  invisible string.
- **Confirm unreachable when Document Review is off** (`validated_collections` only from
  `_write_review_decision`) — pre-existing; `submitted` makes handover undischargeable.
  Out of scope per plan; document it.
- **No seller-vs-admin ACL** — lockout is only MCP/state gates. Future write tools must
  use `SELLER_SHEET_STATES`.
- **Mistaken close has no undo to `open`**; remedy is dragging members between the new
  `open` sheet and the `submitted` one (both admin-editable).
- **`date_from`/`date_to` can still shift after handover** because membership stays
  mutable in `submitted`.
- **ORM voucher create with explicit `sheet_id` skips the advisory lock** — plan calls
  this benign; comment it, do not add `FOR UPDATE`.

### Ready for Proposal

Yes. Orchestrator should run **sdd-propose** for `seller-close-submitted-sheet` using
this exploration and the settled plan. Do not reopen gate, naming, cancel/reinstate,
recon split, or MCP `seller_id`-only close. Flag sibling edit-authority and the
83-vs-163 count in the proposal. Strict TDD. One OpenSpec change,
`chain_strategy: stacked-to-main`, six PRs.
