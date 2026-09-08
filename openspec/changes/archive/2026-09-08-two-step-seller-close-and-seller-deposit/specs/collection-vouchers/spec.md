# Delta for Collection Vouchers

## ADDED Requirements

### Requirement: Sentinel partner for seller_deposit

`seller_deposit` vouchers MUST point at a seeded non-customer sentinel `res.partner`.
`partner_id` MUST remain required. The system MUST NOT make `partner_id` optional. The
sentinel MUST be a data record (`noupdate`) resolvable per company. NEW `seller_deposit`
create MUST stamp that sentinel and MUST NOT accept a customer identification.
(Previously: Every voucher required a real customer partner; no remittance sentinel.)

#### Scenario: Deposit stamps sentinel

- GIVEN a lawful `seller_deposit` create
- WHEN persist completes
- THEN `partner_id` MUST be the sentinel
- AND MUST NOT be empty

#### Scenario: Customer identification refused

- GIVEN `create_seller_deposit` or ORM create of `seller_deposit`
- WHEN a customer identification or non-sentinel `partner_id` is supplied
- THEN MUST refuse with no write

### Requirement: Receipt values reverse relation and replaced_amount

Each voucher MUST expose `receipt_value_ids` as the inverse of
`collection.receipt.value` and a `replaced_amount` equal to Σ replacement `replace`
minus Σ `reverse` for that voucher as cash. Unassigned remittance MUST still satisfy
`partner_id` required.
(Previously: Core had no reverse receipt-value relation; `replaced_amount` did not
exist.)

#### Scenario: Reverse relation lists values

- GIVEN voucher V with values on two same-sheet receipts
- WHEN `receipt_value_ids` is read
- THEN both values MUST appear

#### Scenario: replaced_amount from ledger

- GIVEN cash voucher V with replace 40 and reverse 0
- WHEN `replaced_amount` is read
- THEN it MUST equal 40

### Requirement: Replacement trigger on validated_collections write

Writing voucher `state` to `validated_collections` MUST run cash replacement when the
voucher is a `seller_deposit` on a sheet that still allows receipt-value writes. The
trigger MUST be that write (including audited Document Review approve). It MUST NOT
require `document_review_enabled`. It MUST NOT hook only `action_review_approve`.
Companies with Document Review OFF MUST still replace. A second write that does not
transition to `validated_collections` MUST NOT re-replace.
(Previously: No replacement trigger.)

#### Scenario: Deposit validation replaces cash

- GIVEN a submitted sheet with replaceable cash and a `seller_deposit` in
  `validated_seller`
- WHEN `state` is written to `validated_collections`
- THEN replacement rows MUST persist per Collection Receipts
- AND receipt `amount_applied` MUST be unchanged

#### Scenario: Review-off companies still replace

- GIVEN Document Review OFF and a `seller_deposit` written to `validated_collections`
- WHEN that write completes
- THEN replacement MUST run
- AND MUST NOT raise because review is off

#### Scenario: Non-transition write does not re-replace

- GIVEN a `seller_deposit` already `validated_collections` with replacement rows
- WHEN a later write does not change `state` into `validated_collections`
- THEN no additional replacement row MUST be created

### Requirement: MCP write create_seller_deposit

The system MUST expose `create_seller_deposit` via `@mcp_tool` on `muk_mcp.mixin`
(`category=write`, `registry=mcp`), method-discovered; MUST NOT add a DB tool record.
Calls MUST use the authenticated user and MUST NOT `sudo()`. Input MUST require integer
`seller_id`, amount, `voucher_number`, `voucher_date`, and MAY accept nested
`attachment`. The tool MUST NOT accept `customer_identification` or `sheet_id` from the
caller. It MUST resolve the seller's own `submitted` sheet, stamp the sentinel partner
and `document_type` `seller_deposit`, stamp `validated_seller`, pass that `sheet_id`
explicitly, and require new-work for that seller and `seller_deposit`. Portal or public
callers MUST receive `AccessError`. Errors MUST be raised, never `{"error":...}`. Zero
or more than one `submitted` sheet MUST raise `UserError`. `create_collection_allocation`
MUST remain customer-required and `open`-sheet-only.
(Previously: No MCP path could create a no-customer remittance voucher.)

#### Scenario: Internal seller creates a deposit on submitted

- GIVEN an internal caller and an internal seller with exactly one `submitted` sheet
- WHEN `create_seller_deposit` runs with amount, number, date, and optional proof
- THEN one `seller_deposit` voucher MUST persist on that sheet
- AND `partner_id` MUST be the sentinel
- AND `state` MUST be `validated_seller`
- AND no `sudo()` MUST occur

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

### Requirement: Seller deposit form fields

Payment Vouchers form MUST show `voucher_number` and `voucher_date` for
`seller_deposit` on current, OCR, and seller-confirmed layers. Search MUST include a
`seller_deposit` document-type filter. `partner_id` MUST appear exactly once per arch.
The system MUST NOT add a second Customer field for remittance.
(Previously: `voucher_number` / `voucher_date` were hidden for types other than
transfer, check extras, cash deposit, and retention.)

#### Scenario: Number and date visible for seller_deposit

- GIVEN a `seller_deposit` voucher
- WHEN Payment Vouchers form opens
- THEN `voucher_number` and `voucher_date` MUST be visible on current, OCR, and
  seller-confirmed layers

#### Scenario: Search filter exists

- GIVEN Payment Vouchers search
- WHEN filters are inspected
- THEN a `document_type` filter for `seller_deposit` MUST exist

#### Scenario: Single partner_id in arch

- GIVEN Payment Vouchers form, list, and search arch
- WHEN `partner_id` nodes are counted
- THEN each arch MUST contain exactly one `partner_id`

## MODIFIED Requirements

### Requirement: Payment field contract

Each voucher MUST persist `document_type` as one of `bank_transfer`, `check`,
`echeck`, `cash_deposit`, `retention_certificate`, `cash`, `unsupported`, or
`seller_deposit`, plus nullable payment fields (OCR validators NOT required): `amount`,
`from_account`, `to_account`, `voucher_number`, `voucher_date`, `check_number`,
`check_bank`, `check_issue_date`, `check_payment_date`, `check_type` Selection
`common`/`deferred`, and `retention_kind` Selection
`iva`/`ganancias`/`iibb`/`suss`/`other` (nullable). `unsupported` MUST persist
without other payment fields. `cash` MUST persist with `amount` and optional
`voucher_date` and MUST NOT require designated proof. `seller_deposit` MUST persist
with `amount`, `voucher_number`, and `voucher_date`, MAY have designated proof, and
MUST use the sentinel partner.

| `document_type` | Type-owned fields |
| --- | --- |
| `bank_transfer` | `amount`, `from_account`, `to_account`, `voucher_number`, `voucher_date` |
| `check` | `amount`, `check_number`, `check_bank`, `check_issue_date`, `check_payment_date`, `check_type` |
| `echeck` | same as `check` |
| `cash_deposit` | `amount`, `to_account`, `voucher_number`, `voucher_date` |
| `retention_certificate` | `amount`, `voucher_number`, `voucher_date`, `retention_kind` |
| `cash` | `amount`, `voucher_date`; no proof |
| `unsupported` | discriminator only |
| `seller_deposit` | `amount`, `voucher_number`, `voucher_date`; sentinel partner |

(Previously: Seven types only; no `seller_deposit`.)

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

#### Scenario: Persist seller_deposit

- GIVEN a `seller_deposit` voucher with `amount`, `voucher_number`, `voucher_date`,
  and the sentinel partner
- WHEN saved
- THEN the voucher MUST persist those values
- AND `partner_id` MUST remain the sentinel

### Requirement: Collection Settings persistence

Each company MUST persist Collection Settings: enabled sellers,
`auto_create_sheet` (default ON), and allowed document types (all eight catalog
codes). Settings action and menu labels MUST be **Collection Settings**. An
empty enabled-seller list MUST mean none for NEW work. All eight types MUST
start enabled. Unsupported MUST remain independently configurable. Saving these
fields MUST NOT clear `document_review_enabled`.
(Previously: Defaults enabled seven catalog codes.)

#### Scenario: Collection Settings labels

- GIVEN the module is installed
- WHEN an internal Settings admin opens Collections settings
- THEN the action and menu labels MUST be Collection Settings

#### Scenario: Empty enabled sellers means none for new work

- GIVEN a company with no enabled sellers
- WHEN a new voucher is created via UI, ORM, import, or MCP
- THEN the create MUST be rejected with no write

#### Scenario: Defaults enable auto-create and all eight types

- GIVEN a fresh install or a company with no prior Collection Settings
- WHEN settings are read
- THEN `auto_create_sheet` MUST be ON
- AND `bank_transfer`, `check`, `echeck`, `cash_deposit`,
  `retention_certificate`, `cash`, `unsupported`, and `seller_deposit` MUST all be
  enabled

#### Scenario: Unsupported is configurable

- GIVEN Unsupported is disabled for the company
- WHEN a new voucher is created with `document_type` `unsupported`
- THEN the create MUST be rejected
- AND existing `unsupported` vouchers MUST remain visible

### Requirement: Catalog XMLIDs and 19.0.1.40.0 allow-list union

The catalog MUST include exactly these eight codes, each with a stable XMLID:

| Code | XMLID |
| --- | --- |
| `bank_transfer` | `collection.document_type_bank_transfer` |
| `check` | `collection.document_type_check` |
| `cash_deposit` | `collection.document_type_cash_deposit` |
| `unsupported` | `collection.document_type_unsupported` |
| `echeck` | `collection.document_type_echeck` |
| `cash` | `collection.document_type_cash` |
| `retention_certificate` | `collection.document_type_retention_certificate` |
| `seller_deposit` | `collection.document_type_seller_deposit` |

Voucher `document_type`, `ocr_document_type`, `seller_document_type`, and review
snapshot type Selection MUST include the same eight codes. Upgrade to
`19.0.1.40.0` MUST union the then-seven codes onto every company’s
`allowed_document_type_ids` and MUST NOT remove custom extra types. Upgrade to
`19.0.1.43.0` MUST union all eight codes onto every company via
`_collection_enable_all_document_types` and MUST NOT remove extras. Manifest MUST
be `19.0.1.43.0`. `migrations/19.0.1.42.0/` MUST NOT exist. Empty-only seed MUST
NOT be the upgrade path. New companies MUST start with all eight enabled.
(Previously: Exactly seven catalog codes; last allow-list union was `19.0.1.40.0`.)

#### Scenario: Seven catalog XMLIDs exist

- GIVEN the module at `19.0.1.40.0`
- WHEN catalog records are inspected
- THEN the seven codes and XMLIDs above except `seller_deposit` MUST exist
- AND `UNIQUE(code)` MUST still hold

#### Scenario: Upgrade unions without dropping extras

- GIVEN a company whose allow-list has the prior four types plus a custom extra
- WHEN upgrade to `19.0.1.40.0` runs
- THEN `echeck`, `cash`, and `retention_certificate` MUST be linked
- AND the custom extra MUST remain

#### Scenario: New company starts with seven types

- GIVEN a company created after the seven-type catalog and before `seller_deposit`
- WHEN `allowed_document_type_ids` is read at that version
- THEN those seven catalog codes MUST be enabled

#### Scenario: Eight catalog XMLIDs exist

- GIVEN the module at `19.0.1.43.0`
- WHEN catalog records are inspected
- THEN the eight codes and XMLIDs above MUST exist
- AND `UNIQUE(code)` MUST still hold

#### Scenario: Upgrade to 19.0.1.43.0 unions seller_deposit

- GIVEN a company whose allow-list has the seven prior types plus a custom extra
- WHEN upgrade to `19.0.1.43.0` runs
- THEN `seller_deposit` MUST be linked
- AND the custom extra MUST remain
- AND `migrations/19.0.1.42.0/` MUST NOT exist

#### Scenario: New company starts with eight types

- GIVEN a company created after this change
- WHEN `allowed_document_type_ids` is read
- THEN all eight catalog codes MUST be enabled
