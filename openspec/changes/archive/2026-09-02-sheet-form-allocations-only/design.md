# Design: Sheet Form Allocations Only

## Technical Approach

Sheet form becomes allocations-first: drop the Vouchers notebook page, keep a one-page
Allocations notebook with Customer, and add a counted smart button that opens a
**hand-built** voucher window filtered by this sheet. Membership unlink moves to voucher
`sheet_id` views. Keep model `voucher_ids` so `_compute_dates`, freeze sanitizer, and
MCP stay unchanged. No DDL, ACL, or sequence work. Change specs were not on disk at
design time; this follows the proposal plus live code.

## Architecture Decisions

| Topic                    | Options                                                                                 | Tradeoff                                                                                                                                                                                                               | Decision                                                                                                                                                                                                |
| ------------------------ | --------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Stat action              | `_for_xml_id` `collection.action_collection_voucher` vs dict                            | Menu XMLID has `path="payment-vouchers"` and kanban-first `view_mode`                                                                                                                                                  | Hand-built dict: `view_mode` `list,kanban,form`; domain `sheet_id`; context `default_sheet_id` + `default_seller_id`. Do **not** `_for_xml_id` that XMLID                                               |
| Form `sheet_id`          | `readonly="sheet_id and state != 'pending'"` vs editable                                | Readonly would block clearing `sheet_id` on **approved/rejected** members of **open** sheets. Server `_ensure_sheet_membership_unlocked` / `_check_sheet_seller` already allow that unlink; closed sheets still freeze | Fully editable; rely on server guards (matches proposal)                                                                                                                                                |
| Unsaved RPC              | New helper vs `_ensure_saved_sheet`                                                     | Current string names Document Review; tests assert `UserError` type, not the string                                                                                                                                    | Reuse helper; generalize message                                                                                                                                                                        |
| Sheet `partner_id` count | Update `test_customer_field_is_partner_id_without_domain` vs related alias vs move node | Test uses `_field_nodes` → `//field[@name="partner_id"]` on the **whole** sheet form arch; expected count is **1**. Today that node is the Vouchers embedded list                                                      | Remove Vouchers page and add one `partner_id` on the allocations `<list>` after `name` before `state`. Count stays 1. **Do not** change that test. **Do not** add a sheet-level or related `partner_id` |

## Data Flow

```
saved sheet form ──stat button──► action_open_vouchers
                                      ├─ _ensure_saved_sheet
                                      └─ act_window vouchers [sheet_id = self.id]
                                           └─ form write sheet_id
                                                └─ membership guards → dates recompute
```

Unsaved: button `invisible="not id"`; if invoked, generalized `UserError`.

## File Changes

| File                             | Action | Description                                                                                                        |
| -------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------ |
| `models/collection_sheet.py`     | Modify | Non-stored `voucher_count` `@api.depends("voucher_ids")`; `action_open_vouchers`; generalize `_ensure_saved_sheet` |
| `views/collection_views.xml`     | Modify | Button box; drop Vouchers page; allocations `partner_id`; voucher list/form/search `sheet_id`                      |
| `tests/test_collection_ui.py`    | Modify | Invert notebook/statusbar **first**; add stat-button + `sheet_id` arch; keep `SHEET_NOTEBOOK_VOUCHERS` for absence |
| `tests/test_collection_sheet.py` | Modify | `voucher_count`; `action_open_vouchers` domain/context/`view_mode`; unsaved `.new()`                               |
| `AGENTS.md`                      | Modify | Apply/archive: UI bullet. Not this design write                                                                    |

**Model:** add compute only. **View:** XML above. **Sequence / security:** none.

## Interfaces / Contracts

Non-stored Integer, same pattern as `document_review_enabled`:
`voucher_count = fields.Integer(compute="_compute_voucher_count")` with
`@api.depends("voucher_ids")` → `len(sheet.voucher_ids)`.

```python
def action_open_vouchers(self):
    self.ensure_one()
    self._ensure_saved_sheet()
    return {
        "type": "ir.actions.act_window",
        "name": _("Vouchers"),
        "res_model": "collection.voucher",
        "view_mode": "list,kanban,form",
        "domain": [("sheet_id", "=", self.id)],
        "context": {
            "default_sheet_id": self.id,
            "default_seller_id": self.seller_id.id,
        },
    }
```

First child **inside** `<sheet>` (Odoo smart-button slot, after the opening tag — not
after `</sheet>`):

```xml
<div class="oe_button_box" name="button_box">
    <button
    name="action_open_vouchers"
    type="object"
    class="oe_stat_button"
    icon="fa-list"
    invisible="not id"
  >
        <field name="voucher_count" widget="statinfo" string="Vouchers" />
    </button>
</div>
```

`_ensure_saved_sheet` UserError: **"This action requires a saved collection sheet."**

Voucher XML: list `sheet_id optional="hide"`; form `sheet_id` in the left group after
`seller_id`, no extra readonly; search `<field name="sheet_id"/>` plus group-by
`sheet_id`. Kanban unchanged.

## Testing Strategy

Strict TDD (`openspec/config.yaml`): invert UI tests **before** XML/Python.

| Layer        | What                                                                                                                                                                                                                                                                                                                                 | Approach                                                                        |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------- |
| Unit (arch)  | Invert `test_sheet_form_notebook_*` → allocations only; no Vouchers page / no `voucher_ids` in arch; keep `SHEET_NOTEBOOK_VOUCHERS` for absence; drop `voucher_ids` from statusbar required names and many2many asserts; stat button `statinfo` + `invisible="not id"`; voucher list `optional="hide"`; form + search field/group-by | `TransactionCase` + lxml on `view.arch` in `tests/test_collection_ui.py`        |
| Unit (model) | Empty count 0; N members; action `view_mode`/`domain`/`context`; no `path`; `.new()` UserError; Document Review still works                                                                                                                                                                                                          | Mirror `test_action_open_document_review_*` in `tests/test_collection_sheet.py` |
| Integration  | Freeze, dates, Document Review header, `_check_sheet_seller`                                                                                                                                                                                                                                                                         | Existing tests; no new HttpCase (e2e unavailable)                               |

## Threat Matrix

N/A — Odoo views + computed Integer + act_window dict. No routing, shell, subprocess,
VCS/PR automation, executable-file classification, or process-integration boundary.

## Migration / Rollout

No migration required. `voucher_count` is non-stored. Sequence and security unchanged.
Upgrade with `-u collection`. Rollback: revert the same implementation files.

## Open Questions

- [ ] None
