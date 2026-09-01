# Design: Sync Enabled Sellers from connector

## Technical Approach

Treat `enabled_seller_ids` as the source of truth. Import is a company-scoped write that
reuses `collection.connector.list_sellers()` (no new dispatch op). `get_seller_id`
intersects unique AR-phone matches with `env.company.enabled_seller_ids`. Never
`sudo()`.

## Architecture Decisions

| Decision         | Options                              | Tradeoff                         | Choice                                                    |
| ---------------- | ------------------------------------ | -------------------------------- | --------------------------------------------------------- |
| Sync owner       | `res.company` vs connector vs wizard | Company owns Enabled Sellers     | `_sync_enabled_sellers_from_connector()` on `res.company` |
| Match order      | Binding, phone, create               | Login reuse is extra             | Binding → unique phone → create                           |
| Replace vs merge | `Command.set` vs link extras         | Manual extras (Vendedor) drop    | Replace all after successful fetch                        |
| Dropped sellers  | Delete users vs keep                 | Vouchers still point at them     | Keep users and old bindings                               |
| Lookup filter    | All internals vs enabled list        | Agent must not collect as extras | Filter to `enabled_seller_ids`                            |
| Phone helper     | Duplicate vs mixin                   | One normalize                    | Reuse `_collection_normalize_ar_mobile`                   |

Rejected: new `_dispatch` op; `sudo()`; deleting users; picking first on duplicate
phone.

## Data Flow

```
Collection Settings Import
  → require active collection_connector_id
  → payload = connector.list_sellers()   # inactive rows already omitted
  → validate unique external id + unique normalized phone
  → for each row: binding else unique phone else create user
  → abort if two rows resolve to the same user
  → upsert bindings; company_ids includes this company
  → enabled_seller_ids = Command.set(imported ids)
```

Fail closed before any write when the connector is missing/inactive/misconfigured or the
source is internally inconsistent.

## File Changes

| File                                         | Action | Description                                |
| -------------------------------------------- | ------ | ------------------------------------------ |
| `models/res_company.py`                      | Modify | `_sync_enabled_sellers_from_connector`     |
| `models/res_config_settings.py`              | Modify | `action_import_enabled_sellers`            |
| `views/res_config_settings_views.xml`        | Modify | Import button                              |
| `tools/seller_lookup.py`                     | Modify | Enabled-list filter                        |
| `tests/common_connector.py`                  | Modify | Optional `collection_test_sellers` context |
| `tests/test_collection_seller_sync.py`       | Create | Sync TransactionCase                       |
| `tests/test_collection_mcp_seller_lookup.py` | Modify | Invert three unfiltered tests              |
| `tests/test_collection_ui.py`                | Modify | Button arch                                |
| `__manifest__.py`                            | Modify | `19.0.1.19.0`                              |
| `AGENTS.md`, `readme/DESCRIPTION.md`         | Modify | Domain + MCP                               |

Optional sqlite: Import via sample connector creates 5 users and replaces the list.

## Interfaces / Contracts

New-user login: `collection.{company_id}.{external_seller_id}` (globally unique, no
email blast). Groups: `base.group_user`. Context: `no_reset_password`.

Generic miss for `get_seller_id` stays `No unique seller found for that mobile.` Empty
enabled list and unique-but-not-enabled use that same `UserError`.

## Testing Strategy

Strict TDD. `invoke test -m collection --mode=update`.

| Layer | What                                                                                                                                                           | Approach                           |
| ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| Unit  | Create / phone-match / binding reuse; replace-all; inactive omitted; missing connector; duplicate phone; two ids → one user; idempotent re-import; no `.sudo(` | `TransactionCase` + test connector |
| UI    | Button present, `base.group_system`, `invisible` without connector                                                                                             | View arch                          |
| MCP   | Enabled-list membership                                                                                                                                        | Invert three lookup tests          |

## Migration / Rollout

No schema migration. Module upgrade reloads Python/XML. First Import replaces whatever
is currently on Enabled Sellers.

## Open Questions

None.
