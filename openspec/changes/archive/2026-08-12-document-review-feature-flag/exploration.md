## Exploration: Gate document-review behind a per-company Settings flag (default OFF)

### Current State

Document Review is always on. There is **no** `res.company` / `res.config.settings`
extension in this addon (`models/` is only voucher + line).

- `collection.voucher` has **no** `company_id`; currency already uses
  `self.env.company.currency_id`.
- `action_validate()` always calls `_ensure_no_pending_attached_review()`, which blocks
  while any attachment-bearing line is `pending`.
- Line RPCs `get_review_queue`, `action_review_approve`, `action_review_reject`,
  `action_review_set_rotation` always run (ACL: `base.group_user`). Last attached
  approve may `action_validate()`; line reject calls `voucher.action_reject()`.
- Menu `collection.menu_collection_document_review` (parent `menu_collection_root`,
  sequence 30) + client action tag `collection.document_review`, path `document-review`
  (`/odoo/document-review`). `ir.ui.menu.active` is a **global** boolean.
- Line `state` / `reviewed_by` / `reviewed_at` / `attachment_rotation` stay on
  payment-line views; attachment write still resets review to pending.
- Specs: `document-review/spec.md` (queue/UI/ACL) and `collection-vouchers/spec.md`
  (validate gate + approve/reject voucher side-effects) assume the workflow is always
  active.
- Tests that exercise the live workflow (will break if default OFF without opt-in):
  `tests/test_collection_document_review.py`
  (queue/approve/reject/rotation/validate-blocked; `_neutralize_preexisting_queue` calls
  `get_review_queue`), `tests/test_collection_voucher.py`
  `test_action_validate_blocked_when_attached_line_pending`,
  `tests/test_collection_acl.py` internal-user review tests. UI xmlid tests only assert
  the menu **record**, not `load_menus` visibility.

Odoo 19: `res.config.settings.company_id` already exists (`base_setup`). Related company
booleans use `related='company_id.<field>', readonly=False`. Settings hash is
`<app name="...">` (e.g. calendar → `#calendar`). `ir.ui.menu.load_menus` applies
`_load_menus_blacklist()` then caches on **uid + debug + lang only** (not company).

### Affected Areas

- `models/collection_voucher.py` — skip `_ensure_no_pending_attached_review` when flag
  OFF
- `models/collection_voucher_line.py` — refuse queue + review RPCs when OFF
- `models/__init__.py` — import new models
- `models/res_company.py` _(new)_ — `document_review_enabled` boolean, default `False`
- `models/res_config_settings.py` _(new)_ — related field, `readonly=False`
- `models/ir_ui_menu.py` _(new)_ — `_load_menus_blacklist` hides Document Review menu
  per `env.company`
- `views/res_config_settings_views.xml` _(new)_ — inherit
  `base.res_config_settings_view_form`, `<app name="collections">` →
  `/odoo/settings#collections`
- `__manifest__.py` — add settings view to `data`
- `views/collection_document_review_views.xml` — menu xmlids stay; visibility via
  blacklist, not `active`
- `tests/test_collection_document_review.py`, `test_collection_voucher.py`,
  `test_collection_acl.py` — opt-in `env.company.document_review_enabled = True`
- `tests/test_collection_ui.py` — keep xmlid contract; add load_menus / settings
  field+view coverage
- `openspec/specs/document-review/spec.md` and `collection-vouchers/spec.md` — delta in
  later phases (validate gate and review RPCs become flag-conditional)
- Out of scope (do not touch): voucher/line `company_id`, payment-line state UI,
  MCP/`tools/`, Nebula, OWL except as needed for RPC errors on direct URL

### Approaches

1. **`res.company` boolean + settings inherit + `_load_menus_blacklist`** — Per-company
   flag default `False`; Settings related field; `<app name="collections">`; hide menu
   via Odoo’s blacklist hook (not `menu.active`); single private helper (e.g.
   `res.company._document_review_enabled()` / `_ensure_document_review_enabled()`) used
   by voucher validate-gate and line queue/review actions. Direct
   `/odoo/document-review` and RPCs still refuse when OFF. Clear `ir.ui.menu` / registry
   cache when the flag is written (parent `load_menus` cache is not company-keyed).

   - Pros: Matches locked product (per company, Settings `#collections`, default OFF);
     standard Odoo 19 settings + menu patterns; RPCs remain the real gate; menu `active`
     stays global-safe
   - Cons: `load_menus` ormcache omits company — mixed-flag company switch can show a
     stale menu until cache clear (UX only; RPCs still refuse); helper + three new model
     files
   - Effort: Medium

2. **`ir.config_parameter` global flag** —
   `config_parameter='collection.document_review_enabled'` on settings (or
   `ir.config_parameter` get/set). One value for the whole DB.

   - Pros: Slightly less code; `load_menus` uid cache is less wrong (no per-company
     split)
   - Cons: Violates locked per-company decision; Settings company switch would lie;
     `config_parameter` fields are global by design (`res_config.py`)
   - Effort: Low

3. **Toggle `ir.ui.menu.active`** — Write `menu_collection_document_review.active` when
   the flag changes.
   - Pros: Tiny menu change
   - Cons: `active` is **global** — cannot be per-company; does not gate validate/RPCs;
     concurrent companies would clobber each other
   - Effort: Low (and wrong)

### Recommendation

Use **approach 1**. The codebase does not make it unsafe: no existing settings models,
vouchers already read `self.env.company`, and core already exposes
`_load_menus_blacklist` (hr, project, recruitment) plus
`related='company_id.*', readonly=False` settings booleans.

Implementation notes (verify-safe):

- Field: `res.company.document_review_enabled = fields.Boolean(default=False)`; settings
  related with `readonly=False`. Do **not** use `config_parameter` (that is approach 2).
- Settings view: inherit `base.res_config_settings_view_form`,
  `<app name="collections" groups="base.group_system">` so only Settings admins toggle
  it at `#collections`.
- Menu: override `_load_menus_blacklist` to append
  `collection.menu_collection_document_review` when
  `not self.env.company.document_review_enabled`. Do not set `active=False`.
- Helper: one `@api.private` on `res.company` (or thin wrappers on voucher/line) so
  `_ensure_no_pending_attached_review` no-ops when OFF, and
  queue/approve/reject/set_rotation raise `UserError` when OFF. When ON, current
  behavior unchanged.
- Cache: on flag write, `self.env.registry.clear_cache()` (or equivalent) so turning the
  flag on shows the menu without a worker restart.
- Tests: enable the flag in existing review/validate-blocked/ACL-allow cases (including
  `_neutralize_preexisting_queue`). New tests for OFF: validate with pending attached
  lines succeeds; review RPCs refuse; menu id absent from `load_menus` / blacklist;
  settings field + inherited view with `name="collections"`. Portal `AccessError` tests
  stay as-is.
- Additive `res.company` column: module `-u` is enough; no data migration.

### Risks

- **`load_menus` cache is not company-keyed.** After a company switch with mixed flags,
  the Document Review menu can be stale until cache invalidation. Mitigate by clearing
  cache on flag write; keep RPC refuse as the security/UX backstop for
  `/odoo/document-review`.
- **Existing tests assume always-on review.** Missing opt-in (especially
  `_neutralize_preexisting_queue` → `get_review_queue`) will fail the whole
  document-review suite under default OFF.
- **Vouchers are not company-scoped.** Flag follows `env.company` (Settings / current
  company), not the voucher. Accepted for this change; do not add `company_id` here.
- **OWL client action record remains.** Direct URL still loads the client; it must fail
  on RPC, not look like an empty queue.

### Ready for Proposal

Yes — product decisions are locked, the intended design matches Odoo 19 core, and no
code finding forces a different approach. Orchestrator should run **sdd-propose** for
`document-review-feature-flag` with approach 1, then spec deltas for `document-review`
(flag + menu + RPC refuse) and `collection-vouchers` (validate gate only when enabled).
