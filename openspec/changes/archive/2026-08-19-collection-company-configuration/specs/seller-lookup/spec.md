# Delta for seller-lookup

## ADDED Requirements

### Requirement: Lookup ignores enabled sellers and company allow-lists

`get_seller_id` MUST resolve any unique internal user by mobile even when that user is
not on the current company's enabled-seller list, including when that list is empty. The
tool MUST NOT apply voucher or sheet company allow-lists as a lookup filter. Fail-
closed uniqueness, internal-only matching, and caller authorization MUST remain
unchanged.

#### Scenario: Unique match not on the enabled list still returns

- GIVEN an internal caller and exactly one internal user whose phone matches after
  AR/WhatsApp normalize, and that user is absent from the current company's enabled
  sellers
- WHEN `get_seller_id` runs with that mobile
- THEN the response MUST be `{ "seller_id": <that user’s positive id> }` only

#### Scenario: Empty enabled list does not block lookup

- GIVEN the current company has no enabled sellers and exactly one internal phone match
- WHEN `get_seller_id` runs with that mobile
- THEN the response MUST be that user’s `seller_id`

#### Scenario: Other-company enabled lists do not filter lookup

- GIVEN a unique internal phone match enabled only on another company
- WHEN `get_seller_id` runs
- THEN the response MUST still be that user’s `seller_id`
