# Delta for collection-vouchers

Align voucher catalog, Selection, provenance, and MCP proof so Nebula’s
seven-type dump can persist. OWL labels and reports are unchanged.

## ADDED Requirements

### Requirement: Catalog XMLIDs and 19.0.1.40.0 allow-list union

The catalog MUST include exactly these seven codes, each with a stable XMLID:

| Code | XMLID |
| --- | --- |
| `bank_transfer` | `collection.document_type_bank_transfer` |
| `check` | `collection.document_type_check` |
| `cash_deposit` | `collection.document_type_cash_deposit` |
| `unsupported` | `collection.document_type_unsupported` |
| `echeck` | `collection.document_type_echeck` |
| `cash` | `collection.document_type_cash` |
| `retention_certificate` | `collection.document_type_retention_certificate` |

Voucher `document_type`, `ocr_document_type`, `seller_document_type`, and review
snapshot type Selection MUST include the same seven codes. Upgrade to
`19.0.1.40.0` MUST union all seven codes onto every company’s
`allowed_document_type_ids` and MUST NOT remove custom extra types. Empty-only
seed MUST NOT be the upgrade path. New companies MUST start with all seven
enabled.

#### Scenario: Seven catalog XMLIDs exist

- GIVEN the module at `19.0.1.40.0`
- WHEN catalog records are inspected
- THEN the seven codes and XMLIDs above MUST exist
- AND `UNIQUE(code)` MUST still hold

#### Scenario: Upgrade unions without dropping extras

- GIVEN a company whose allow-list has the prior four types plus a custom extra
- WHEN upgrade to `19.0.1.40.0` runs
- THEN `echeck`, `cash`, and `retention_certificate` MUST be linked
- AND the custom extra MUST remain

#### Scenario: New company starts with seven types

- GIVEN a company created after this change
- WHEN `allowed_document_type_ids` is read
- THEN all seven catalog codes MUST be enabled

## MODIFIED Requirements

### Requirement: Payment field contract

Each voucher MUST persist `document_type` as one of `bank_transfer`, `check`,
`echeck`, `cash_deposit`, `retention_certificate`, `cash`, or `unsupported`, plus
nullable payment fields (OCR validators NOT required): `amount`, `from_account`,
`to_account`, `voucher_number`, `voucher_date`, `check_number`, `check_bank`,
`check_issue_date`, `check_payment_date`, `check_type` Selection
`common`/`deferred`, and `retention_kind` Selection
`iva`/`ganancias`/`iibb`/`suss`/`other` (nullable). `unsupported` MUST persist
without other payment fields. `cash` MUST persist with `amount` and optional
`voucher_date` and MUST NOT require designated proof.

| `document_type` | Type-owned fields |
| --- | --- |
| `bank_transfer` | `amount`, `from_account`, `to_account`, `voucher_number`, `voucher_date` |
| `check` | `amount`, `check_number`, `check_bank`, `check_issue_date`, `check_payment_date`, `check_type` |
| `echeck` | same as `check` |
| `cash_deposit` | `amount`, `to_account`, `voucher_number`, `voucher_date` |
| `retention_certificate` | `amount`, `voucher_number`, `voucher_date`, `retention_kind` |
| `cash` | `amount`, `voucher_date`; no proof |
| `unsupported` | discriminator only |

(Previously: Four types only; no `echeck`/`cash`/`retention_certificate` or
`retention_kind`.)

#### Scenario: Persist type-specific fields

- GIVEN `bank_transfer`, `check`, and `cash_deposit` vouchers with payment fields
  filled (`check_type` `common` or `deferred`)
- WHEN saved
- THEN each voucher MUST persist those values

#### Scenario: Unsupported and partial entry

- GIVEN an `unsupported` voucher plus a partial supported-type voucher
- WHEN saved
- THEN both MUST persist

#### Scenario: Persist echeck cash and retention_certificate

- GIVEN `echeck`, `cash`, and `retention_certificate` vouchers with their
  type-owned fields filled (`retention_kind` one of the five kinds)
- WHEN saved
- THEN each voucher MUST persist those values including `retention_kind` on the
  retention certificate

#### Scenario: Cash persists without proof

- GIVEN a `cash` voucher with `amount` and no designated proof
- WHEN saved
- THEN the voucher MUST persist
- AND `message_main_attachment_id` MAY be empty

### Requirement: MCP optional payment attachment on create

`create_collection_allocation` MAY accept one optional nested attachment per
payment with required `name`, `mimetype`, and base64 `datas` when present.
Declared `mimetype` MUST match content detection (`image/*` or PDF only);
`image/jpg` MUST be treated as equivalent to `image/jpeg` (case-insensitive)
when comparing declared vs detected MIME. Mismatch or bad base64 MUST raise
`UserError` with no writes. Explicit JSON `null`, `false`, or empty attachment
MUST be treated as omit. Seller-declared `cash` MUST succeed with attachment
omitted or null. Create with attachments MUST persist all vouchers and files
atomically under a savepoint by posting each nest onto the new voucher chatter
via `message_post` (MUST NOT write Binary `attachment`). Exact same-company
`document_id` reuse MUST NOT add, replace, or compare attachments (even when a
voucher has none) and MUST continue to allocation. All-new and conflict rules
MUST remain unchanged except as this change specifies for company, seller, and
type gates.
(Previously: Declared MIME had to equal detected MIME exactly; `image/jpg` vs
`image/jpeg` failed; cash-without-proof was not named.)

#### Scenario: MCP create with nested attachment

- GIVEN unused `document_id`s and a payment with valid nested attachment
- WHEN `create_collection_allocation` runs
- THEN vouchers and the nested file MUST persist atomically under a savepoint
- AND the file MUST appear on that voucher's chatter as designated proof

#### Scenario: MCP attachment MIME mismatch rejected

- GIVEN nested attachment with mismatched or non-image/non-PDF `mimetype`
- WHEN `create_collection_allocation` runs
- THEN MUST raise `UserError` with no writes

#### Scenario: Exact-retry skips attachment writes

- GIVEN every submitted `document_id` already exists in the same company
- WHEN retried with or without nested attachments
- THEN matching vouchers MUST be unchanged; attachments MUST NOT be
  written/replaced/compared
- AND the write MUST continue to allocation

#### Scenario: image/jpg aliases to jpeg

- GIVEN JPEG bytes whose detected MIME is `image/jpeg` and declared
  `mimetype` is `image/jpg`
- WHEN `create_collection_allocation` runs
- THEN the nested proof MUST persist as designated proof
- AND MUST NOT raise MIME mismatch

#### Scenario: Cash attachment null or omit is valid

- GIVEN a `cash` payment whose `attachment` is omitted or JSON `null`
- WHEN all-new `create_collection_allocation` runs
- THEN the voucher MUST persist without designated proof
- AND MUST NOT raise for missing attachment

### Requirement: Typed provenance copies of payment fields

Each voucher MUST persist typed raw-OCR and seller-confirmed copies of the
payment review field set, including `retention_kind`. Current columns MUST
remain the editable copy. Provenance MUST NOT include `document_id`,
`partner_id`, customer identification, `seller_id`, attachment, or base64, and
MUST NOT copy with the voucher. Cash-deposit MAY store `voucher_number` and
`voucher_date` in all three layers even when UI hides them. Voucher write MUST
reject provenance keys after create.
(Previously: Review field set omitted `retention_kind`.)

#### Scenario: Identity and proof stay outside provenance

- GIVEN an all-new MCP payment with `document_id`, customer, seller, and
  attachment
- WHEN create completes
- THEN provenance MUST contain only payment review fields
- AND MUST NOT contain `document_id`, customer, seller, attachment, or base64

#### Scenario: Cash-deposit extra keys stored in all layers

- GIVEN a cash-deposit payment whose nests include `voucher_number` and
  `voucher_date`
- WHEN all-new create completes
- THEN they MUST persist in all three layers
- AND UI MAY hide them for `cash_deposit`

#### Scenario: Voucher write rejects provenance keys

- GIVEN an existing voucher
- WHEN write includes raw or seller-confirmed field keys
- THEN the write MUST be rejected
- AND stored provenance MUST remain unchanged

#### Scenario: retention_kind stamps all three layers

- GIVEN an all-new `retention_certificate` payment whose nests include
  `retention_kind`
- WHEN create completes
- THEN current, `seller_retention_kind`, and `ocr_retention_kind` (when
  `raw_ocr` is present) MUST persist that kind

### Requirement: MCP nested provenance on all-new create

`create_collection_allocation` MUST require nested `seller_confirmed` and MAY
accept nested `raw_ocr` with the same typed keys as current fields, including
`retention_kind` and the seven `document_type` codes. Voucher fields MUST be
derived from `seller_confirmed`. Amounts in those nests MUST accept decimal
strings. Explicit JSON `null` or empty string on optional nest fields MUST be
treated as omit. When `raw_ocr` is present, it MUST persist as submitted; when
omitted or null, `ocr_*` MUST stay empty. Stamp `seller_*` always on all-new
create. Reject `unsupported` and non-positive `seller_confirmed` amount.
Seller-declared `cash` MUST succeed with `raw_ocr` omitted or null. UI/ORM
create without nests MUST remain allowed. Malformed nests, raw without seller,
or seller≠ derived current (minus `document_id`) MUST fail the batch with no
writes. Exact same-company `document_id` reuse MUST ignore those nests with no
provenance mutation and MUST continue to allocation.
(Previously: Four-type nests; `retention_kind` was an unknown key; cash-without-
proof and decimal-string amounts were not named.)

#### Scenario: Unchanged seller confirmation

- GIVEN unused `document_id`s and required `seller_confirmed`
- WHEN all-new create runs
- THEN seller-confirmed and current MUST be equal
- AND `seller_*` MUST be stamped

#### Scenario: Seller correction with optional raw

- GIVEN `raw_ocr` differs from `seller_confirmed`
- WHEN all-new create runs
- THEN raw MUST persist unchanged
- AND seller-confirmed and current MUST contain the correction

#### Scenario: Seller-only nest stamps seller fields

- GIVEN MCP create with `seller_confirmed` and no `raw_ocr`
- WHEN all-new create completes
- THEN `seller_*` MUST be stamped
- AND `ocr_*` MUST stay empty

#### Scenario: UI create without nests leaves empty provenance

- GIVEN UI or ORM create with neither `raw_ocr` nor `seller_confirmed`
- WHEN create completes
- THEN raw and seller-confirmed MUST be empty
- AND current payment fields MUST persist as submitted

#### Scenario: Bad provenance fails the batch

- GIVEN a payment with raw-only, malformed, or mismatched nests
- WHEN `create_collection_allocation` runs
- THEN the call MUST fail with no writes

#### Scenario: Exact replay ignores provenance nests

- GIVEN every submitted `document_id` already exists in the same company, with
  or without stored provenance
- WHEN retried with different or omitted nests
- THEN matching vouchers MUST return unchanged
- AND provenance and snapshots MUST NOT be written, backfilled, or mutated

#### Scenario: Cash dump without raw_ocr

- GIVEN a `cash` `seller_confirmed` with decimal-string `amount` and
  `raw_ocr` omitted or JSON `null`
- WHEN all-new create runs
- THEN `seller_*` MUST be stamped, `ocr_*` MUST stay empty, and the voucher
  MUST persist

#### Scenario: Explicit null optional nest fields are omit

- GIVEN `seller_confirmed` with unused typed fields set to JSON `null`
- WHEN all-new create runs
- THEN those fields MUST be treated as omitted
- AND MUST NOT fail as unknown or required values

### Requirement: Collection Settings persistence

Each company MUST persist Collection Settings: enabled sellers,
`auto_create_sheet` (default ON), and allowed document types (all seven catalog
codes). Settings action and menu labels MUST be **Collection Settings**. An
empty enabled-seller list MUST mean none for NEW work. All seven types MUST
start enabled. Unsupported MUST remain independently configurable. Saving these
fields MUST NOT clear `document_review_enabled`.
(Previously: Defaults enabled four types: transfer, check, cash deposit,
Unsupported.)

#### Scenario: Collection Settings labels

- GIVEN the module is installed
- WHEN an internal Settings admin opens Collections settings
- THEN the action and menu labels MUST be Collection Settings

#### Scenario: Empty enabled sellers means none for new work

- GIVEN a company with no enabled sellers
- WHEN a new voucher is created via UI, ORM, import, or MCP
- THEN the create MUST be rejected with no write

#### Scenario: Defaults enable auto-create and all seven types

- GIVEN a fresh install or a company with no prior Collection Settings
- WHEN settings are read
- THEN `auto_create_sheet` MUST be ON
- AND `bank_transfer`, `check`, `echeck`, `cash_deposit`,
  `retention_certificate`, `cash`, and `unsupported` MUST all be enabled

#### Scenario: Unsupported is configurable

- GIVEN Unsupported is disabled for the company
- WHEN a new voucher is created with `document_type` `unsupported`
- THEN the create MUST be rejected
- AND existing `unsupported` vouchers MUST remain visible
