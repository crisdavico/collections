# Proposal: Document Review Feature Flag

## Intent

Document Review is always on and blocks Validate while attached lines stay `pending`.
Operators need it **off by default**. Settings admins toggle per company; operators lose
the menu when OFF and Validate is unblocked.

## Scope

### In Scope

- `res.company.document_review_enabled` default `False` (not `ir.config_parameter`)
- Settings admin toggle at `/odoo/settings#collections`
- OFF: hide Document Review menu; Validate succeeds with unreviewed attachments; refuse
  `get_review_queue` / `action_review_approve` / `action_review_reject` /
  `action_review_set_rotation`
- ON: current review behavior unchanged
- Keep line `state` / audit columns in DB and payment-line views (ignored when OFF)
- Opt-in existing review tests; add OFF coverage

### Out of Scope

- `company_id` on vouchers/lines; hiding payment-line state UI; MCP / attachments /
  Nebula; `ir.ui.menu.active`

## Capabilities

### New Capabilities

None

### Modified Capabilities

- `document-review`: settings page, default off, menu/RPC gating
- `collection-vouchers`: validate gate and approve/reject voucher side-effects **only
  when the company flag is on**

## Approach

Approach 1: company Boolean + settings related `readonly=False`; inherit
`base.res_config_settings_view_form`
(`<app name="collections" groups="base.group_system">`); `_load_menus_blacklist` (not
`menu.active`); one `@api.private` helper; skip `_ensure_no_pending_attached_review` /
refuse review RPCs when OFF; `self.env.company`; clear cache on write; additive `-u`.

## Affected Areas

| Area                                                               | Impact    | Description                                     |
| ------------------------------------------------------------------ | --------- | ----------------------------------------------- |
| `models/res_company.py`, `res_config_settings.py`, `ir_ui_menu.py` | New       | Flag, helper, menu blacklist                    |
| `views/res_config_settings_views.xml`                              | New       | `#collections` settings app                     |
| `models/collection_voucher.py`, `collection_voucher_line.py`       | Modified  | Skip validate gate; refuse review RPCs when OFF |
| `models/__init__.py`, `__manifest__.py`                            | Modified  | Import + settings view                          |
| `views/collection_document_review_views.xml`                       | Unchanged | xmlids stay; blacklist visibility               |
| `tests/test_collection_{document_review,voucher,acl,ui}.py`        | Modified  | Opt-in flag; `load_menus` + settings tests      |

## Risks

| Risk                                    | Likelihood | Mitigation                                   |
| --------------------------------------- | ---------- | -------------------------------------------- |
| `load_menus` cache not company-keyed    | Med        | Clear cache on write; RPC refuse is the gate |
| Review tests assume always-on           | High       | Opt-in flag; new OFF tests                   |
| Flag follows `env.company`, not voucher | Low        | Accepted; no `company_id`                    |
| OWL client action remains               | Med        | RPCs raise `UserError` (not empty queue)     |

## Rollback Plan

Disable the flag or revert the module. Additive column; no migration.

## Dependencies

- Odoo 19 settings `company_id` and `ir.ui.menu._load_menus_blacklist`
- Existing Document Review menu xmlid and review RPCs; stay inside `collection`

## Success Criteria

- [ ] Fresh install / upgrade: flag off; Document Review not in menus; Validate works
      with pending attached lines
- [ ] Settings admin enables it for a company: menu appears; current review spec applies
      for that company
- [ ] Turning it on later: existing pending attached lines then block Validate (no data
      migration)
- [ ] Rollback: disable the flag (or revert the module)
