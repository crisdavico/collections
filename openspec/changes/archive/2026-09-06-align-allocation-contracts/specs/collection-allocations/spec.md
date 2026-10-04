# Delta for collection-allocations

Align `create_collection_allocation` parse with Nebula
`CollectionAllocationRequest.model_dump(mode="json")`. Keep one customer, `request_id`
replay, draft writes, `balance_seen` revalidation, receipt persist, and
`{sheet_id, vouchers, allocation}`. `collection-receipts` is unchanged.

## ADDED Requirements

### Requirement: Strict nested-key parse of dump payloads

Runtime parse of `create_collection_allocation` MUST reject unknown keys at every nested
object (`extra=forbid`): request, each payment, `seller_confirmed`, `raw_ocr`,
`attachment`, each receipt, each value, and each application. It MUST reject keys that
do not belong to that payment’s `document_type` (type-owned fields only; see
collection-vouchers). Explicit JSON `null` on optional dump fields MUST be accepted as
omit. Omitted optional keys MUST remain valid. A forbidden key MUST raise `UserError`
with no writes.

#### Scenario: Unknown key on payment or request rejected

- GIVEN a valid dump plus an extra key on the request or a payment object
- WHEN `create_collection_allocation` runs
- THEN MUST raise `UserError` with no writes

#### Scenario: Unknown key on nested receipt objects rejected

- GIVEN a valid dump plus an extra key on a receipt, value, application,
  `seller_confirmed`, `raw_ocr`, or `attachment`
- WHEN `create_collection_allocation` runs
- THEN MUST raise `UserError` with no writes

#### Scenario: Type-foreign nest fields rejected

- GIVEN `seller_confirmed.document_type` `bank_transfer` with `check_number` set (or any
  type-foreign field for that discriminator)
- WHEN `create_collection_allocation` runs
- THEN MUST raise `UserError` with no writes

#### Scenario: Explicit nulls accepted as omit

- GIVEN a dump whose unused typed nest fields, `attachment`, `raw_ocr`, and application
  `number` are JSON `null`
- WHEN `create_collection_allocation` runs with otherwise valid data
- THEN parse MUST treat those nulls as omit and MAY persist

## MODIFIED Requirements

### Requirement: MCP create_collection_allocation

MUST expose MCP write `create_collection_allocation` for Enabled Seller internal callers
(`category=write`, `registry=mcp`, method-discovered; MUST NOT add a `muk_mcp.tool`
row). Input MUST be:

| Key                     | Rule                                                                                                                                                                                                                                                                     |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| seller_id               | int > 0                                                                                                                                                                                                                                                                  |
| customer_identification | stripped string; top-level only; MUST NOT on payment items                                                                                                                                                                                                               |
| request_id              | required                                                                                                                                                                                                                                                                 |
| payments[]              | minItems 1; each item requires `document_id` and `seller_confirmed`; optional `raw_ocr` and `attachment`; voucher fields MUST come from `seller_confirmed`; `seller_confirmed.document_type` MUST be one of the seven catalog codes; amount MUST accept a decimal string |
| receipts[]              | REQUIRED; minItems 1; each item requires `document_kind` and `values[]`; `applications[]` MAY be empty (on account); amounts MUST accept decimal strings                                                                                                                 |

MUST NOT accept `invoices`, `splits`, `total_debt`, or `residual_reason`. Unknown keys
at any nested level MUST be rejected (see Strict nested-key parse).

`seller_confirmed.document_type` `unsupported` MUST raise `UserError` with no writes.
The six dump types `bank_transfer`, `check`, `echeck`, `cash_deposit`,
`retention_certificate`, and `cash` MUST persist when otherwise valid. Seller-declared
`cash` MUST persist with `attachment` and `raw_ocr` omitted or null.

Success output MUST be exactly `{sheet_id, vouchers, allocation}`: `vouchers[]` one
`{id,name,state,document_id}` row per submitted payment IN SEND ORDER; `allocation`
exactly seven keys `{id,name,state,revision,total_vouchers,total_applied,residual}` with
`revision` a JSON int (MUST NOT be bool, float, or str). Persist `draft` revision-1;
`UNIQUE(sheet_id, partner_id)`. Unbound identification MUST lazy-resolve via
`resolve_customer_partner` on this write. When `company.auto_create_sheet` is False,
MUST raise a named `UserError` and write zero rows. Exact same-company `document_id` set
MUST reuse rows and continue to allocation (MUST NOT voucher-style early-return).
Partial overlap or other-company hit MUST raise generic conflict with no writes.
Revalidation failure MUST roll back vouchers and allocation. Errors MUST be raised,
NEVER `{"error":...}` bodies. MUST NOT `sudo()`. (Previously: Four-type
`seller_confirmed`; amounts advertised as numbers only; `unsupported` reject was not
stated on this requirement; extra nested keys were ignored on payment objects.)

#### Scenario: First create

- GIVEN valid enabled-seller payload with inline `payments` and required `receipts`
  (`applications` MAY be `[]`)
- WHEN create with a new `request_id`
- THEN `draft`, `revision` 1 (int), matching totals, `sheet_id`, and `vouchers[]` in
  send order
- AND a second header for same (sheet, partner) MUST be unique-rejected

#### Scenario: Authorization denied

- GIVEN a non-internal or non-enabled seller
- WHEN the tool runs
- THEN the call MUST fail with no writes

#### Scenario: Response shape freeze

- GIVEN a successful create or `request_id` replay
- WHEN the body is inspected
- THEN top-level keys MUST be exactly `sheet_id`, `vouchers`, `allocation`
- AND `allocation` MUST have exactly those seven keys with int `revision`

#### Scenario: Exact document_id reuse continues

- GIVEN every submitted `document_id` already exists in the same company
- WHEN `create_collection_allocation` runs with a new `request_id`
- THEN those voucher rows MUST be reused and allocation MUST still persist
- AND MUST NOT return a voucher-only payload

#### Scenario: Partial overlap or other-company conflict

- GIVEN a partial same-company `document_id` overlap, or a hit only in another company
- WHEN `create_collection_allocation` runs
- THEN MUST raise generic conflict with no writes and no ids disclosed

#### Scenario: Revalidation rolls back vouchers

- GIVEN inline payments that would create vouchers and receipts that fail ERP
  revalidation
- WHEN create runs
- THEN MUST raise and MUST write zero vouchers and zero allocation

#### Scenario: Unsupported payment write rejected

- GIVEN a payment whose `seller_confirmed.document_type` is `unsupported`
- WHEN `create_collection_allocation` runs
- THEN MUST raise `UserError`
- AND MUST write zero vouchers, receipts, and allocations

#### Scenario: Six dump types persist with decimal-string amounts

- GIVEN a valid one-customer dump for `bank_transfer`, `check`, `echeck`,
  `cash_deposit`, `retention_certificate`, or `cash` whose amounts are decimal strings
- WHEN create runs with a new `request_id`
- THEN allocation MUST persist `draft` with response `{sheet_id, vouchers, allocation}`
- AND `cash` MAY omit proof; the other five MAY include valid proof

### Requirement: MCP receipts payload

`create_collection_allocation` MUST include `receipts[]` (`minItems` 1). Each receipt
MUST have unique `document_kind` (`invoice` or `quotation`), required `values[]`
(`minItems` 1; `{document_id, amount}` amount > 0), and `applications[]` that MAY be
empty (on account). A payment MAY appear on both kinds. Sum of value amounts per payment
across receipts MUST equal that payment's `seller_confirmed` amount. Applied total per
receipt MUST NOT exceed funded values. Unknown `document_id` or duplicate kind /
duplicate payment+kind / duplicate `external_document_id` MUST raise with no writes.
Value `amount`, application `balance_seen`, and `amount_applied` MUST accept decimal
strings (and MAY accept numbers). Application `number` MAY be JSON `null` (omit).
(Previously: Amounts were not required to accept decimal strings; `number` null was not
named.)

#### Scenario: Split one voucher two kinds

- GIVEN a valid create payload with one payment amount 100 and receipt values 40 invoice
  plus 60 quotation
- WHEN create succeeds
- THEN both values MUST persist on the matching receipts

#### Scenario: Empty applications is on account

- GIVEN a valid create with one invoice receipt, full values, and `applications: []`
- WHEN create succeeds
- THEN the invoice receipt MUST persist with those values
- AND allocation lines MUST expand outstanding ERP invoices at applied 0

#### Scenario: Over-split refused

- GIVEN a payment amount 50 and receipt values summing to 51
- WHEN create runs
- THEN MUST raise with no allocation persist

#### Scenario: Decimal-string receipt amounts persist

- GIVEN receipt values and applications whose `amount`, `balance_seen`, and
  `amount_applied` are decimal strings matching fresh ERP `balance_seen`
- WHEN create succeeds
- THEN those receipts and applications MUST persist
- AND `balance_seen` revalidation MUST still use `currency.compare_amounts`
