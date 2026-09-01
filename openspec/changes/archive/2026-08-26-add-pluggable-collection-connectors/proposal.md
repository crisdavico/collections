# Proposal: Add Pluggable Collection Connectors

Admins pick a company-scoped seller source; agents get a stable MCP list. Phone lookup
and voucher/sheet writes stay unchanged.

## Intent

No connector, binding, or list MCP exists. Providers must plug in without baking SQLite
into `collection` or duplicating MuK tool names.

## Scope

### In Scope

- `collection.connector` (company-scoped); `res.company.collection_connector_id`;
  writable related field on Collection Settings
- Dispatcher: `selection_add` + `_sqlite_test_connection` / `_sqlite_list_sellers`; no
  competing mixin overrides; no duplicate MuK names
- `collection.connector.seller.binding`: 1:1 external seller ID ↔ `res.users`;
  company-consistent uniqueness
- Method-discovered MCP `list_collection_sellers` (read); only
  `env.company.collection_connector_id` (no caller `company_id`); normalized sellers,
  source metadata, `odoo_seller_id` when bound
- Sibling `collection_connector_sqlite` (depends on `collection`): read-only SQLite,
  admin connection-test, fixed `sellers` schema, `mode=ro`, no path/SQL leakage
- Two ~400-line units: (1) collection facade/bindings/MCP; (2) SQLite addon
- Planning follow-up: extend `apply.roots` for the sibling path (not app code now)

### Out of Scope

- ERP/SQLite write-back; extra providers; config on `res.company`
- Changing `get_seller_id` or voucher/sheet write MCP; `enabled_seller_ids` list filter;
  Nebula MCP rename

## Capabilities

### New Capabilities

- `collection-connectors`: company-scoped connector, dispatcher, seller bindings,
  `list_collection_sellers` MCP, SQLite first provider

### Modified Capabilities

- None

## Approach

MCP contract stays in `collection`. Config lives on `collection.connector`; company
selects the active record. Addons implement `_<type>_*` only. Missing/inactive connector
fails closed (`UserError`). Never `sudo()`; never add DB `muk_mcp.tool` rows. List ≠ NEW
voucher permission (`_assert_new_work` still gates create).

## Affected Areas

- New: `collection_connector.py` (provider + dispatcher),
  `collection_connector_seller_binding.py` (1:1 bindings),
  `tools/collection_connector.py` (`list_collection_sellers`)
- Modified: `res_company.py` (`collection_connector_id`); Settings + Collection Settings
  view; `security/*`, views, tests, AGENTS.md
- Unchanged: `tools/seller_lookup.py`, voucher MCP
- New (parent git): `odoo/custom/src/private/collection_connector_sqlite/`

## Risks

- SQLite addon outside collection git and `apply.roots` (High): roots update as planning
  follow-up; unit 1 stays in collection
- Path/SQL leakage (Med): generic `UserError`
- Combined PR >400 lines (High): two delivery units
- Uninstall leftover `sqlite` Selection (Med): explicit `ondelete`; clear company
  pointer
- Bound user not enabled (Med): list ≠ collect permission

## Rollback Plan

Clear each company's `collection_connector_id`, then uninstall
`collection_connector_sqlite`. Existing vouchers, sheets, `get_seller_id`, and
`create_collection_vouchers` stay unchanged.

## Dependencies

- `collection` + existing `muk_mcp`; sqlite addon depends on `collection`; stdlib
  `sqlite3`; container-visible Char path (ops)
- Follow-up: `openspec/config.yaml` `apply.roots` must include parent
  `odoo/custom/src/private/` before unit 2 apply

## Success Criteria

- [ ] Company can select an active `collection.connector` from Collection Settings
- [ ] `list_collection_sellers` uses only `env.company.collection_connector_id`; returns
      normalized sellers with source metadata and `odoo_seller_id` when bound
- [ ] SQLite connection-test is read-only against the fixed `sellers` schema with no
      path/SQL leakage
- [ ] `get_seller_id` and voucher/sheet write contracts unchanged
- [ ] Rollback (clear connector + uninstall sqlite) leaves existing vouchers/sheets
      intact
