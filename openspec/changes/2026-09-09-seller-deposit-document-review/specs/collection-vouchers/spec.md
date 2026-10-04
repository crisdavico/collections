# Delta for Collection Vouchers

## MODIFIED Requirements

### Requirement: MCP write create_seller_deposit

The system MUST expose `create_seller_deposit` via `@mcp_tool` on `muk_mcp.mixin`
(`category=write`, `registry=mcp`), method-discovered; MUST NOT add a DB tool record.
Calls MUST use the authenticated user and MUST NOT `sudo()`. Input MUST require integer
`seller_id`, amount, `voucher_number`, `voucher_date`, and MAY accept nested
`attachment`. The tool MUST NOT accept `customer_identification` or `sheet_id` from the
caller. It MUST resolve the seller's own `submitted` sheet, stamp the sentinel partner
and `document_type` `seller_deposit`, stamp `validated_seller`, pass that `sheet_id`
explicitly, and require new-work for that seller and `seller_deposit`. The tool MUST NOT
write `validated_collections`: the deposit slip is a reviewable designated proof, so the
voucher MUST stay `validated_seller` and MUST reach `validated_collections` only through
Document Review Approve. A deposit carrying designated proof MUST appear in
`get_review_queue` for its sheet. Portal or public callers MUST receive `AccessError`.
Errors MUST be raised, never `{"error":...}`. Zero or more than one `submitted` sheet
MUST raise `UserError`. `create_collection_allocation` MUST remain customer-required and
`open`-sheet-only. (Previously: the tool wrote `validated_collections` under
`collection_audited_state` right after create, so the slip never reached the review
queue. Before that: No MCP path could create a no-customer remittance voucher.)

#### Scenario: Internal seller creates a deposit on submitted

- GIVEN an internal caller and an internal seller with exactly one `submitted` sheet
- WHEN `create_seller_deposit` runs with amount, number, date, and optional proof
- THEN one `seller_deposit` voucher MUST persist on that sheet
- AND `partner_id` MUST be the sentinel
- AND `state` MUST be `validated_seller`
- AND no `sudo()` MUST occur

#### Scenario: Deposit slip enters the review queue

- GIVEN a `create_seller_deposit` call carrying a nested `attachment`
- WHEN `get_review_queue` runs for that sheet
- THEN the deposit MUST be listed
- AND its `state` MUST still be `validated_seller`

#### Scenario: Review Approve promotes the deposit

- GIVEN a queued `seller_deposit` with designated proof
- WHEN Document Review Approve runs
- THEN `state` MUST become `validated_collections`
- AND cash replacement MUST run per Collection Receipts

#### Scenario: Open sheet is not the deposit target

- GIVEN an internal seller with one `open` sheet and zero `submitted` sheets
- WHEN `create_seller_deposit` runs
- THEN MUST raise `UserError`
- AND no voucher MUST persist

#### Scenario: Disabled type refused

- GIVEN `seller_deposit` is not allowed for the company
- WHEN `create_seller_deposit` runs
- THEN MUST raise `UserError` with no write

#### Scenario: Non-internal deposit refused

- GIVEN a portal or public caller
- WHEN `create_seller_deposit` runs
- THEN MUST raise `AccessError`
- AND no voucher MUST persist

#### Scenario: Allocation write still requires a customer

- GIVEN `create_collection_allocation` with `document_type` `seller_deposit` or omitted
  customer identification
- WHEN the call runs
- THEN MUST refuse
- AND MUST NOT persist a remittance voucher
