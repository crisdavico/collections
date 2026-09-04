# Delta for Document Review

## MODIFIED Requirements

### Requirement: OWL client loads real ORM data

The Document Review OWL client MUST load queue and voucher data via ORM (no mocks) from
`collection.voucher`. MUST support one typed editable control per field, prefilled from
OCR with current fallback, queue navigation, and advance to the next eligible record
after a successful approve. Reject MUST NOT exist. MUST NOT present a second OCR or
seller widget per field. (Previously: Document Review showed readonly `ocr_*` plus
inline seller-change warnings.)

#### Scenario: Typed editable fields by document type

- GIVEN a queued `bank_transfer`, `check`, or `cash_deposit` voucher
- WHEN shown in Document Review
- THEN one editable control MUST appear per typed field: `document_type`, `amount`; bank
  transfer (`from_account`, `to_account`, `voucher_number`, `voucher_date`); check
  (`check_number`, `check_bank`, `check_type`, `check_issue_date`,
  `check_payment_date`); cash deposit (amount/`document_type` only beyond shared)
- AND that control MUST be prefilled from non-empty `ocr_*`, else current
- AND MUST NOT render a second OCR or seller control for the same field

#### Scenario: Typed groups follow the editable document type

- GIVEN a queued voucher whose draft `document_type` is `bank_transfer` or `check`
- WHEN the reviewer changes draft `document_type`
- THEN MUST show the field group for the draft type only

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

Approve MUST call a real server action (no mocks). Approve MUST persist sanitized client
vals onto current `_REVIEW_EDITABLE_FIELDS` only, then snapshot those current values
with `decision` `approved`. `state` MUST become `validated_collections`. Empty or
omitted vals MUST leave current unchanged. `ocr_*`, `seller_*`, `document_id`,
attachment bytes, and rotation MUST NOT be rewritten from client vals. Reject MUST NOT
exist (`action_review_reject` and OWL reject MUST be removed). (Previously: Approve
ignored client vals and did not rewrite current.)

#### Scenario: Correction persistence on approve

- GIVEN an eligible `validated_seller` voucher
- WHEN the reviewer approves with non-empty current-field client vals
- THEN current MUST persist those edits, the snapshot MUST match the corrected current
  with `decision` `approved`, and `state` MUST be `validated_collections`
- AND `ocr_*` and `seller_*` MUST stay unchanged

#### Scenario: Empty or omitted vals leave current

- GIVEN an eligible `validated_seller` voucher
- WHEN the reviewer approves with empty or omitted vals
- THEN current MUST stay unchanged, the snapshot MUST match current with `decision`
  `approved`, and `state` MUST be `validated_collections`

#### Scenario: Reject invokes real action

- GIVEN an eligible `validated_seller` voucher
- WHEN reject is invoked
- THEN Reject MUST NOT exist and `state` MUST stay `validated_seller`

### Requirement: Three-way raw, seller, and current comparison

Payment Vouchers form MUST present raw OCR, seller-confirmed, and current side by side.
Current MUST remain the editable copy. Raw and seller-confirmed MUST be readonly.
Type-specific visibility MUST apply to all three form layers. Document Review MUST show
one editable current control per field (OCR-prefilled) and MUST NOT show three
side-by-side widgets or inline seller-change warnings. MUST NOT show `document_id`.
Empty provenance MUST still load. (Previously: Document Review showed readonly `ocr_*`
plus inline seller-change warnings.)

#### Scenario: Type-specific visibility and hidden document_id

- GIVEN a `bank_transfer`, `check`, or `cash_deposit` voucher
- WHEN shown on the voucher form
- THEN type-specific fields MUST follow existing visibility on all three layers
- AND current MUST remain editable while raw and seller-confirmed MUST stay readonly

#### Scenario: Reviewer correction diverges current only

- GIVEN a voucher with stored raw and seller-confirmed copies
- WHEN an internal user edits current on the voucher form
- THEN current MUST persist the edit and raw and seller-confirmed MUST stay unchanged

#### Scenario: Document Review one editable OCR-prefilled control

- GIVEN a queued voucher with stored provenance
- WHEN shown in Document Review
- THEN MUST show one editable control per field bound to the OCR-prefilled draft
- AND MUST NOT show three side-by-side widgets, seller-warning lines, or `document_id`
