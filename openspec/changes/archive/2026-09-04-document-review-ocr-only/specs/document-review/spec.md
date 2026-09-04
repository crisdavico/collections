# Delta for Document Review

## ADDED Requirements

### Requirement: Queue payload includes seller_changed_fields

The Document Review queue MUST include deterministic `seller_changed_fields` comparing
typed `ocr_*` to `seller_*`. Empty MUST be False, None, `""`, or monetary `0.0`. Both
empty MUST omit the field (no warning). Else MUST include the seller value (explicit
empty if seller emptied).

#### Scenario: Empty-empty omitted

- GIVEN an eligible voucher whose OCR and seller copies are both empty for a typed field
- WHEN the queue loads
- THEN that field MUST NOT appear in `seller_changed_fields`

#### Scenario: Seller value included including emptied

- GIVEN an eligible voucher whose seller copy differs from OCR, including seller emptied
- WHEN the queue loads
- THEN `seller_changed_fields` MUST include that field with the seller value
- AND emptied seller MUST be explicit empty, not omitted

## MODIFIED Requirements

### Requirement: OWL client loads real ORM data

The Document Review OWL client MUST load queue and voucher data via ORM (no mocks) from
`collection.voucher`. MUST support typed readonly `ocr_*` controls, queue navigation,
and advance to the next eligible record after a successful approve. Reject MUST NOT
exist. MUST NOT present editable current fields or input handlers. (Previously: Document
Review showed typed editable current fields.)

#### Scenario: Typed editable fields by document type

- GIVEN a queued `bank_transfer`, `check`, or `cash_deposit` voucher
- WHEN shown in Document Review
- THEN one readonly `ocr_*` control MUST appear per typed field: `ocr_document_type`,
  `ocr_amount`; bank transfer (`ocr_from_account`, `ocr_to_account`,
  `ocr_voucher_number`, `ocr_voucher_date`); check (`ocr_check_number`,
  `ocr_check_bank`, `ocr_check_type`, `ocr_check_issue_date`, `ocr_check_payment_date`);
  cash deposit (ocr amount/`ocr_document_type` only beyond shared)
- AND MUST NOT render editable current controls or input handlers

#### Scenario: Dual typed groups when seller changed document_type

- GIVEN a queued voucher whose OCR `document_type` differs from seller `document_type`
- WHEN shown in Document Review
- THEN MUST render both OCR-type and seller-type field groups

#### Scenario: Readonly context fields

- GIVEN a queued voucher
- WHEN shown in Document Review
- THEN voucher reference and queue position MUST be readonly and `document_id` MUST NOT
  be shown

#### Scenario: Navigate and next record after decision

- GIVEN more than one eligible queued voucher
- WHEN the reviewer navigates or successfully approves the current voucher
- THEN the client MUST move to the requested or next eligible record without mocks

### Requirement: Approve and reject without mocks

Approve MUST call a real server action (no mocks). Approve MUST NOT rewrite current.
Client MUST send empty vals or omit them; the server MUST ignore client vals. Snapshot
MUST still match current with `decision` `approved`. `state` MUST become
`validated_collections`. Reject MUST NOT exist (`action_review_reject` and OWL reject
MUST be removed). (Previously: Approve persisted field corrections onto current before
snapshot.)

#### Scenario: Correction persistence on approve

- GIVEN an eligible `validated_seller` voucher
- WHEN the reviewer approves with empty, omitted, or non-empty client vals
- THEN current MUST stay unchanged, the snapshot MUST match current with `decision`
  `approved`, and `state` MUST be `validated_collections`

#### Scenario: Reject invokes real action

- GIVEN an eligible `validated_seller` voucher
- WHEN reject is invoked
- THEN Reject MUST NOT exist and `state` MUST stay `validated_seller`

### Requirement: Three-way raw, seller, and current comparison

Payment Vouchers form MUST present raw OCR, seller-confirmed, and current side by side.
Current MUST remain the editable copy. Raw and seller-confirmed MUST be readonly.
Type-specific visibility MUST apply to all three form layers. Document Review MUST NOT
keep editable current or three side-by-side widgets. MUST show readonly `ocr_*` plus
inline seller-change warnings. MUST NOT show `document_id`. Empty provenance MUST still
load. (Previously: Document Review also presented three-way raw, seller, and editable
current side by side.)

#### Scenario: Type-specific visibility and hidden document_id

- GIVEN a `bank_transfer`, `check`, or `cash_deposit` voucher
- WHEN shown on the voucher form
- THEN type-specific fields MUST follow existing visibility on all three layers
- AND current MUST remain editable while raw and seller-confirmed MUST stay readonly

#### Scenario: Reviewer correction diverges current only

- GIVEN a voucher with stored raw and seller-confirmed copies
- WHEN an internal user edits current on the voucher form
- THEN current MUST persist the edit and raw and seller-confirmed MUST stay unchanged

#### Scenario: Document Review OCR-only with seller warnings

- GIVEN a queued voucher with stored provenance
- WHEN shown in Document Review
- THEN MUST show one readonly `ocr_*` control per field, MUST NOT show three
  side-by-side widgets, and MUST NOT show `document_id`
- AND fields in `seller_changed_fields` MUST warn inline with the seller value (emptied
  shown empty, not omitted)
- AND fields omitted from that map MUST NOT warn
