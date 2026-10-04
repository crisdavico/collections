# Delta for collection-connectors

## MODIFIED Requirements

### Requirement: Write path may create partners and bindings

`create_collection_allocation` (inline `payments[]`) MAY create `res.partner` records
and `collection.connector.customer.binding` rows through `resolve_customer_partner`. MCP
read tools `get_collection_allocation`, `list_collection_customers`, and `customer_debt`
MUST NOT create partners or bindings. (Previously: Only `create_collection_vouchers` MAY
lazy-create; reads listed were `list_collection_customers` and `customer_debt`.)

#### Scenario: Write path provisions on all-new create

- GIVEN an all-new MCP payment for an unbound listable identification
- WHEN `create_collection_allocation` runs
- THEN a partner and customer binding MAY be created
- AND `get_collection_allocation`, `list_collection_customers`, and `customer_debt` MUST
  still create neither

#### Scenario: Get unbound does not provision

- GIVEN an enabled seller and an unbound identification
- WHEN `get_collection_allocation` runs
- THEN MUST return `{allocation: null}`
- AND MUST NOT create a partner or binding
