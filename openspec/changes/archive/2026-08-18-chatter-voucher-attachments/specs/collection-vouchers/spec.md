# Delta for collection-vouchers

## ADDED Requirements

### Requirement: Designated proof is message_main_attachment_id

Each voucher's designated proof MUST be `message_main_attachment_id`. MCP create MUST
post at most one nested proof per payment. Extra chatter files MAY exist after save.
MIME allow-list (`image/*` or PDF) MUST apply only when setting or replacing designated
proof and when validating MCP nests. Extra chatter files MUST NOT be restricted to that
allow-list. A non-image/non-PDF file MUST NOT become designated proof.

#### Scenario: MCP nest becomes designated proof

- GIVEN an all-new MCP payment with one valid nested image/PDF
- WHEN create completes
- THEN that file MUST be `message_main_attachment_id`
- AND MUST be visible on the voucher chatter

#### Scenario: Extra files do not steal proof

- GIVEN a voucher whose designated proof is already set
- WHEN an extra chatter file is attached
- THEN `message_main_attachment_id` MUST remain the prior proof

#### Scenario: Non-image extra cannot become proof

- GIVEN a voucher with empty designated proof
- WHEN a non-image/non-PDF chatter file is attached
- THEN `message_main_attachment_id` MUST remain empty

### Requirement: Pre-upgrade migration of Binary proofs

On upgrade to this change, each voucher that had a Binary field attachment MUST keep
that file as designated chatter proof, using the prior `attachment_filename` (or
`proof.bin` when empty). After upgrade, Binary `attachment` and `attachment_filename`
MUST NOT remain, and leftover `res_field=attachment` rows MUST NOT remain inaccessible.

#### Scenario: Binary field attachment migrates

- GIVEN a voucher with a Binary field attachment and `attachment_filename`
- WHEN this change is applied
- THEN that file MUST be the chatter designated proof
- AND `res_field` MUST NOT remain `attachment`

#### Scenario: Empty filename fallback

- GIVEN a Binary field attachment with empty `attachment_filename`
- WHEN this change is applied
- THEN designated proof `name` MUST be `proof.bin`

## MODIFIED Requirements

### Requirement: Optional image or PDF attachment per voucher

Each `collection.voucher` MAY store one optional designated proof as a chatter
`ir.attachment` (empty `res_field`, linked via `mail.message`). Omit/empty MUST remain
valid. Proof files MUST be `copy=False` and under existing internal-user voucher ACL.
Setting or replacing designated proof MUST validate base64 and detected MIME (`image/*`
or PDF only); MUST raise `UserError` otherwise.
(Previously: Proof was Binary `attachment=True` plus filename via `ir.attachment`.)

#### Scenario: Omit attachment valid

- GIVEN a voucher with no attachment
- WHEN saved
- THEN the voucher MUST persist

#### Scenario: Valid file persists

- GIVEN a saved voucher and a valid image/PDF proof
- WHEN the proof is posted on the voucher chatter
- THEN the file MUST persist as an `ir.attachment` on that thread
- AND MUST NOT persist as Binary field `attachment`

#### Scenario: Invalid content rejected

- GIVEN invalid base64 or non-image/non-PDF MIME
- WHEN a designated proof is set or replaced
- THEN MUST raise `UserError` and MUST NOT persist the file

### Requirement: Attachment widgets on Payment Vouchers views

Payment Vouchers form, list, and kanban MUST NOT include Binary attachment or filename
widgets. Form chatter MAY remain so internal users MAY attach after the voucher is
saved. Where a file picker applies to designated proof, browser accept MUST be limited
to `image/*` and PDF.
(Previously: Form, list, and kanban required Binary attachment and filename widgets.)

#### Scenario: Payment Vouchers views omit Binary widgets

- GIVEN Collections → Payment Vouchers
- WHEN an internal user opens form, list, or kanban
- THEN Binary attachment and filename widgets MUST NOT be present
- AND form chatter MUST remain available for attaching files after save

### Requirement: MCP optional payment attachment on create

`create_collection_vouchers` MAY accept one optional nested attachment per payment with
required `name`, `mimetype`, and base64 `datas` when present. Declared `mimetype` MUST
match content detection (`image/*` or PDF only); mismatch or bad base64 MUST raise
`UserError` with no writes. Create with attachments MUST persist all vouchers and files
atomically under a savepoint by posting each nest onto the new voucher chatter via
`message_post` (MUST NOT write Binary `attachment`). Exact-retry by `document_id` MUST
return all matching vouchers and MUST NOT add, replace, or compare attachments (even
when a voucher has none). All-new and conflict rules MUST remain unchanged.
(Previously: Nested files persisted as Binary `attachment` plus `attachment_filename`.)

#### Scenario: MCP create with nested attachment

- GIVEN unused `document_id`s and a payment with valid nested attachment
- WHEN `create_collection_vouchers` runs
- THEN vouchers and the nested file MUST persist atomically under a savepoint
- AND the file MUST appear on that voucher's chatter as designated proof

#### Scenario: MCP attachment MIME mismatch rejected

- GIVEN nested attachment with mismatched or non-image/non-PDF `mimetype`
- WHEN `create_collection_vouchers` runs
- THEN MUST raise `UserError` with no writes

#### Scenario: Exact-retry skips attachment writes

- GIVEN every submitted `document_id` already exists
- WHEN retried with or without nested attachments
- THEN all matching vouchers return unchanged; attachments MUST NOT be
  written/replaced/compared

### Requirement: Concurrent and stale review attempts

Approve and reject MUST refuse stale or concurrent attempts when the voucher is no
longer eligible (not `pending`, or designated proof (`message_main_attachment_id`) no
longer present) and MUST NOT corrupt review or voucher state.
(Previously: Eligibility failed when Binary attachment was no longer present.)

#### Scenario: Concurrent or stale review attempt

- GIVEN a voucher already decided or otherwise ineligible for review (not `pending`, or
  designated proof no longer present)
- WHEN approve or reject is attempted again
- THEN the system MUST refuse the action and MUST NOT alter terminal or decided state

### Requirement: Attachment replacement resets review to pending

Replacing a voucher's designated proof (a change of `message_main_attachment_id` to a
different attachment) MUST reset that voucher's `state` to `pending` and MUST clear
prior reviewer/time audit for a fresh review. Extra chatter files that do not change
`message_main_attachment_id` MUST NOT reset review, audit, or rotation. Clearing
designated proof MUST reset rotation to 0 and MUST NOT reopen a decided voucher.
Omit/empty and MIME validation rules remain unchanged.
(Previously: Replacement was a write of new Binary content.)

#### Scenario: Attachment replacement resets voucher state

- GIVEN a voucher previously `approved` or `rejected` with a designated proof
- WHEN `message_main_attachment_id` changes to a different valid proof
- THEN `state` MUST become `pending`
- AND prior reviewer/time audit MUST be cleared for re-review

#### Scenario: Extra chatter files do not reset review

- GIVEN a voucher with designated proof in `approved` or `rejected`
- WHEN an extra chatter file is added without changing `message_main_attachment_id`
- THEN `state` and reviewer/time audit MUST remain unchanged

#### Scenario: Clearing proof does not reopen

- GIVEN a voucher in `approved` or `rejected` with designated proof
- WHEN designated proof is cleared with no replacement
- THEN `state` MUST remain decided
- AND rotation MUST reset to 0
