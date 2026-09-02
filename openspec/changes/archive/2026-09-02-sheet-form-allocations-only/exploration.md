# Exploration: sheet-form-allocations-only

Collection Sheet form should show **only Allocations** (not Vouchers), keep an auditable
path to the sheet's vouchers via a smart button with count, add Customer (`partner_id`)
on the embedded allocations list, and expose `sheet_id` on voucher views so membership
can still be unlinked.

Settled product decisions are taken as given. Approaches below exist only to record why
the settled plan is technically sound, plus one small helper-message amendment.

CodeGraph indexed Python models (`collection.sheet`, `collection.voucher`,
`collection.allocation`) but not XML view arches. View and test facts below come from
Read of `views/collection_views.xml` and `tests/test_collection_ui.py` after that gap.

## Current State

### Sheet form notebook (`views/collection_views.xml`)

`collection.view_collection_sheet_form` (lines 429–514) is a form with Close / Reopen /
Document Review in the **header**, then `<sheet>` with title, seller, stored `date_from`
/ `date_to`, and a **single notebook with two pages**:

- **Vouchers** (lines 484–496): `voucher_ids` with `widget="many2many"`,
  `readonly="state == 'closed'"`, embedded `<list>` of `name`, `partner_id`, `state`.
  This is the only UI that can link/unlink sheet membership today.
- **Allocations** (lines 497–508): `allocation_ids` with
  `create="false" delete="false"`, embedded `<list>` of `name`, `state`,
  `total_vouchers`, `total_applied`, `residual` — **no `partner_id`**.

There is **no** `oe_button_box` / `oe_stat_button` / `statinfo` anywhere in this addon.
Document Review is a header object button with
`invisible="not id or not document_review_enabled"`.

### `sheet_id` on voucher views

The model field exists (`collection.voucher.sheet_id`, Many2one, `ondelete="set null"`).
It does **not** appear in:

- `view_collection_voucher_list` (name, partner, seller, company optional, create_date,
  state, reviewers optional, document_type, document_id optional, amount)
- `view_collection_voucher_form` (left group: partner, company invisible, seller,
  create_date — no sheet)
- `view_collection_voucher_search` (no `sheet_id` field or group-by)
- `view_collection_voucher_kanban` (name, partner, create_date, state)

The claim in the source plan is confirmed. Unlink from a sheet is only possible via the
sheet Vouchers page (or ORM/MCP). Allocation views already show `sheet_id`; that is a
different model.

The voucher list has **no** `editable` / `multi_edit`. Adding `sheet_id optional="hide"`
is display/filter only unless a later change turns on list multi-edit. Form remains the
practical unlink surface.

### `collection.action_collection_voucher`

```xml
<field name="path">payment-vouchers</field>
<field name="view_mode">kanban,list,form</field>
```

Reusing this via `_for_xml_id` would rewrite the browser URL when opening the stat
button. Hand-building the act_window is required. Existing `action_open_document_review`
uses `_for_xml_id` on a **client** action
(`collection.action_collection_document_review`), which is a different pattern.

### Sheet model (`models/collection_sheet.py`)

| Surface                       | Fact                                                                                                                                                                                                                                  |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `voucher_ids`                 | One2many → `collection.voucher.sheet_id`. Kept for ORM, `_compute_dates`, `_sanitize_voucher_commands`, MCP.                                                                                                                          |
| `allocation_ids`              | One2many → `collection.allocation.sheet_id`.                                                                                                                                                                                          |
| `date_from` / `date_to`       | Stored computes on `voucher_ids` / `voucher_ids.create_date`. Recalc on membership write even if `voucher_ids` leaves the form.                                                                                                       |
| `document_review_enabled`     | Non-stored Boolean compute (pattern for `voucher_count`).                                                                                                                                                                             |
| `voucher_count`               | **Does not exist.**                                                                                                                                                                                                                   |
| `action_open_vouchers`        | **Does not exist.**                                                                                                                                                                                                                   |
| `action_open_document_review` | Lines 225–233: `ensure_one`, review flag, `_ensure_saved_sheet()`, `_for_xml_id` client action.                                                                                                                                       |
| `_ensure_saved_sheet`         | Lines 235–239: raises `UserError("Document Review requires a saved collection sheet.")` when `id` is not a positive int. Only caller today is Document Review. Tests assert `UserError` on `.new()` sheets, **not** the exact string. |

Closed-sheet membership freeze stays in `write()` / voucher
`_ensure_sheet_membership_unlocked` / `_check_sheet_seller`. No need to touch those for
this UI change.

### Allocation uniqueness

`collection.allocation.partner_id` is already a required Many2one `res.partner` (label
Customer). Constraint `_sheet_partner_uniq`: `UNIQUE(sheet_id, partner_id)` — "Only one
allocation is allowed per customer per sheet." Adding `partner_id` to the embedded list
is view-only.

### Tests (`strict_tdd: true`)

Will break without updates:

- `test_collection_sheets_form_statusbar_close_reopen` — requires `voucher_ids` in the
  form field set; asserts `widget="many2many"` and `readonly` contains
  `state == 'closed'`.
- `test_sheet_form_notebook_vouchers_and_allocations` — requires both notebook pages,
  Vouchers `voucher_ids` many2many, and `voucher_ids` still in `_field_names`.

Will keep passing if partner_id moves from voucher list to allocation list (count stays
1):

- `test_customer_field_is_partner_id_without_domain` expects exactly **one**
  `partner_id` on `view_collection_sheet_form`.

No `Form()` usage on `collection.sheet` (or anywhere in this addon). Removing
`voucher_ids` from the arch does not break functional Form helpers.

`tests/test_collection_sheet.py` covers lifecycle, freeze, Document Review actions,
auto-assign. It does **not** assert notebook XML. New tests needed for `voucher_count`
and `action_open_vouchers` (domain, unsaved `UserError`).

Existing voucher list/form/search tests use `assertIn` for required fields, not an exact
field set — adding `sheet_id` does not break them.

### Spec

`openspec/specs/collection-sheets/spec.md` requirement **Sheet form notebook** (lines
379–387) currently: "Sheet form MUST expose vouchers and allocations in a notebook."
This change replaces that requirement.

`action_create_collection_sheet`, Document Review OWL, ACLs, and MCP tools are out of
scope.

## Affected Areas

- `models/collection_sheet.py` — add non-stored `voucher_count`,
  `_compute_voucher_count`, `action_open_vouchers`; optionally generalize
  `_ensure_saved_sheet` message.
- `views/collection_views.xml` — sheet form notebook + button box; voucher
  list/form/search `sheet_id`.
- `tests/test_collection_ui.py` — rewrite notebook contract; drop `voucher_ids` from
  statusbar test; add stat-button and voucher `sheet_id` arch tests.
- `tests/test_collection_sheet.py` — `voucher_count` and `action_open_vouchers`
  behavior.
- `openspec/specs/collection-sheets/spec.md` — MODIFIED requirement (delta in this
  change).
- `AGENTS.md` (collection) — UI bullet still says "Sheet form notebooks Vouchers and
  Allocations"; update when behavior ships (apply/archive), not this explore file.

Not affected: MCP tools, `action_create_collection_sheet`, Document Review client
action, security, migrations, `voucher_ids` field on the model.

## Approaches

1. **Settled plan (allocations notebook + stat button + expose `sheet_id`)** — Remove
   the Vouchers page; keep a one-page Allocations notebook with `partner_id`; add
   `voucher_count` + hand-built `action_open_vouchers`; expose `sheet_id` on voucher
   list (`optional="hide"`), form (editable, server guards), and search (field +
   group-by).

   - Pros: Matches settled UX; keeps `voucher_ids` for ORM/MCP; no migration; Document
     Review and list Action untouched; standard Odoo stat-button pattern.
   - Cons: First `oe_button_box` in this addon (no local template); mass unlink
     deferred; `_ensure_saved_sheet` error text is Document Review– specific if reused
     verbatim.
   - Effort: Low–Medium (views + TDD tests + small compute/action).

2. **Reuse `collection.action_collection_voucher` via `_for_xml_id`** — Copy the menu
   action and overlay domain/context.

   - Pros: Slightly less dict boilerplate.
   - Cons: `path="payment-vouchers"` rewrites the URL; `view_mode` starts at kanban,
     which is wrong for a sheet drill-down. **Rejected** by settled decision and
     confirmed in XML.
   - Effort: Low (but wrong).

3. **Hide Vouchers page instead of removing it** — `invisible="1"` on the Vouchers page.
   - Pros: Less XML churn; membership widget still in the arch for tests.
   - Cons: Field still loads; contradicts "show only Allocations"; keeps the noisy
     widget the change exists to remove.
   - Effort: Low. **Do not use.**

## Recommendation

Implement the **settled plan** (Approach 1). Code confirms it; nothing in the plan is
structurally wrong.

Implementation notes for propose/design (not product reopens):

- **Hand-build** `action_open_vouchers` (`list,kanban,form`, domain
  `[("sheet_id", "=", self.id)]`, context `default_sheet_id` / `default_seller_id`). Do
  not `_for_xml_id` `collection.action_collection_voucher`.
- **Reuse `_ensure_saved_sheet()`**, but **generalize the UserError** to a sheet-saved
  message (not "Document Review requires…"). Document Review tests do not assert that
  string. Pair with `invisible="not id"` on the stat button.
- **Form `sheet_id`**: editable; rely on `_ensure_sheet_membership_unlocked` and
  `_check_sheet_seller`. Do not add extra readonly tied to voucher `state` (server
  allows unlink on open sheets regardless of voucher state).
- **Kanban**: leave without `sheet_id` (settled list/form/search only).
- **TDD first** (`openspec/config.yaml` `strict_tdd: true`): invert UI contracts before
  XML/Python. Keep `SHEET_NOTEBOOK_VOUCHERS` for absence asserts. Rename
  `test_sheet_form_notebook_vouchers_and_allocations` →
  `test_sheet_form_notebook_allocations_only`.
- **No migration.** `voucher_count` is non-stored, like `document_review_enabled`.
- Mass unlink stays deferred: form `sheet_id` (one-by-one). Voucher list is not
  multi-editable today.

## Risks

- **Mass unlink lost** until a later server action or `multi_edit` on the voucher list.
  Accepted / deferred.
- **Misleading unsaved error** if `_ensure_saved_sheet` is reused without changing the
  Document Review wording. Mitigate by generalizing the string.
- **`test_customer_field_is_partner_id_without_domain`** fails if sheet form ends with 0
  or 2 `partner_id` nodes. Keep exactly one: on the allocations embedded list.
- **Strict TDD**: architecture tests fail until they are updated first.
- **Rollback** is a view+test revert; no data/DDL risk.
- Review size: XML + two test files + small model. Watch the 400-line budget at
  tasks/apply; likely one work unit.

## Ready for Proposal

**Yes.** Orchestrator should run `sdd-propose` with this exploration as input. No
clarification needed: product decisions are settled and verified against current code.
