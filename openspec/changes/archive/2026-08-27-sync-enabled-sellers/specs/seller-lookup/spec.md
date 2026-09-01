# Seller Lookup Specification (delta)

## MODIFIED Requirements

### Requirement: Lookup matches only enabled sellers

`get_seller_id` MUST match only among `env.company.enabled_seller_ids`. Empty enabled
list or a unique internal phone that is not enabled MUST raise the same generic
`UserError` as zero matches (`No unique seller found for that mobile.`). Enabled lists
on other companies MUST NOT satisfy lookup for the current company. Fail-closed
uniqueness, internal-only matching, and caller authorization MUST remain unchanged.
`list_collection_sellers` MUST remain a connector preview and MUST NOT grant collect
permission.

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
