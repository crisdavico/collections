# Delta for Document Review

## ADDED Requirements

### Requirement: Three-way raw, seller, and current comparison

Payment Vouchers form and Document Review MUST present raw OCR, seller-confirmed, and
current payment fields side by side. Current MUST remain the editable copy. Raw and
seller-confirmed MUST be readonly. Type-specific visibility MUST apply to all three
layers. Document Review MUST NOT show `document_id`. Empty provenance MUST still load.

#### Scenario: Type-specific visibility and hidden document_id

- GIVEN a queued `bank_transfer`, `check`, or `cash_deposit` voucher
- WHEN shown in Document Review or on the voucher form
- THEN type-specific fields MUST follow existing visibility on all three layers
- AND Document Review MUST NOT show `document_id`

#### Scenario: Reviewer correction diverges current only

- GIVEN an eligible pending voucher with stored raw and seller-confirmed copies
- WHEN the reviewer edits current fields and Document Review approve completes
- THEN current MUST persist the correction
- AND raw and seller-confirmed MUST remain unchanged
- AND the appended snapshot MUST match current

### Requirement: Queue payload includes readonly provenance

The Document Review queue MUST include readonly raw and seller-confirmed payment fields
for each eligible voucher. Missing provenance MUST be represented as empty, not
fabricated.

#### Scenario: Queue exposes provenance without fabricating

- GIVEN eligible vouchers with and without stored provenance
- WHEN the queue loads
- THEN each item MUST include readonly raw and seller-confirmed copies
- AND empty provenance MUST remain empty

### Requirement: Document Review decisions append immutable snapshots

Document Review approve MUST append a snapshot of the typed current payment fields even
when those fields are unchanged. Document Review reject MUST also append a snapshot.
Each snapshot MUST record revision, reviewer, time, and decision. Form Approve and
Reject MUST NOT satisfy this requirement.

#### Scenario: Unchanged Document Review approval still snapshots

- GIVEN an eligible pending voucher with unchanged current fields
- WHEN the reviewer approves in Document Review
- THEN a snapshot MUST be appended
- AND it MUST match the current payment fields

#### Scenario: Document Review reject also snapshots

- GIVEN an eligible pending voucher
- WHEN the reviewer rejects in Document Review
- THEN a snapshot MUST be appended
- AND voucher state MUST become `rejected`

### Requirement: Repeated Document Review appends another revision

After a decided voucher is reopened to `pending`, a later Document Review approve or
reject MUST append a new snapshot. Earlier snapshots MUST remain unchanged.

#### Scenario: Reopen then re-review appends another revision

- GIVEN a voucher with an existing snapshot that is `pending` again after reopen
- WHEN Document Review approve or reject runs
- THEN a new snapshot revision MUST be appended
- AND earlier snapshots MUST remain unchanged

### Requirement: Voucher review history is visible

Payment Vouchers form MUST show the voucher's Document Review snapshot history in
revision order. History rows MUST be readonly.

#### Scenario: History list on the voucher form

- GIVEN a voucher with one or more snapshots
- WHEN an internal user opens the Payment Vouchers form
- THEN the history MUST list those snapshots in revision order
- AND the rows MUST be readonly
