# Design: Two-step Seller Close and Seller Deposit

## Technical Approach

Split Seller Close from cash declaration. Freeze `open` → `submitted` with no
amounts. Seller reads the Planilla, banks cash as catalog `seller_deposit` on a
seeded sentinel partner, then `action_declare_cash` (re-runnable on
`SELLER_DECLARATION_STATES`). Confirm gates on `cash_declared_at` when
`cash_collected > 0`.

`seller_deposit` is remittance: out of `collected_total`/`mismatch`, into
`tendered` as `seller_deposits`. `cash_banked` sums `seller_deposit` only.
Replacement is value-preserving (quotation then invoice) on write to
`validated_collections`, audited by immutable `collection.cash.replacement`.

U1 lifts sheet-boundary + sheet-wide cap + receipt `depends=` into core. U6
locks the board **before** U5b so replaced cash cannot re-enter the pool.

**`apply.roots` omit the sibling.** `collection/openspec/config.yaml` roots only
`…/private/collection`. U1 deletes and U6 edits live under
`collection_receipt_proposal`. Apply MUST grant that sibling root. Grant is
consent, not a reason to drop U1/U6.

Stack: **U1 → U2 → U3 → U4 → U5a → U6 → U5b → U5c**. Strict TDD.
`auto-chain` / `stacked-to-main`. No `migrations/19.0.1.42.0/`.

## Architecture Decisions

| Option | Tradeoff | Decision |
| --- | --- | --- |
| Sentinel partner vs optional `partner_id` | NOT NULL + spec inversion | **Sentinel XMLID**; `partner_id` stays required |
| `seller_deposit` vs reuse `cash_deposit` | Double-count / `cash_banked` slip | **Eighth catalog code**; `cash_banked` = `seller_deposit` only |
| Remittance in collected vs tendered | Inflates Total Cobrado + mismatch | **Exclude from collected/mismatch; add to tendered** |
| Recon algebra rewrite vs untouched | XLSX live vs cached SUM drift | **Untouched** (`net_due = collected − withheld`) |
| Ledger vs voucher scalars | Multi-deposit + reverse triple | **`collection.cash.replacement`**; `write()` raises |
| Trigger on Approve vs `validated_collections` write | Review flag defaults False | **Voucher `write` to `validated_collections`** |
| Reverse on Cancel | `cancelled ∈ FROZEN_SHEET_STATES`; money is banked | **No reverse**; Reinstate is also a no-op |
| PDF via `_open_sheets_for_seller` vs call site | Widening helper breaks one-open | **Call site only** + `_submitted_sheets_for_seller` |
| Rename `cash_on_hand` | Column rename + MCP + tests | **Keep column**; `string=` "Cash to Administration" |
| Named frozenset vs inline `"open"` | Leftover scanner | **`SELLER_DECLARATION_STATES = frozenset({"submitted"})`** |
| Satellite N+1 cap vs delete core `:72-73` | N+1 in core | **Delete allocation filter; keep batched `search`** |
| Exact-cent unlink vs round-to-zero unlink | Sub-cent leak → `"cruce"` | **Skip 0 slices; shrink only if equal or remainder ≥ 1 cent** |
| Manifest `.43.0` vs `.42.0/` migrate | Pin forbids `.42.0/` | **`19.0.1.43.0` + union-all types** |
| MCP deposit `document_id` from model | UNIQUE + agent burden | **Server mints `sd-<uuid4 hex>`** |
| Sentinel stored company field vs XMLID | Extra column | **`collection.partner_seller_deposit` + `_seller_deposit_partner()`** |

Do not lift `_check_voucher_allocation_partner` / `_proposal_allocation_owner_ok`
/ `_check_voucher_partners`. Do not send replacement to ERP (`create_receipt`
follow-up). Do not implement Nebula.

## Data Flow

### Close → PDF → deposit (replacement) → declare → Planilla

```mermaid
sequenceDiagram
    participant S as Seller / MCP
    participant Close as close_collection_sheet
    participant Sheet as collection.sheet
    participant PDF as get_collection_sheet_pdf
    participant Dep as create_seller_deposit
    participant V as collection.voucher
    participant Eng as replacement engine
    participant Led as collection.cash.replacement
    participant Decl as declare_collection_cash
    participant Rpt as _collection_report_data

    S->>Close: {seller_id}
    Close->>Sheet: lock + _open_sheets_for_seller
    Close->>Sheet: action_seller_close()  %% no amounts
    Sheet-->>Close: state=submitted
    Close-->>S: {sheet, cash:{collected}}

    S->>PDF: {seller_id}
    PDF->>Sheet: open? else _submitted_sheets_for_seller
    PDF-->>S: Planilla PDF (cash total, no declaration)

    S->>Dep: {seller_id, amount, voucher_number, voucher_date, attachment?}
    Dep->>Sheet: _submitted_sheets_for_seller
    Dep->>V: create sentinel + seller_deposit + sheet_id + validated_seller
    Dep->>V: audited write validated_collections
    V->>Eng: write-hook (seller_deposit only)
    Eng->>Eng: quotation then invoice; exact-cent shrink/grow
    Eng->>Led: gated create direction=replace
    Note over Eng: total_values unchanged → amount_applied untouched
    Dep-->>S: {sheet, voucher}

    S->>Decl: {seller_id, cash_on_hand, commission_withheld}
    Decl->>Sheet: action_declare_cash (re-runnable)
    Sheet-->>Decl: cash_declared_at/by
    Decl-->>S: {sheet}

    S->>PDF: {seller_id}
    PDF->>Rpt: collected excludes seller_deposit; tendered includes it
    PDF-->>S: Cuadrada (when algebra balances)
```

Advisory lock on close stays `(company, seller)` + `invalidate_recordset`.
Deposit MCP **must** pass `sheet_id` (`_apply_open_sheet_auto_assign` only
resolves `SELLER_SHEET_STATES`). `submitted ∈ ADMIN_EDITABLE_SHEET_STATES` so
membership writes succeed.

### Replacement (U5b)

```
seller_deposit → validated_collections
  → buckets: quotation, then invoice
  → within kind: _proposal_fifo_key (due_date or date.max, invoice_number or "")
  → within bucket: cash values, oldest create_date first
  → for each slice: round; skip 0; shrink iff slice==amount or remainder≥1 cent
  → grow deposit value on the SAME receipt
  → ledger row direction=replace
```

No allocations → silent no-op; `cash_banked` still comes from the voucher.
Cancel/Reinstate MUST NOT re-replace (ledger already exists; hook is
transition-only).

## File Changes

Paths relative to `odoo/custom/src/private/`. **U** = work unit.

### collection (core)

| File | Action | U | Description |
| --- | --- | --- | --- |
| `collection/models/collection_receipt_value.py` | Modify | U1, U5a | Sheet boundary `_check_same_allocation`; delete `:72-73` allocation filter (keep batched search); currency-agreement check; `_shrink_or_unlink` / `_grow_voucher_amount` primitives |
| `collection/models/collection_receipt.py` | Modify | U1 | Field-level `depends=` on `total_values` / `total_applied` / `amount_on_account` (lift from satellite; short-circuit `line_ids` SQL) |
| `collection/models/collection_voucher.py` | Modify | U1, U5a, U5b | `receipt_value_ids` inverse o2m; stored/computed `replaced_amount` = Σreplace − Σreverse; write-hook on `validated_collections` for `seller_deposit` |
| `collection/models/collection_allocation.py` | Modify | U5a | Neutral `_receipt_get_or_create(document_kind)` (move from satellite) |
| `collection/models/collection_common.py` | Modify | U2, U4 | Eighth `seller_deposit`; `SELLER_DECLARATION_STATES = frozenset({"submitted"})` |
| `collection/data/collection_document_type_data.xml` | Modify | U2 | XMLID `document_type_seller_deposit` |
| `collection/data/collection_seller_deposit_partner_data.xml` | Create | U2 | `noupdate` sentinel `collection.partner_seller_deposit` (`company_id` False) |
| `collection/models/res_company.py` | Modify | U2 | `@api.private _seller_deposit_partner()` via `env.ref`; `COLLECTION_TYPE_CODES` follows `DOCUMENT_TYPE_CODES` |
| `collection/migrations/19.0.1.43.0/post-migrate.py` | Create | U2 | Clone `19.0.1.40.0`: `_collection_enable_all_document_types()`. **Not** `19.0.1.42.0/` |
| `collection/__manifest__.py` | Modify | U2 | `19.0.1.43.0`; data entry for sentinel XML |
| `collection/models/collection_sheet_report.py` | Modify | U3, U4, U5b | Skip `seller_deposit` voucher blocks; tendered keys `seller_deposits` + `echecks` + `retentions` (keep `cash`/`deposits`/`checks`/`transfers`); invert declaration window to `SELLER_DECLARATION_STATES`; keep `cash_on_hand` column, change `string=`; `cash_declared_at` / `cash_declared_by`; computed `cash_collected` / `cash_banked` |
| `collection/report/collection_sheet_xlsx.py` | Modify | U3 | Recon header + cross-links for new tendered keys; keep existing formula ladder keys |
| `collection/report/collection_sheet_templates.xml` | Modify | U3 | QWeb recon table shows new tendered lines |
| `collection/models/collection_sheet.py` | Modify | U4 | `action_seller_close` drops amount vals (keep kwargs `=None`); `action_declare_cash`; Confirm gate; `_submitted_sheets_for_seller` |
| `collection/tools/collection_sheet_close.py` | Modify | U4 | Amount-free schema; return `cash.collected`; still open-only |
| `collection/tools/collection_cash_declare.py` | Create | U4 | MCP `declare_collection_cash` |
| `collection/tools/sheet_report.py` | Modify | U4 | After 0 open, serve 1 submitted; `{sheet: null}` if neither; multi-submitted `UserError`. Do **not** change `_open_sheets_for_seller` |
| `collection/views/collection_views.xml` | Modify | U4, U5c | Recon `readonly` on `submitted`; `voucher_number`/`voucher_date` `invisible=` include `seller_deposit` on Current + OCR + Seller Confirmed; search filter; **no** second `partner_id` |
| `collection/models/collection_cash_replacement.py` | Create | U5a | Immutable ledger (revision pattern) |
| `collection/models/__init__.py` | Modify | U5a | Import ledger |
| `collection/security/ir.model.access.csv` | Modify | U5a | Ledger `1,0,1,0` |
| `collection/security/collection_security.xml` | Modify | U5a | Global company `ir.rule` |
| `collection/tools/collection_seller_deposit.py` | Create | U5c | MCP `create_seller_deposit` |
| `collection/tools/__init__.py` | Modify | U4, U5c | Import declare + deposit mixins |
| `collection/static/src/document_review/document_review_helpers.esm.js` | Modify | U2 | `DOCUMENT_TYPE_LABELS.seller_deposit` |
| `collection/AGENTS.md` | Modify | U2, U4 | Eight catalog rows; `19.0.1.43.0`; fix stale “submitted dormant”; MCP contracts |
| `collection/readme/DESCRIPTION.md` | Modify | U2 | Eighth type + two-step close |
| `collection/tests/test_collection_receipt.py` | Modify | U1 | Split `:170-199` into named same-sheet vs cap tests |
| `collection/tests/test_collection_company_migration.py` | Modify | U2, U4 | Eight codes; leftover pin keeps no `19.0.1.42.0/`; add `19.0.1.43.0`; scanner still forbids new `"open"` gates |
| `collection/tests/test_collection_company_settings.py` | Modify | U2 | `CATALOG_XMLIDS` len 8 |
| `collection/tests/test_collection_voucher.py` | Modify | U2 | Selection includes `seller_deposit` |
| `collection/tests/test_collection_sheet_report_data.py` | Modify | U3, U4 | Remittance totals; invert declaration freeze; `cash_banked` |
| `collection/tests/test_collection_sheet_xlsx.py` | Modify | U3, U4 | New tendered columns; submitted declarations |
| `collection/tests/test_collection_sheet.py` | Modify | U4 | Amount-free close; declare; Confirm gate |
| `collection/tests/test_collection_mcp_sheet_close.py` | Modify | U4 | Amount-free + `cash.collected` |
| `collection/tests/test_collection_mcp_sheet_pdf.py` | Modify | U4 | Submitted call-site serve |
| `collection/tests/test_collection_ui.py` | Modify | U4, U5c | Readonly `submitted`; `voucher_number` for deposit; partner_id once |
| `collection/tests/test_collection_acl.py` | Modify | U5a | Ledger `1,0,1,0` + company rule (house `:137`) |
| `collection/tests/test_collection_allocation_acl.py` | Modify | U5a | House `:168` |
| `collection/tests/test_collection_cash_replacement.py` | Create | U5a, U5b | Immutability, slicing, trigger, no Cancel reverse, `cash_banked` from voucher |
| `collection/tests/test_collection_mcp_seller_deposit.py` | Create | U5c | Schema, sentinel, `sheet_id`, audited validate |
| `collection/tests/test_collection_mcp_cash_declare.py` | Create | U4 | Declare MCP; 0-submitted `UserError` |

### collection_receipt_proposal (sibling — grant required)

| File | Action | U | Description |
| --- | --- | --- | --- |
| `collection_receipt_proposal/models/collection_receipt.py` | Delete | U1 | `depends=` now in core |
| `collection_receipt_proposal/models/__init__.py` | Modify | U1 | Drop `collection_receipt` import (`:5`) |
| `collection_receipt_proposal/models/collection_receipt_value.py` | Modify | U1 | Delete `_check_same_allocation` / `_check_voucher_split_cap` (`:12-57`); keep `_proposal_card_payload` |
| `collection_receipt_proposal/models/collection_voucher.py` | Modify | U6 | `proposal_free_amount = amount − assigned − replaced_amount`; depends include `replaced_amount` |
| `collection_receipt_proposal/models/collection_sheet.py` | Modify | U5a, U6 | `_proposal_shrink_value` / `_proposal_grow_value` become wrappers of core primitives; guard `_proposal_transfer_plan` pool path and `_proposal_sync_voucher_owner` against `seller_deposit`; replaced cash keeps `allocation_id` |
| `collection_receipt_proposal/models/collection_allocation.py` | Modify | U5a | `_proposal_receipt_get_or_create` delegates to core |
| `collection_receipt_proposal/tests/test_receipt_proposal_split.py` | Modify | U1, U6 | Still green on core constraints; remittance not draggable |
| `collection_receipt_proposal/tests/test_receipt_proposal_board.py` | Modify | U6 | Replaced cash absent from pool; excess deposit not a pool card |
| `collection_receipt_proposal/tests/test_receipt_proposal_actions.py` | Modify | U6 | Transfer/sync-owner remittance guards |
| `collection_receipt_proposal/AGENTS.md` | Modify | U1, U6 | Same-sheet/cap now core; board lock |

## Interfaces / Contracts

### Named sets

```python
SELLER_SHEET_STATES = frozenset({"open"})          # unchanged; one-open / close / allocation write
ADMIN_EDITABLE_SHEET_STATES = frozenset({"open", "submitted"})
SELLER_DECLARATION_STATES = frozenset({"submitted"})  # NEW; leftover-scanner safe
DRAFT_SHEET_STATES = frozenset({"open", "submitted", "proposal", "cancelled"})
FROZEN_SHEET_STATES = frozenset({"closed", "cancelled"})
```

### Ledger `collection.cash.replacement`

Follow `collection.allocation.revision` (`create` gated, `write()` raises,
`@api.ondelete` exempts `collection_allocation_parent_unlink`). Context key
`collection_cash_replacement`. Unlink ACL is `0`: receipt `ondelete="cascade"`
is PostgreSQL-level.

| Field | Notes |
| --- | --- |
| `receipt_id` | required, index, `ondelete="cascade"` |
| `cash_voucher_id` | required, index, `ondelete="restrict"` |
| `deposit_voucher_id` | required, index, `ondelete="restrict"` |
| `amount` | Monetary, required, `CHECK(amount > 0)` |
| `direction` | Selection `replace` / `reverse`, required |
| `sheet_id` | related stored from `receipt_id` |
| `currency_id` | related stored from `receipt_id` |
| `company_id` | related stored, required, precompute, index |
| `created_by` | Many2one `res.users`, required |
| `created_at` | Datetime, required |

`replaced_amount(cash) = Σreplace − Σreverse`. No `reversed_at`. Reverse API
exists for completeness; Cancel/Reinstate MUST NOT call it.

ACL: `base.group_user` `1,0,1,0`. Company `ir.rule`
`[('company_id', 'in', company_ids)]`. Never `sudo()`.

### MCP — `close_collection_sheet` (breaking)

```python
_CLOSE_COLLECTION_SHEET_SCHEMA = {
    "type": "object",
    "properties": {
        "seller_id": {"type": "integer", "minimum": 1},
    },
    "required": ["seller_id"],
}
# success:
{"sheet": {id, name, state, seller_id, date_from, date_to, voucher_count},
 "cash": {"collected": <number>}}
# 0 open → UserError (not {sheet: null}); >1 open → existing UserError
```

`cash.collected` = SUM of `document_type == "cash"` on that sheet (company
currency). Description drops the amount clause. Disabled sellers MAY still
close.

### MCP — `declare_collection_cash` (additive write)

```python
{
    "type": "object",
    "properties": {
        "seller_id": {"type": "integer", "minimum": 1},
        "cash_on_hand": dict(_COLLECTION_AMOUNT_SCHEMA),
        "commission_withheld": dict(_COLLECTION_AMOUNT_SCHEMA),
    },
    "required": ["seller_id", "cash_on_hand", "commission_withheld"],
}
# resolve _submitted_sheets_for_seller; 0 or >1 → UserError
# → check_access("write") → action_declare_cash(...)
# success: {sheet: _collection_sheet_identity}
```

### MCP — `create_seller_deposit` (additive write)

```python
{
    "type": "object",
    "properties": {
        "seller_id": {"type": "integer", "minimum": 1},
        "amount": dict(_COLLECTION_AMOUNT_SCHEMA),
        "voucher_number": {"type": "string"},
        "voucher_date": {"type": "string", "description": "ISO date"},
        "attachment": _ATTACHMENT_NEST_SCHEMA,  # optional
    },
    "required": ["seller_id", "amount", "voucher_number", "voucher_date"],
}
```

Flow: internal user → `_collection_require_internal_seller` →
`_assert_new_work(seller, "seller_deposit")` → `_submitted_sheets_for_seller`
→ `check_access("write")` on sheet → `create` with sentinel,
`document_type=seller_deposit`, minted `document_id`, explicit `sheet_id`,
`state=validated_seller`, `allocation_id` unset → optional chatter proof →
`with_context(collection_audited_state=True).write({state: validated_collections})`
so the U5b hook runs in-process. UI/ORM form deposits stay `validated_seller`
until Document Review.

`create_collection_allocation` stays `open` + customer-required (four live
gates unchanged). Do **not** add `seller_deposit` to allocation
`_DOCUMENT_TYPES`.

### MCP — `get_collection_sheet_pdf` (additive serve)

Seller-only schema unchanged. Call site: 1 open → current path; 0 open and 1
submitted → render that sheet; 0 and 0 → `{sheet: null}`; `>1` submitted →
same multi-sheet `UserError`. Identity helper reused.

### Confirm / declare

```python
def action_seller_close(self, cash_on_hand=None, commission_withheld=None):
    # ignore amounts; write {"state": "submitted"} only
    # _dispatch_submitted_state_write / common_connector stay argument-free

def action_declare_cash(self, cash_on_hand, commission_withheld):
    # gate SELLER_DECLARATION_STATES; stamp cash_declared_at/by; re-runnable

def action_confirm(self):
    # existing submitted + validated_collections members
    # PLUS: cash_collected > 0 and not cash_declared_at → UserError
```

### Exact-cent primitives (U5a)

`currency.round` every slice. Skip `compare_amounts(slice, 0) == 0`. Shrink
unlinks only when `compare_amounts(slice, value.amount) == 0`; else remaining
must be `>= 0.01` or skip. Grow adds the **rounded** slice. Cash / deposit /
receipt currencies MUST agree.

## Testing Strategy

| Layer | What | How |
| --- | --- | --- |
| Unit | U1 constraints + depends; U2 catalog/migrate/scanner; U3 remittance totals + echeck/retention; U4 amount-free close/declare/PDF/Confirm; U5a ledger ACL/immutability/slicing; U6 pool/sync-owner; U5b trigger/`cash_banked`/no Cancel reverse; U5c deposit MCP | `TransactionCase` RED then GREEN per unit; `invoke test -m collection --mode=update` |
| Integration | After U1 **and** after U6: sibling suite; Confirm + board sees locked cash | `invoke test -m collection_receipt_proposal --mode=update` |
| E2E | Devel: close → PDF → deposit → declare → Planilla Cuadrada → Confirm → board | Manual after U5c (plan Verification) |

Scanner: no new `.state == "open"` / domain `"open"` in `models/` or `tools/`
outside `collection_common.py`. Invoice `open` files stay exempt.

## Threat Matrix

N/A — Odoo ORM, MCP mixin tools, QWeb/XLSX reports, and a satellite board.
No routing, shell, subprocess, VCS/PR automation, executable-file
classification, or process-integration boundary.

## Migration / Rollout

Additive. Manifest `19.0.1.43.0`. `migrations/19.0.1.43.0/post-migrate.py`
unions catalog types onto every company (extras kept). No `partner_id`
nullability change. No `cash_on_hand` rename. No `migrations/19.0.1.42.0/`.

Stacked PRs (do not merge U4+U5 or U5b+U5c):

| PR | Unit | Depends |
| --- | --- | --- |
| 1 | U1 lift (sibling grant) | — |
| 2 | U2 catalog + `.43.0` | — |
| 3 | U3 remittance totals | U2 |
| 4 | U4 two-step close | U2 |
| 5 | U5a ledger + primitives | U1, U2 |
| 6 | U6 board lock | U5a |
| 7 | U5b engine + `cash_banked` | U5a, **U6** |
| 8 | U5c deposit MCP + form | U5b |

Rollback: revert newest-first. Ledger table drops with U5a revert. Nebula
close will fail until a follow-up drops amounts and learns declare/deposit.

## Open Questions

None that reopen settled product choices.

Pins recorded above (not questions): sentinel XMLID; server-minted
`document_id`; MCP deposit audited-validates in-process; echeck/retention as
new tendered keys `echecks`/`retentions` (existing keys kept).
