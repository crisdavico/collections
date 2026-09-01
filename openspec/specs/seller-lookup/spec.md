# Seller Lookup Specification

## Purpose

Read-only MCP lookup of an internal seller id from the seller’s own mobile.

## Requirements

### Requirement: Read-only MCP tool get_seller_id

The system MUST expose `get_seller_id` via `@mcp_tool` on `muk_mcp.mixin`
(`category=read`, `registry=mcp`), method-discovered; MUST NOT add a DB tool record.
Calls MUST use the authenticated user and MUST NOT `sudo()`. Input MUST require string
`mobile`. Unique success MUST return exactly `{ "seller_id": <positive int> }` with no
extra PII unless a later spec adds `name`. This tool MUST NOT create or update vouchers,
MUST NOT fill invoke context, and MUST NOT replace connector `seller_id` on
`create_collection_vouchers`.

#### Scenario: Unique internal match returns seller_id only

- GIVEN an internal caller and exactly one enabled internal user whose phone matches
  after AR/WhatsApp normalize
- WHEN `get_seller_id` runs with that mobile
- THEN the response MUST be `{ "seller_id": <that user’s positive id> }` only
- AND vouchers, invoke context, and write-MCP connector `seller_id` MUST stay unchanged

### Requirement: Caller authorization

Portal and public callers MUST receive `AccessError`. Internal users (`base.group_user`)
MUST be allowed to invoke the tool.

#### Scenario: Portal or public caller denied

- GIVEN a portal or public caller
- WHEN `get_seller_id` runs with any mobile
- THEN the system MUST raise `AccessError` and MUST NOT return a `seller_id`

### Requirement: Fail closed on empty or invalid mobile

Empty, whitespace-only, or invalid `mobile` (no usable digits after AR/WhatsApp
normalize) MUST raise `UserError` and MUST NOT return a `seller_id`.

#### Scenario: Empty whitespace or invalid mobile rejected

- GIVEN an internal caller
- WHEN `get_seller_id` runs with empty, whitespace-only, or invalid `mobile`
- THEN the system MUST raise `UserError` and MUST NOT return a `seller_id`

### Requirement: Phone-only AR WhatsApp identity

Match MUST use `res.users.phone` / `partner_id.phone` only. MUST NOT require partner
`mobile` (absent in Odoo 19) or `hr.employee.mobile_phone`. AR WhatsApp variants
(`+54 9 …`, `549…`, local 10 digits, spaces/punctuation) MUST be one identity after
normalize (strip `+`, spaces/punctuation, `54`, then one leading `9`).

#### Scenario: AR variants match one seller

- GIVEN one internal user stored as `+54 9 11 1234-5678`
- WHEN `get_seller_id` runs with `5491112345678` or local 10-digit `1112345678`
- THEN the response MUST be that user’s `seller_id`

#### Scenario: Employee mobile_phone is not a match field

- GIVEN an internal user whose employee `mobile_phone` matches but `phone` does not
- WHEN `get_seller_id` runs with that number
- THEN the system MUST raise `UserError`

### Requirement: Unique internal match or fail closed

Only internal users MUST count after normalize. Portal/share users with the same digits
MUST NOT count or be returned. Zero or many internal matches MUST raise `UserError`
(MUST NOT pick first). A unique hit MUST then pass the write-path seller bar (exists,
not share, `base.group_user`); otherwise `UserError`.

#### Scenario: Zero matches fail closed

- GIVEN no internal user whose phone matches after normalize
- WHEN `get_seller_id` runs
- THEN the system MUST raise `UserError` and MUST NOT return a `seller_id`

#### Scenario: Many internal matches fail closed

- GIVEN two internal users whose phones normalize to the same identity
- WHEN `get_seller_id` runs with that mobile
- THEN the system MUST raise `UserError` and MUST NOT pick the first user

#### Scenario: Portal share digits excluded

- GIVEN a portal or share user with the same normalized digits as exactly one internal
  seller
- WHEN `get_seller_id` runs with that mobile
- THEN the response MUST be the internal seller’s `seller_id`
- AND the portal/share user MUST NOT be returned

#### Scenario: Portal-only digits fail closed

- GIVEN only a portal or share user has that normalized phone
- WHEN `get_seller_id` runs
- THEN the system MUST raise `UserError` and MUST NOT return that user’s id

#### Scenario: Unique hit fails seller bar

- GIVEN a unique phone match that does not exist, is share, or lacks `base.group_user`
- WHEN `get_seller_id` runs
- THEN the system MUST raise `UserError`

### Requirement: Lookup matches only enabled sellers

`get_seller_id` MUST match only among `env.company.enabled_seller_ids`. Empty enabled
list or a unique internal phone that is not enabled MUST raise the same generic
`UserError` as zero matches (`No unique seller found for that mobile.`). Enabled lists
on other companies MUST NOT satisfy lookup for the current company. Fail-closed
uniqueness, internal-only matching, and caller authorization MUST remain unchanged.
Connector `list_sellers()` MUST NOT grant collect permission.

#### Scenario: Unique match not on the enabled list fails closed

- GIVEN an internal caller and exactly one internal user whose phone matches after
  AR/WhatsApp normalize, and that user is absent from the current company's enabled
  sellers
- WHEN `get_seller_id` runs with that mobile
- THEN the system MUST raise `UserError` and MUST NOT return a `seller_id`

#### Scenario: Empty enabled list blocks lookup

- GIVEN the current company has no enabled sellers and exactly one internal phone match
- WHEN `get_seller_id` runs with that mobile
- THEN the system MUST raise `UserError` and MUST NOT return a `seller_id`

#### Scenario: Other-company enabled lists do not satisfy lookup

- GIVEN a unique internal phone match enabled only on another company
- WHEN `get_seller_id` runs
- THEN the system MUST raise `UserError` and MUST NOT return a `seller_id`

#### Scenario: Unique match on the enabled list returns seller_id

- GIVEN the matching internal user is on `env.company.enabled_seller_ids`
- WHEN `get_seller_id` runs with that mobile
- THEN the response MUST be `{ "seller_id": <that user’s positive id> }` only
