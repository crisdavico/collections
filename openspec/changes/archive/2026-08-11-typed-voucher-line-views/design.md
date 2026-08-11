# Design: Typed voucher line tables and payment-lines menu

## Technical Approach

UI-only reshape of payment lines on the existing `collection.voucher` /
`collection.voucher.line` models. Replace the mono `payment_ids` editable list with
three domain-filtered embeds (stacked in the form sheet/notebook page), each with
type-specific list columns and `default_document_type` context. Add a read-only
act_window + menu for browsing lines. MCP and field schema stay unchanged.

## Architecture Decisions

| Decision              | Options                                                                             | Choice                                            | Rationale                                                                  |
| --------------------- | ----------------------------------------------------------------------------------- | ------------------------------------------------- | -------------------------------------------------------------------------- |
| Typed embeds          | A) Reuse `payment_ids` 3× with domain/context B) Extra One2many fields with domains | **A first**; B if A fails create UX               | Fewer model fields; same inverse; Odoo supports domain+context on One2many |
| Where stacked         | Notebook pages vs vertical stack                                                    | **Vertical stack** under one “Payment Lines” area | Matches product ask: tables one below the other                            |
| `unsupported` on form | Hide vs fourth table                                                                | **Hide** from form tables                         | Product excludes it; Payment Lines menu covers discovery                   |
| Lines menu mutability | CRUD vs read-only                                                                   | **Read-only** (`create`/`edit` false)             | Browse/filter only; edits stay on voucher form                             |
| `document_id`         | Optional show                                                                       | **Show**, still not required in UI                | Aligns with MCP visibility; keep nullable UI create                        |

## Data Flow

```
Voucher form
  ├─ bank_transfer list ── domain type=bank_transfer ──┐
  ├─ check list ────────── domain type=check ──────────┼─→ collection.voucher.line
  └─ cash_deposit list ─── domain type=cash_deposit ───┘
                                                         ↑
Payment Lines menu (read-only list/search) ──────────────┘
```

New row in a typed list → context `default_document_type` → saved with that type → only
that list’s domain matches.

## File Changes

| File                                     | Action            | Description                                                                       |
| ---------------------------------------- | ----------------- | --------------------------------------------------------------------------------- |
| `views/collection_views.xml`             | Modify            | Three stacked typed lists; remove mono list; line list/search/action/menu         |
| `models/collection_voucher.py`           | Modify (optional) | Only if typed One2many fields prove clearer than triple `payment_ids`             |
| `tests/test_collection_ui.py`            | Modify            | Assert menus, typed arches, defaults/fields, no mono list, read-only lines action |
| `tests/test_collection_*.py` (MCP/model) | Unchanged         | Unless a helper field is added that needs touch                                   |

## Interfaces / Contracts

Form typed lists (conceptual):

```xml
<field
  name="payment_ids"
  domain="[('document_type', '=', 'bank_transfer')]"
  context="{'default_document_type': 'bank_transfer'}"
>
  <list editable="bottom">
    <field name="document_id" />
    <field name="amount" />
    <field name="from_account" />
    <field name="to_account" />
    <field name="voucher_number" />
    <field name="voucher_date" />
    <field name="currency_id" column_invisible="1" />
  </list>
</field>
<!-- check / cash_deposit analogs; no document_type column -->
```

Payment Lines action:

- `res_model`: `collection.voucher.line`
- `view_mode`: `list,form` (form optional/read-only) or `list` only
- `create` / `edit`: false
- Search filters/group_by on `document_type`, `document_id`, `amount`, type-specific
  fields, `voucher_id`

## Testing Strategy

| Layer                  | What to Test                                                                                                                     | Approach                                     |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| Unit (TransactionCase) | Menu xmlids; three typed lists; fields; no mono list; no `document_type` column; read-only lines action flags; create_date rules | Extend `tests/test_collection_ui.py`         |
| Unit                   | Creating lines via typed context defaults `document_type`                                                                        | Form create or ORM with context mimicking UI |
| Integration            | Module upgrade loads views                                                                                                       | `invoke install -m collection`               |
| E2E browser            | N/A                                                                                                                              | Not available                                |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification,
or process-integration boundary.

## Migration / Rollout

No data migration. Module upgrade reloads views/menus. Existing lines (including
`unsupported`) keep data; form visibility changes only.

## Open Questions

- None — product decisions locked in proposal Q&A.
