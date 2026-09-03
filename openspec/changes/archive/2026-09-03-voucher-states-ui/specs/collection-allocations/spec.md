# Delta for collection-allocations

## MODIFIED Requirements

### Requirement: Input and sheet gates

Vouchers MUST be caller-company, amount > 0, one partner, one caller seller, one sheet. All three voucher states (`draft`, `validated_seller`, `validated_collections`) MAY allocate. MUST NOT refuse a voucher because it is not `rejected` (that state MUST NOT exist). Those single-customer and single-sheet gates MUST remain and MUST be reachable via `document_id` reuse. Customer MUST resolve via `resolve_customer_partner` on this write (MAY create partner/binding); MUST match voucher partner after resolve. Sheet MUST be `open` and same company. Successful persist MUST leave the allocation `draft` on that open sheet. When `auto_create_sheet` is False, MUST raise a named `UserError` (company requires a sheet chosen in Odoo) with zero writes.
(Previously: Vouchers MUST be not `rejected`.)

#### Scenario: Ineligible input rejected

- GIVEN amount null/≤0, other company, other sheet, mixed partner/seller/sheet via reused `document_id`, partner mismatch after resolve, closed sheet, or other company sheet
- WHEN allocated
- THEN MUST error
- AND mixed-reuse and mismatch MUST NOT create a partner or binding

#### Scenario: All voucher states may allocate

- GIVEN a caller-company voucher in `draft`, `validated_seller`, or `validated_collections` with amount > 0
- WHEN allocated
- THEN voucher state MUST NOT by itself refuse the allocation

#### Scenario: Unbound write lazy-creates partner

- GIVEN an unbound listable identification and `auto_create_sheet` ON
- WHEN `create_collection_allocation` runs
- THEN a partner and customer binding MAY be created
- AND vouchers MUST share that partner

#### Scenario: auto_create_sheet off fail-closed

- GIVEN `company.auto_create_sheet` is False
- WHEN `create_collection_allocation` runs
- THEN MUST raise a named `UserError`
- AND MUST write zero vouchers, sheets, and allocations
