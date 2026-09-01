# Exploration: add-pluggable-collection-connectors

CodeGraph: MCP namespace `user-codegraph` was unavailable;
`gentle-ai codegraph init --cwd <collection-git-root>` failed with exit 127 (codegraph
CLI not runnable from WSL). Investigation used Shell `cat`/`rg`/`ls` against real files.

## Exploration: Pluggable collection connectors

### Current State

Collection (`19.0.1.17.0`) is a company-scoped cobranzas addon with no connector,
SQLite, or external-seller-id models. Integration config today lives only as Collection
Settings on `res.company` with related writable `res.config.settings`.

- **Settings pattern:** `models/res_company.py` stores `enabled_seller_ids`,
  `auto_create_sheet`, `allowed_document_type_ids`, `document_review_enabled`.
  `models/res_config_settings.py` mirrors them as `related=…, readonly=False`. UI XMLID
  `collection.action_collection_config_settings` in
  `views/res_config_settings_views.xml` (label “Collection Settings”; menus
  `groups="base.group_system"`). Tests: `tests/test_collection_company_settings.py`
  (persist via `settings.execute()`), `tests/test_collection_ui.py` (XMLID/label).
- **MCP discovery:** method-discovered `@mcp_tool` on `muk_mcp.mixin` —
  `tools/collection_voucher.py` `create_collection_vouchers` (`category=write`,
  `registry=mcp`) and `tools/seller_lookup.py` `get_seller_id` (`category=read`,
  `registry=mcp`). No DB `muk_mcp.tool` rows. Never `sudo()`. Tests assert `kind=method`
  via `get_tool_index` (`tests/test_collection_mcp_seller_lookup.py`,
  `tests/test_collection_mcp_tool.py`).
- **`get_seller_id`:** required `mobile`; unique internal `res.users.phone` after AR
  normalize → `{seller_id}` only. **Unfiltered** vs `enabled_seller_ids` / company
  allow-lists (spec + tests). Reuses `_collection_require_internal_seller` from the
  write mixin. AGENTS.md: leave `seller_lookup.py` unchanged unless a later change
  explicitly filters it.
- **Company isolation:** required `company_id` (default `env.company`) on voucher/sheet.
  Global `ir.rule` `[('company_id', 'in', company_ids)]` in
  `security/collection_security.xml` for voucher, sheet, snapshot. `_assert_new_work`
  gates NEW voucher/sheet work (enabled seller + allowed type). MCP create stamps
  `env.company`. Catalog `collection.document.type` has no company rule (read-only ACL).
- **ACL:** `base.group_user` only in `security/ir.model.access.csv`; no extra groups.
  Snapshot: read + gated create. Catalog: read-only. Collection Settings UI is
  system-gated even though company fields use core company write rights.
- **Manifest / siblings:** `__manifest__.py` depends `base`, `mail`, `muk_mcp`. Doodba
  loads everything under `odoo/custom/src/private/` (addons.yaml does not list private
  addons). Collection is its **own git** (`nebula_odoo`); `seedian_webpage` and
  `seedian_product_catalog_mcp` live in the **parent Seedian** git.
  `openspec/config.yaml` `apply.roots` is only collection + `nebula-agent`. There is
  **no** `collection_connector_sqlite` today.
- **Uniqueness pattern:** Odoo 19 `models.Constraint('UNIQUE(...)')` on
  `collection.document.type.code`, voucher `document_id`, snapshot
  `(voucher_id, revision)`.
- **Specs:** `openspec/specs/seller-lookup/spec.md` and
  `openspec/specs/collection-vouchers/spec.md` cover phone lookup and voucher MCP. No
  `collection-connectors` capability exists.
- **Odoo 19 `selection_add`:** core `fields.Selection` requires `ondelete` for added
  values (`set null` / `cascade` / `set default` / `set VALUE` / callable).
  Payment-style example: `payment_stripe`
  `selection_add=[('stripe', "Stripe")], ondelete={'stripe': 'set default'}`.

Settled product shape is **absent** in code: no `collection.connector`, no seller
bindings, no `list_collection_sellers`, no `collection_connector_id` on company.

### Affected Areas

- `models/res_company.py` — add `collection_connector_id` Many2one; do not dump
  connector config onto company.
- `models/res_config_settings.py` + `views/res_config_settings_views.xml` — related
  writable selector on Collection Settings; keep XMLID
  `collection.action_collection_config_settings`.
- **New** `models/collection_connector.py` — persistent provider record (`name`,
  `company_id`, `connector_type`, active/config state) + dispatcher (`test_connection` /
  `list_sellers` → `_sqlite_*` etc.).
- **New** `models/collection_connector_seller_binding.py` — 1:1 external seller id ↔
  `res.users` per connector; company consistency + uniqueness.
- `models/__init__.py`, `__manifest__.py` (version bump),
  `security/collection_security.xml`, `security/ir.model.access.csv`,
  `views/collection_views.xml` (connector/binding UI under Configuration).
- **New** `tools/collection_connector.py` (or similar) — one `@mcp_tool`
  `list_collection_sellers` on `muk_mcp.mixin`; `tools/__init__.py` import. Do **not**
  redefine the tool in connector addons.
- `tools/seller_lookup.py`, `tools/collection_voucher.py` — **no-regression**; leave
  `get_seller_id` and voucher contracts unchanged.
- `tests/__init__.py` + new `tests/test_collection_connector*.py`; extend
  ACL/settings/UI tests. No-regression: `test_collection_mcp_seller_lookup.py`,
  `test_collection_mcp_tool.py`.
- `openspec/specs/` — **new** capability `collection-connectors`; seller-lookup /
  collection-vouchers stay as no-regression (do not filter `get_seller_id`).
- `AGENTS.md` — document connector model, MCP list tool, sibling addon, never-sudo / no
  DB tool rows.
- **Outside this git / apply.roots:** sibling
  `odoo/custom/src/private/collection_connector_sqlite/` (parent Seedian repo):
  `depends: ['collection']`, `selection_add` for `sqlite`, Char path +
  `_sqlite_test_connection` / `_sqlite_list_sellers`, admin test-connection action,
  stdlib `sqlite3` URI `mode=ro`.

### Approaches

1. **Provider record + type dispatcher (settled)** — `collection.connector` holds
   config; public methods dispatch to `_<type>_*`; addons use `selection_add` + private
   methods; one MCP tool in base resolves `env.company.collection_connector_id` only.

   - Pros: stable MCP names; no competing mixin overrides; company-scoped like Settings;
     matches `payment.provider` / Stripe.
   - Cons: two modules; SQLite work lives outside collection git and current
     `apply.roots`.
   - Effort: Medium (split into two review units).

2. **Competing mixin overrides of shared operations** — each connector addon overrides
   the same `list_sellers` / MCP tool on `muk_mcp.mixin`.

   - Pros: fewer models.
   - Cons: rejected: duplicate MuK tool names, MRO fights, last-installed wins.
   - Effort: Low, unsafe.

3. **All config on `res.company`** — SQLite path and type fields on company/settings.
   - Pros: no new model.
   - Cons: rejected: company becomes a junk drawer; multi-connector history/bindings
     don’t fit; Settings XML grows per provider.
   - Effort: Low.

Open implementation details (only these were compared):

| Detail             | Options                                                          | Lean                                                                                                                                                                              |
| ------------------ | ---------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SQLite path        | Char filesystem path vs Binary/attachment vs filestore           | **Char path** on the sqlite inherit (container-visible file; live DB). Binary would snapshot upload and hide live ERP files. Never put path/SQL in `UserError`.                   |
| Dispatch home      | Methods on `collection.connector` vs extra mixin                 | **On the connector model** (`getattr(self, f'_{code}_list_sellers')`). Mixin stays MCP-only.                                                                                      |
| MCP module         | New `tools/collection_connector.py` vs add to `seller_lookup.py` | **New module**. AGENTS.md forbids casual edits to `seller_lookup.py`; lookup stays phone-only.                                                                                    |
| Binding uniqueness | `models.Constraint` UNIQUE vs `@api.constrains` only             | **Both:** SQL `UNIQUE(connector_id, external_seller_id)` and `UNIQUE(connector_id, user_id)`; `@api.constrains` for company match (`binding.company_id == connector.company_id`). |

### Recommendation

Implement the settled **provider-record + dispatcher** design.

- Base unit in **collection**: `collection.connector` with empty/base `connector_type`
  Selection; `res.company.collection_connector_id`; related writable Settings field;
  `collection.connector.seller.binding`; MCP `list_collection_sellers` (`category=read`,
  `registry=mcp`, method-discovered, no DB row, no `sudo()`, no caller `company_id`).
  Return normalized rows with explicit source metadata and `odoo_seller_id` when bound.
  Missing/inactive connector → fail closed with a generic `UserError`. Do not apply
  `enabled_seller_ids` as a list filter (same spirit as unfiltered `get_seller_id`; NEW
  voucher work still uses `_assert_new_work`).
- SQLite unit in **`collection_connector_sqlite`**:
  `selection_add=[('sqlite', 'SQLite')], ondelete={'sqlite': 'cascade'}` (or
  `set default` if uninstall should keep the row with type cleared — prefer
  **cascade/unlink sqlite records or clear company pointer** so leftover `sqlite` values
  cannot exist after uninstall). Fields + `_sqlite_*` only. Open
  `sqlite3.connect('file:%s?mode=ro' % path, uri=True)`. Schema
  `sellers(id TEXT PRIMARY KEY, name TEXT NOT NULL, mobile TEXT, active INTEGER NOT NULL DEFAULT 1)`.
  Admin test-connection action. Normalize failures.
- New OpenSpec capability **`collection-connectors`**. Delta seller-lookup/vouchers only
  if needed to state “unchanged / not replaced.”
- Delivery: two PRs (~400-line budget). Rollback: clear each company’s
  `collection_connector_id`, uninstall sqlite addon;
  vouchers/sheets/`get_seller_id`/create tool untouched.
- ACL exception vs “no extra groups”: grant `base.group_user` **read** on connector +
  binding (MCP agent is internal); grant write/create/unlink to `base.group_system`
  (matches Settings menus). Company `ir.rule` on both new models. Never `sudo()`.

### Risks

- **`collection_connector_sqlite` is outside collection git and outside
  `openspec/config.yaml` `apply.roots`.** Apply in this change folder cannot legally
  write the sibling addon unless roots are extended (parent Seedian path) or unit 2 is a
  follow-up change in the parent repo. Flag for propose/tasks.
- **Cursor-ignore / nested git:** collection files are often tool-invisible; sqlite
  addon will be parent-repo files beside a nested `.git`. Easy to commit to the wrong
  tree.
- **Path and SQL leakage** in logs/`UserError` if sqlite exceptions are re-raised raw.
- **ACL tension:** write gated by `group_system` introduces a second group on collection
  models (Settings already uses it in views). Read for `group_user` is required so MCP
  list works without `sudo()`.
- **Uninstall leftover Selection values:** sqlite `ondelete` must be explicit or
  upgrade/uninstall breaks.
- **Container filesystem:** Char path only works if the Odoo container can read the file
  (volume mount); that is ops, not ORM.
- **Binding vs enabled sellers:** listing a bound user who is not enabled still cannot
  create NEW vouchers; document so agents do not assume list ≡ allowed to collect.
- Combined base+sqlite in one PR likely exceeds the 400-line review budget — already
  split into two units.

### Ready for Proposal

**Yes.** Product decisions are settled and match current code gaps. Propose should lock
the provider-record + dispatcher design, new capability `collection-connectors`, two
delivery units, rollback, and the apply.roots / sibling-git flag. Do not reopen
mixin-override or company-as-config. Keep `get_seller_id` and voucher MCP contracts
unchanged.
