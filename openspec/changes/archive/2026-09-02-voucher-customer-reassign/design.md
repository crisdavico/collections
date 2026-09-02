# Design: Voucher Customer Reassign

## Technical Approach

Kanban drop already writes `partner_id`. Open-sheet header opens a **new** XMLID
kanban grouped by Customer. `write()` projects allocation follow-up and
`super().write`s `partner_id`+`allocation_id` together. A voucher-side constrain
closes the allocation inverse gap. Specs were not on disk. No sudo, stored field, migrate, or OWL/MCP.

## Architecture Decisions

| Topic | Options | Tradeoff | Decision |
| ----- | ------- | -------- | -------- |
| Columns | `group_expand=True` vs method | Many2one `True` is not callable | `_read_group_partner_ids`; identity unless readable `collection_reassign_sheet_id` |
| Write order | Two-step vs same vals | Constrain fires mid-move | Same `super().write`; split per-record like `message_main_attachment_id` |
| Source residual | Silent unallocate vs block | Fully applied goes negative without line edits | `UserError` when projected residual `< 0` (`compare_amounts`) |
| Target | Always attach vs residual-safe | Empty alloc + no `residual_reason` cannot take a positive amount | Attach iff unique confirmed same-sheet still passes `_check_residual`; else `False` + `message_post` |
| Action views | `view_mode`+`view_id` vs `views` | Combo still loads the **state** kanban | `views` only (reassign kanban XMLID, then form). Omit `view_mode`/`view_id` |
| Kanban XMLID | Edit state kanban vs new | Tests freeze `default_group_by="state"`, `partner_id`×2, Selection `group_expand=True` | New `view_collection_voucher_reassign_kanban` |
| Closed freeze | New string vs membership | Operators see membership copy | Reuse closed-membership `UserError` |
| Helpers | Inline vs private | Keep `write()` flat | `@api.private` next to `_ensure_sheet_membership_unlocked` / `_ensure_allocation_membership_writable` |

## Data Flow

```mermaid
sequenceDiagram
    participant A as action_open_voucher_reassign
    participant K as Reassign kanban
    participant W as voucher.write
    A->>K: open sheet; domain sheet_id; context collection_reassign_sheet_id
    K->>W: drop writes partner_id
    W->>W: freeze; source residual block; target or False; same-vals write; chatter if unallocated
```

Unsaved/closed action: `_ensure_saved_sheet` or membership `UserError`. Bad expand context: return `groups` (no sudo).

## File Changes

| File | Action | Description |
| ---- | ------ | ----------- |
| `models/collection_voucher.py` | Modify | Method `group_expand`; `write()` partner branch; constrain; private helpers |
| `models/collection_sheet.py` | Modify | `action_open_voucher_reassign` beside `action_open_vouchers` |
| `views/collection_views.xml` | Modify | New reassign kanban; header after Document Review. Do **not** edit state kanban |
| `__manifest__.py` | Modify | `19.0.1.26.0` |
| `tests/test_collection_ui.py` | Modify | New kanban+header; keep state-kanban freezes; add xmlid to `partner_id` counts; `formatted_read_group` expand |
| `tests/test_collection_sheet.py` | Modify | Action shape/unsaved/closed; freeze includes `partner_id` |
| `tests/test_collection_voucher.py` | Modify | Follow-up, residual block, constrain, chatter |
| `tests/test_collection_allocation.py` | Modify | Voucher-`partner_id` mismatch; residual still confirmed-only |
| `tests/test_collection_company_migration.py` | Modify | Rename `test_manifest_version_is_1_25_0` → `1_26_0`; keep `migrations/19.0.1.25.0/` asserts |
| `AGENTS.md` | Modify | Apply/archive UI bullets (header+kanban; closed freeze includes `partner_id`; same-vals follow-up; `19.0.1.26.0`). Not this design write |

**Model:** no stored field. **Sequence / security / migrate folder:** none.

## Interfaces / Contracts

```python
partner_id = fields.Many2one(..., group_expand="_read_group_partner_ids")

@api.model
def _read_group_partner_ids(self, groups, domain):
    # identity unless readable context sheet; else allocation ∪ voucher partners, partner _order

def action_open_voucher_reassign(self):
    self.ensure_one(); self._ensure_saved_sheet()
    if self.state != "open":
        raise UserError(_("Closed collection sheets cannot change membership. Reopen first."))
    return {
        "type": "ir.actions.act_window", "name": _("Reassign Customers"),
        "res_model": "collection.voucher",
        "views": [(self.env.ref("collection.view_collection_voucher_reassign_kanban").id, "kanban"), (False, "form")],
        "domain": [("sheet_id", "=", self.id)],
        "context": {"collection_reassign_sheet_id": self.id, "group_by": "partner_id",
                    "default_sheet_id": self.id, "default_seller_id": self.seller_id.id},
    }
```

Kanban: `default_group_by="partner_id"`, `records_draggable="1"`,
`create`/`quick_create`/`group_create`/`group_delete`/`group_edit` `"0"`,
`groups_draggable="0"`, `class="o_kanban_mobile"`, `t-name="card"`, `partner_id`
not readonly. Header `invisible="not id or state != 'open'"`.

`write()` partner branch **before** the existing `allocation_id` check so injected
id is gated. Helpers: `_ensure_partner_reassign_unlocked`,
`_vals_with_partner_allocation`, `_check_voucher_allocation_partner`
`@api.constrains("partner_id", "allocation_id")`. Voucher **state** does not freeze
`partner_id`; validated allocation membership still does.

## Testing Strategy

Strict TDD: invert tests **before** XML/Python.

| Layer | What | Approach |
| ----- | ---- | -------- |
| Arch | New kanban+header; state kanban unchanged (`partner_id`×2); **add** reassign xmlid | `test_collection_ui.py` lxml |
| Expand | Empty allocation columns + stray partners; identity without context | `formatted_read_group` + `read_group_expand=True` |
| Action | `views`/domain/context; no `view_mode`/`view_id`/`path`; `.new()` and closed `UserError` | Mirror `test_action_open_vouchers_*` |
| Write | Attach / unallocated+chatter; fully applied source refused; closed `partner_id`; two-step constrain; any voucher state | `test_collection_voucher.py` + freeze in `test_collection_sheet.py` |
| Alloc | Voucher `partner_id` mismatch; residual unchanged | `test_collection_allocation.py` |
| Version | Manifest `19.0.1.26.0`; **no** `migrations/19.0.1.26.0/` | Rename version test only |
| E2E | None | Unavailable |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file
classification, or process-integration boundary.

## Migration / Rollout

No migration. Manifest `19.0.1.26.0`. Upgrade `-u collection`.

## Risks

- Fully applied source vs any-state move: refuse the drop.
- Review size near 400 lines; keep OWL/MCP/line revision out.
- Partner-count UI test must **gain** the new xmlid; state-kanban count stays 2.

## Rollback

Revert `19.0.1.26.0`: drop new view/action, `write()` branch, `group_expand`,
voucher constrain. No stored field; state kanban/MCP/allocations stay.

## Open Questions

- [ ] None
