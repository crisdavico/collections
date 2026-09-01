# Proposal: Sync Enabled Sellers from connector

## Intent

Enabled Sellers stays the only list vouchers, sheets, and the WhatsApp agent trust.
Administrators import that list from the company's connector (`list_sellers()` today)
instead of maintaining it by hand. `get_seller_id` then matches only among that list.

## Scope

### In Scope

- Collection Settings **Import** button (`base.group_system`) that fetches
  `connector.list_sellers()`, creates or matches internal users, upserts
  `collection.connector.seller.binding`, and **replaces** `enabled_seller_ids`.
- Fail closed: missing/inactive/misconfigured connector, duplicate source phone, or two
  source ids mapping to the same user → `UserError`, no partial write.
- `get_seller_id` filters to `env.company.enabled_seller_ids` (same generic miss
  message).
- TransactionCase coverage; bump `collection` to `19.0.1.19.0`.

### Out of Scope

- Bejerman connector, binding form UI, deleting/archiving users, changing `seller_id`
  off `res.users`.
- Nebula graph changes (`get_seller_id` only).
- New connector dispatch op (reuse `list_sellers()`).

## Capabilities

### New Capabilities

- None (Import is Collection Settings + connector list, not a new MCP tool).

### Modified Capabilities

- `collection-connectors`: Import replaces Enabled Sellers from the active connector.
- `seller-lookup`: `get_seller_id` matches only among the current company's enabled
  sellers.

## Approach

`res.company._sync_enabled_sellers_from_connector()`: require active connector, fetch
`list_sellers()`, resolve binding → unique AR phone → create internal user
(`collection.{company_id}.{external_seller_id}`, `no_reset_password`,
`base.group_user`), upsert bindings, `enabled_seller_ids = Command.set(...)`. Never
`sudo()`. Button on Collection Settings next to Enabled Sellers; hidden without a
connector.

## Affected Areas

| Area                                         | Impact   | Description                           |
| -------------------------------------------- | -------- | ------------------------------------- |
| `models/res_company.py`                      | Modified | Sync helper                           |
| `models/res_config_settings.py`              | Modified | Import action                         |
| `views/res_config_settings_views.xml`        | Modified | Import button                         |
| `tools/seller_lookup.py`                     | Modified | Filter by enabled list                |
| `tests/test_collection_seller_sync.py`       | New      | Create/match/bind/replace/fail-closed |
| `tests/test_collection_mcp_seller_lookup.py` | Modified | Invert unfiltered tests               |
| `tests/test_collection_ui.py`                | Modified | Button present, system-only, hidden   |
| `AGENTS.md`, `readme/DESCRIPTION.md`         | Modified | Docs + version                        |

## Risks

| Risk                                              | Likelihood | Mitigation                                         |
| ------------------------------------------------- | ---------- | -------------------------------------------------- |
| First Import drops manual extras (e.g. Vendedor)  | High       | Document; match-by-phone if SQLite has that number |
| Duplicate phones in source abort the whole list   | Med        | Fail closed; ops fix source                        |
| Creating users without `no_reset_password` emails | Low        | Always pass the context                            |

## Rollback Plan

Revert the collection module (and optional sqlite test). No schema migration. Clear the
connector to leave Enabled Sellers as last imported.

## Success Criteria

- [ ] Import creates/matches/binds and replaces Enabled Sellers from `list_sellers()`.
- [ ] Fail closed leaves the list unchanged; re-import is idempotent.
- [ ] `get_seller_id` requires enabled-list membership.
- [ ] `invoke test -m collection --mode=update` and scoped pre-commit pass.
