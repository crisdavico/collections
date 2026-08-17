# Tasks: Collection Sheets

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 550–750 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR1→PR2→PR3→PR4 per units below |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

Focused test for every unit: `invoke test -m collection`. Runtime harness: `invoke install -m collection` (schema/views; e2e N/A).

| Unit | Goal | Likely PR | Rollback boundary |
|------|------|-----------|-------------------|
| 1 | Voucher seller + MCP | PR 1 | voucher `seller_id`, MCP tool, voucher views + tests |
| 2 | Sheet + sequence | PR 2 | `models/collection_sheet.py`, sequence XML, ACL row, sheet tests |
| 3 | Action, dates, constraints | PR 3 | voucher Action/`sheet_id`/constraints; sheet dates/unlink |
| 4 | UI, ACL, upgrade | PR 4 | sheet views, ACL/UI tests, `__manifest__.py` |

Out: nebula-agent, threat-matrix, new migrations.

## Phase 1: Voucher seller + MCP (PR 1)

- [x] 1.1 RED `tests/test_collection_voucher.py`: ORM create without seller stays null; no backfill.
- [x] 1.2 RED `tests/test_collection_ui.py`: form `required="1"` on `seller_id`; list/form/search show it.
- [x] 1.3 RED `tests/test_collection_mcp_tool.py`: require `seller_id`; all-new stamps; exact replay no mutate (incl. null); missing/portal/unknown reject, no writes.
- [x] 1.4 GREEN `models/collection_voucher.py`: nullable `seller_id` → `res.users`, domain `[('share','=',False)]`.
- [x] 1.5 GREEN `tools/collection_voucher.py`: validate internal `seller_id`; stamp all-new only; replay read-only; no `sudo()`. Voucher seller in `views/collection_views.xml`. REFACTOR. `invoke test -m collection`.

## Phase 2: Sheet model + sequence (PR 2)

- [ ] 2.1 RED `tests/test_collection_sheet.py`: unique `CS/<year>/<number>`; no `state`; missing seller and post-create seller write rejected; not from `create_uid`.
- [ ] 2.2 GREEN create `models/collection_sheet.py`: required frozen `seller_id`; sequence `collection.sheet`.
- [ ] 2.3 GREEN `models/__init__.py`; `data/ir_sequence_data.xml` `CS/%(year)s/` pad 4; `security/ir.model.access.csv` one `base.group_user` CRUD row; `tests/__init__.py`. REFACTOR. `invoke test -m collection`.

## Phase 3: Action, dates, constraints (PR 3)

- [ ] 3.1 RED Action: unassigned same-seller `pending`+`approved` → one sheet, both members; mixed/assigned/empty → `UserError`, no sheet.
- [ ] 3.2 RED Action seller-less selection: null `seller_id` → `UserError`, no sheet (atomic). Spec ineligible GIVEN omitted this; still require non-null seller.
- [ ] 3.3 RED mixed/null assign rejected; reassign → sheet B only; empty dates False; UTC min/max member `create_date`; no `received_date`.
- [ ] 3.4 RED unlink sheet: vouchers persist, `sheet_id` null. RED `tests/test_collection_voucher.py`: assigned without seller fails.
- [ ] 3.5 GREEN `models/collection_voucher.py`: `sheet_id` set-null; constrains+CHECK; list `ir.actions.server` (no wizard).
- [ ] 3.6 GREEN `models/collection_sheet.py`: O2M; UTC dates; `(2,id)`→`(3,id)`; freeze seller. REFACTOR. `invoke test -m collection`.

## Phase 4: UI, ACL, upgrade (PR 4)

- [ ] 4.1 RED `tests/test_collection_ui.py`: sheet menu/list/form/search; Action xmlid; no statusbar; `<list>`. RED `tests/test_collection_acl.py`: sheet CRUD internal vs portal.
- [ ] 4.2 GREEN `views/collection_views.xml`: sheet views+menu; list Action; `widget="many2many"`.
- [ ] 4.3 GREEN `__manifest__.py` `19.0.1.9.0` → `19.0.1.10.0`. Keep `migrations/19.0.1.7.0`; no `migrations/19.0.1.10.0/`.
- [ ] 4.4 Verify: `invoke install -m collection`; `invoke test -m collection`; Seedian root `pre-commit run --files odoo/custom/src/private/collection/**`.
