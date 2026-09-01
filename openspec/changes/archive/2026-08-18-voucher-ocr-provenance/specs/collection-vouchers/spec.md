# Delta for collection-vouchers

## ADDED Requirements

### Requirement: Typed provenance copies of payment fields

Each voucher MUST persist typed raw-OCR and seller-confirmed copies of the payment
review field set. Current columns MUST remain the editable copy. Provenance MUST NOT
include `document_id`, `customer_identification`, `seller_id`, attachment, or base64,
and MUST NOT copy with the voucher. Cash-deposit MAY store `voucher_number` and
`voucher_date` in all three layers even when UI hides them. Voucher write MUST reject
provenance keys after create.

#### Scenario: Identity and proof stay outside provenance

- GIVEN an all-new MCP payment with `document_id`, customer, seller, and attachment
- WHEN create completes
- THEN provenance MUST contain only payment review fields
- AND MUST NOT contain `document_id`, customer, seller, attachment, or base64

#### Scenario: Cash-deposit extra keys stored in all layers

- GIVEN a cash-deposit payment whose nests include `voucher_number` and `voucher_date`
- WHEN all-new create completes
- THEN they MUST persist in all three layers
- AND UI MAY hide them for `cash_deposit`

#### Scenario: Voucher write rejects provenance keys

- GIVEN an existing voucher
- WHEN write includes raw or seller-confirmed field keys
- THEN the write MUST be rejected
- AND stored provenance MUST remain unchanged

### Requirement: MCP nested provenance on all-new create

`create_collection_vouchers` MAY accept nested `raw_ocr` and `seller_confirmed` with the
same typed keys as current fields. When both nests are present, seller-confirmed MUST
equal top-level fields; current MUST initialize from seller-confirmed; raw MUST persist
as submitted. Omitting both nests MUST leave empty provenance; UI/ORM create MUST remain
allowed. Malformed, one-sided, or mismatched nests MUST fail the batch with no writes.
Exact replay MUST ignore those nests with no provenance mutation.

#### Scenario: Unchanged seller confirmation

- GIVEN unused `document_id`s and both nests equal to top-level payment fields
- WHEN all-new create runs
- THEN raw, seller-confirmed, and current MUST be equal

#### Scenario: Seller correction

- GIVEN raw nest differs from seller-confirmed, and seller-confirmed equals top-level
- WHEN all-new create runs
- THEN raw MUST persist unchanged
- AND seller-confirmed and current MUST contain the correction

#### Scenario: Both nests omitted leave empty provenance

- GIVEN UI or MCP create with neither `raw_ocr` nor `seller_confirmed`
- WHEN create completes
- THEN raw and seller-confirmed MUST be empty
- AND current payment fields MUST persist as submitted

#### Scenario: Bad provenance fails the batch

- GIVEN a payment with one-sided, malformed, or mismatched nests
- WHEN `create_collection_vouchers` runs
- THEN the call MUST fail with no writes

#### Scenario: Exact replay ignores provenance nests

- GIVEN every submitted `document_id` already exists, with or without stored provenance
- WHEN retried with different or omitted nests
- THEN matching vouchers MUST return unchanged
- AND provenance and snapshots MUST NOT be written, backfilled, or mutated

### Requirement: Immutable review snapshots and ACL

The system MUST store immutable Document Review snapshots (revision, reviewer, time,
decision, and current payment fields). Internal users MUST read history and MUST NOT
write or unlink snapshots, add groups, record rules, or sudo. Form Approve and Reject
MUST NOT append snapshots.

#### Scenario: Internal users read history without client mutation

- GIVEN an internal user and existing snapshots
- WHEN they read voucher history
- THEN ACL MUST allow read
- AND client write or unlink of snapshots MUST be denied

#### Scenario: Form Approve and Reject do not snapshot

- GIVEN a pending voucher on Payment Vouchers
- WHEN form Approve or Reject runs
- THEN voucher state MUST change as today
- AND no snapshot MUST be appended

### Requirement: Additive upgrade without provenance backfill

Upgrade MUST add nullable provenance with no backfill or fabricated snapshots.

#### Scenario: Existing rows keep current and empty provenance

- GIVEN vouchers created before this change
- WHEN the upgrade is applied
- THEN current payment fields MUST remain
- AND raw and seller-confirmed MUST be empty
- AND those vouchers MUST have no snapshots
