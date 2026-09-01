# Collection Connectors Specification (delta)

## MODIFIED Requirements

### Requirement: Import replaces Enabled Sellers

Administrators MUST be able to Import sellers from the company's active connector into
Collection Settings. Import MUST call `list_sellers()` (MUST NOT add a new dispatcher
op). For each _active_ connector seller, the system MUST reuse an existing binding, else
reuse a unique internal user with the same normalized AR phone, else create an internal
user (name + phone, `no_reset_password`, `base.group_user`, login
`collection.{company_id}.{external_seller_id}`). The system MUST upsert
`collection.connector.seller.binding` (`external_seller_id` 1:1 `user_id` per connector)
and MUST set `company_ids` to include this company. After a successful fetch,
`enabled_seller_ids` MUST be replaced (`Command.set`) with the imported users. Manual
extras MUST drop unless they appear in the source. Inactive external rows MUST be
omitted (same as `list_sellers()`). Users and old bindings MUST NOT be deleted when they
fall off the list. The Import button MUST be `base.group_system`, next to Enabled
Sellers, and MUST be invisible without a connector. Calls MUST NOT `sudo()`.

#### Scenario: Create match and bind then replace all

- GIVEN an active connector with two active sellers (one unbound, one whose phone
  matches an existing internal user) and one inactive external seller, and a manual
  extra on Enabled Sellers
- WHEN an administrator runs Import
- THEN the system MUST create or reuse users, upsert bindings, omit the inactive row,
  and replace Enabled Sellers with exactly the imported users

#### Scenario: Binding reuse on re-import

- GIVEN a prior Import created users and bindings
- WHEN Import runs again with the same source
- THEN the same `res.users` ids MUST be reused (idempotent)

#### Scenario: Fail closed leaves the list unchanged

- GIVEN no connector, or an inactive or misconfigured one, or a source with duplicate
  phones, or two source ids that resolve to the same user
- WHEN Import runs
- THEN the system MUST raise `UserError` and MUST NOT change `enabled_seller_ids` or
  create a partial user/binding set
