# Design: Sheet-Scoped Document Review

Bind Document Review to one saved `collection.sheet`. Reuse the OWL client action;
require `sheet_id` on every review RPC; drop the Collections menu. Maps the proposal and
deltas `document-review` (scoped queue/RPCs, no menu) and `collection-sheets` (header
action).

Impacts: models (sheet action, voucher RPC scope); views (header, menu delete); OWL
params; tests. Sequence none. Security none (no new groups). Migration: non-stored UI
helper only.

## Architecture Decisions

| Option                                    | Tradeoff                             | Decision                                                                                   |
| ----------------------------------------- | ------------------------------------ | ------------------------------------------------------------------------------------------ |
| Form object method vs bound client action | Flag + saved-id checks need Python   | `action_open_document_review` on `collection.sheet`; form `type="object"` header only      |
| `params.sheet_id` vs `context.active_id`  | Context can be stale/wrong model     | Mandatory `params.sheet_id` (int); OWL reads params only                                   |
| Positional `sheet_id` vs kwargs           | OWL `orm.call` args are positional   | `get_review_queue(sheet_id)`; mutations take `sheet_id` after ids, before `vals`/`degrees` |
| Keep vs clear client `path`               | `/odoo/document-review` stays global | Clear `path`; leftover URL still fail-closed on RPCs                                       |
| Menu XML omit vs `<delete>`               | Omit leaves `ir.ui.menu` after `-u`  | Remove menuitem **and** `<delete>` (Payment Lines leftover pattern)                        |
| Keep vs drop `_load_menus_blacklist`      | Blacklist is dead without the menu   | Delete `models/ir_ui_menu.py` and its `__init__` import                                    |
| Hide header via compute vs groups         | Flag is per company, not a group     | Non-stored `document_review_enabled`; `invisible="not id or not document_review_enabled"`  |

Rejected: company-wide fallback, extra ACL, stored fields, OWL-only checks.

## Data Flow

```
Sheet form header (saved, flag ON)
  → action_open_document_review()
       flag OFF / unsaved / empty set → UserError
       else → client action tag=collection.document_review
              params.sheet_id = sheet.id
  → OWL reads props.action.params.sheet_id
  → orm.call collection.voucher:
       get_review_queue([sheetId])
       action_review_approve([[id], sheetId, vals])
       action_review_reject([[id], sheetId])
       action_review_set_rotation([[id], sheetId, degrees])
  → _ensure_document_review_enabled → _require_review_sheet(sheet_id)
       queue: pending + attached + sheet_id
       mutations: member of that sheet, then existing eligibility/lock
```

Unsaved: hide button (`not id`); method refuses non-positive/`NewId`. Empty eligible
sheet: `[]`. Missing/invalid/other-sheet: `UserError`, not `[]`.

## File Changes

| File                                                       | Action | Description                                                             |
| ---------------------------------------------------------- | ------ | ----------------------------------------------------------------------- |
| `models/collection_sheet.py`                               | Modify | Compute helper; `action_open_document_review`                           |
| `models/collection_voucher.py`                             | Modify | Mandatory `sheet_id` on four RPCs; private validators                   |
| `models/ir_ui_menu.py`                                     | Delete | Menu blacklist obsolete                                                 |
| `models/__init__.py`                                       | Modify | Drop `ir_ui_menu` import                                                |
| `views/collection_views.xml`                               | Modify | Sheet `<header>` button + invisible helper field                        |
| `views/collection_document_review_views.xml`               | Modify | Keep xmlid/tag; clear `path`; remove menuitem; `<delete>` leftover menu |
| `static/src/document_review/document_review_action.esm.js` | Modify | Parse `params.sheet_id`; pass on all four RPCs                          |
| `__manifest__.py`                                          | Modify | Bump `19.0.1.10.0` → `19.0.1.11.0`                                      |
| `tests/test_collection_document_review.py`                 | Modify | Sheet-scoped RPCs; OWL arg strings; dedicated sheets                    |
| `tests/test_collection_document_review_flag.py`            | Modify | Flag refuse; action xmlid kept, menu gone; pass `sheet_id`              |
| `tests/test_collection_ui.py`                              | Modify | Menu absence; header visibility; action params                          |
| `tests/test_collection_acl.py`                             | Modify | Assign sheet; pass `sheet_id`; portal `AccessError`                     |
| `tests/test_collection_sheet.py`                           | Modify | Object action: params, flag OFF, unsaved                                |

Helpers XML/JS, Settings, MCP, voucher lifecycle: unchanged.

## Interfaces / Contracts

Non-stored sheet helper `document_review_enabled` (no DDL). Object action:
`ensure_one()`; reuse `_ensure_document_review_enabled`; refuse non-int id; return xmlid
`collection.action_collection_document_review` with `params.sheet_id`.

```python
action = self.env["ir.actions.actions"]._for_xml_id(
    "collection.action_collection_document_review"
)
action["params"] = dict(action.get("params") or {}, sheet_id=self.id)
return action
```

Voucher RPCs stay on `collection.voucher`. Private `_require_review_sheet`: flag first
(existing `"Document Review is not enabled."`); then `sheet_id` must be `int > 0` and
`browse().exists()`; else `UserError` (not `[]`). Mutations then require
`self.sheet_id == sheet` before `_ensure_review_eligible`. `@api.private` helpers. No
`_sql_constraints`. `<list>` unchanged.

OWL: missing/invalid `params.sheet_id` → notify, skip queue call. No `context.active_id`
fallback.

## Testing Strategy

Strict TDD. `invoke test -m collection`.

| RED case                                                       | Where                                     |
| -------------------------------------------------------------- | ----------------------------------------- |
| Cross-sheet isolation (queue A excludes B)                     | `test_collection_document_review.py`      |
| Empty/ineligible sheet → `[]`; other sheets ignored            | same                                      |
| Required sheet context: missing/0/`False`/bad id → `UserError` | same + flag file                          |
| Stale membership / other-sheet mutation refused                | same                                      |
| Feature-flag refusal (with or without `sheet_id`)              | `test_collection_document_review_flag.py` |
| Sheet action params (`tag`, `params.sheet_id`)                 | `test_collection_sheet.py`                |
| Header visible iff saved and flag ON; hidden OFF/unsaved       | `test_collection_ui.py`                   |
| Menu absence ON/OFF; xmlid gone; `load_menus`                  | UI + flag xmlid test                      |
| OWL RPC arguments include `sheet_id`                           | source assert in review tests             |
| Portal still `AccessError`                                     | `test_collection_acl.py`                  |
| Module upgrade XML/Python                                      | `-u collection`                           |
| E2E                                                            | N/A (disabled)                            |

Existing payload/rotation/lock/viewer/form-approve-OFF tests stay; call sites gain
`sheet_id` and a test sheet.

## Threat Matrix

N/A — no HTTP routing, shell, subprocess, VCS/PR automation, executable classification,
or process-integration boundary. Clearing `path` removes a webclient URL; RPCs remain
ORM.

## Migration / Rollout

No stored fields, no `migrations/`. `-u collection` to `19.0.1.11.0` (`<delete>` drops
leftover menu). Rollback: restore menu, global queue, prior RPC/OWL signatures, and
`ir_ui_menu.py` blacklist. No stored data to undo.

## Open Questions

None.
