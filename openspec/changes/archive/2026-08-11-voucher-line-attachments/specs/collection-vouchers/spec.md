# Delta for collection-vouchers

## ADDED Requirements

### Requirement: Optional image or PDF attachment per payment line

Each `collection.voucher.line` MAY store one optional proof as Binary
(`attachment=True`) plus filename via `ir.attachment`. Omit/empty MUST remain valid.
Fields MUST be optional, `copy=False`, under existing internal-user line ACL. MUST
validate base64 and detected MIME (`image/*` or PDF only); MUST raise `UserError`
otherwise.

#### Scenario: Omit attachment valid

- GIVEN a payment line with no attachment
- WHEN saved
- THEN the line MUST persist

#### Scenario: Valid file persists

- GIVEN a line with valid base64 image/PDF and filename
- WHEN saved
- THEN Binary and filename MUST persist via `ir.attachment`

#### Scenario: Invalid content rejected

- GIVEN invalid base64 or non-image/non-PDF MIME
- WHEN saved
- THEN MUST raise `UserError` and MUST NOT persist the file

### Requirement: Attachment widgets on typed and Payment Lines views

Each typed embedded list field set (`bank_transfer`, `check`, `cash_deposit`) and
Payment Lines views MUST include optional Binary attachment and filename widgets.
Browser accept MUST be limited to `image/*` and PDF.

#### Scenario: Typed tables show Binary widgets

- GIVEN a voucher form open for editing
- WHEN a typed payment-line table is shown
- THEN it MUST include Binary attachment and filename widgets
- AND browser accept MUST allow `image/*` and PDF

#### Scenario: Payment Lines views show Binary widgets

- GIVEN Collections → Payment Lines
- WHEN an internal user opens list or form views for a line
- THEN Binary attachment and filename widgets MUST be present
- AND browser accept MUST allow `image/*` and PDF

### Requirement: MCP optional payment attachment on create

`create_collection_voucher` MAY accept one optional nested attachment per payment with
required `name`, `mimetype`, and base64 `datas` when present. Declared `mimetype` MUST
match content detection (`image/*` or PDF only); mismatch or bad base64 MUST raise
`UserError` with no writes. Create with attachments MUST persist voucher, lines, and
files atomically under a savepoint. Exact-retry by `document_id` MUST return the
existing voucher and MUST NOT add, replace, or compare attachments (even when the line
has none). All-new and conflict rules MUST remain unchanged.

#### Scenario: MCP create with nested attachment

- GIVEN unused `document_id`s and a payment with valid nested attachment
- WHEN `create_collection_voucher` runs
- THEN voucher, lines, and attachment MUST persist atomically under a savepoint

#### Scenario: MCP attachment MIME mismatch rejected

- GIVEN nested attachment with mismatched or non-image/non-PDF `mimetype`
- WHEN `create_collection_voucher` runs
- THEN MUST raise `UserError` with no writes

#### Scenario: Exact-retry skips attachment writes

- GIVEN all submitted `document_id`s belong to one existing voucher
- WHEN retried with or without nested attachments
- THEN voucher returns unchanged; attachments MUST NOT be written/replaced/compared

## MODIFIED Requirements

### Requirement: Deferred integrations not required

Completeness MUST NOT require HTTP API, WhatsApp metadata, partner/CRM linkage, or agent
calls. Optional per-line image/PDF attachments are an allowed capability and MUST NOT be
required for completeness of unrelated voucher features. (Previously: Completeness also
MUST NOT require attachments.)

#### Scenario: Completeness without deferred features

- GIVEN backend-only voucher management
- WHEN operators create, edit, validate, or reject vouchers with payment lines
- THEN success MUST NOT depend on deferred integrations
- AND success MUST NOT require that payment lines have attachments
