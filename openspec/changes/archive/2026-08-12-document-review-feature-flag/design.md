# Design: Document Review Feature Flag

## Technical Approach

Add `res.company.document_review_enabled` (Boolean, default `False`) and expose it on
Settings as a related field (`readonly=False`, not `config_parameter`). One
`@api.private` helper on `res.company` reads `self.env.company` (vouchers have no
`company_id`). OFF: skip `_ensure_no_pending_attached_review`, refuse the four review
RPCs with `UserError`, hide `collection.menu_collection_document_review` via
`_load_menus_blacklist`. ON: current review behavior unchanged. Line `state` / audit
columns and payment-line views stay. Maps to proposal approach 1 and deltas
`document-review` (flag, menu, RPC refuse) and `collection-vouchers` (validate /
approve / reject only when ON).

Impacts: models (company, settings, menu, voucher/line gates); views (new Settings
inherit only); sequence none; security none (no new ACL/groups; Settings
`groups="base.group_system"`); migration additive `-u` only.

## Architecture Decisions

| Option | Tradeoff | Decision |
| ------ | -------- | -------- |
| Company Boolean vs `ir.config_parameter` | Per-company vs DB-global | `res.company` Boolean, default False |
| Related `readonly=False` vs `config_parameter=` | Related writes the company row | `related="company_id.document_review_enabled", readonly=False` |
| `_load_menus_blacklist` vs `menu.active` | `active` is global and races | Blacklist xmlid when OFF; never set `active` |
| One private helper vs duplicated reads | Single `env.company` source | `res.company._document_review_enabled()` |
| Cache clear vs stale menus | `load_menus` cache is uid/debug/lang only | `self.env.registry.clear_cache()` on flag write |
| Opt-in tests vs rewrite suite | Default OFF breaks queue/validate-blocked | Enable flag in existing review tests |

## Data Flow

```
Settings #collections ──related──► res.company.document_review_enabled
                                      │
                                      ├─ write → registry.clear_cache()
                                      ▼
         load_menus → _load_menus_blacklist (append review menu id if OFF)

action_validate → _ensure_no_pending_attached_review
    helper OFF → return; ON → existing pending-attached UserError

get_review_queue / action_review_{approve,reject,set_rotation}
    helper OFF → UserError("Document Review is not enabled."); ON → unchanged
```

Direct `/odoo/document-review` may still load OWL; RPCs must raise, not return `[]`.

## File Changes

| File | Action | Description |
| ---- | ------ | ----------- |
| `models/res_company.py` | Create | Boolean, helper, `write` cache clear |
| `models/res_config_settings.py` | Create | Related Boolean `readonly=False` |
| `models/ir_ui_menu.py` | Create | Blacklist review menu id when OFF |
| `views/res_config_settings_views.xml` | Create | Inherit `base.res_config_settings_view_form`; `<app name="collections" groups="base.group_system">` |
| `models/__init__.py` | Modify | Import the three new models |
| `__manifest__.py` | Modify | Add settings view to `data`; bump version |
| `models/collection_voucher.py` | Modify | Gate no-op when helper is false |
| `models/collection_voucher_line.py` | Modify | Four RPCs raise before queue/lock when OFF |
| `views/collection_document_review_views.xml` | Unchanged | xmlids stay |
| `tests/test_collection_document_review.py` | Modify | `setUp` sets flag True (covers `_neutralize_preexisting_queue`) |
| `tests/test_collection_voucher.py` | Modify | Opt-in `test_action_validate_blocked_when_attached_line_pending` only |
| `tests/test_collection_acl.py` | Modify | Enable flag in review ACL tests so portal still `AccessError` |
| `tests/test_collection_ui.py` | Modify | Keep xmlid contract; add settings arch + blacklist/`load_menus` |
| `tests/test_collection_document_review_flag.py` | Create | OFF coverage |
| `tests/__init__.py` | Modify | Import flag tests |

Stay inside `odoo/custom/src/private/collection/`. No OWL, MCP, or security CSV.

## Interfaces / Contracts

```python
# res.company
document_review_enabled = fields.Boolean(default=False)

@api.model
@api.private
def _document_review_enabled(self):
    return bool(self.env.company.document_review_enabled)

# res.config.settings
document_review_enabled = fields.Boolean(
    related="company_id.document_review_enabled",
    readonly=False,
)

# ir.ui.menu
@api.model
def _load_menus_blacklist(self):
    res = super()._load_menus_blacklist()
    if not self.env.company._document_review_enabled():
        menu = self.env.ref(
            "collection.menu_collection_document_review",
            raise_if_not_found=False,
        )
        if menu:
            res.append(menu.id)
    return res
```

On `res.company.write`, if `"document_review_enabled" in vals`, call
`self.env.registry.clear_cache()`. Callers: `self.env.company._document_review_enabled()`.

## Testing Strategy

Strict TDD: RED then GREEN. `invoke test -m collection`.

| Layer | What to Test | Approach |
| ----- | ------------ | -------- |
| Unit | Default False; validate with pending attached succeeds; four RPCs `UserError` not `[]` | New flag tests; do not enable flag |
| Unit | Queue/approve/reject/rotation/validate-blocked | `setUp` / those tests set flag True |
| Unit | Portal review `AccessError` | Enable flag in those tests so ACL hits `search`/write |
| Unit | Settings field + view `name="collections"`; menu xmlid exists; blacklisted/absent from `load_menus` when OFF, present when ON | UI + flag tests |
| Integration | `-u collection` adds column | Existing upgrade path |
| E2E | N/A | Not available |

## Threat Matrix

N/A — this change does not add routing, shell, subprocess, VCS/PR automation,
executable-file classification, or process-integration boundaries.

## Migration / Rollout

Additive company column via ORM; `odoo -u collection` only; no `migrations/` and no
data XML. Pending attached lines stay pending; enabling later re-applies the validate
gate. Rollback: set the flag False or revert the module.

## Open Questions

- [ ] None. Odoo core is not in this checkout; apply must confirm
      `_load_menus_blacklist` is `@api.model` and returns a list of menu ids.
