# Delta: collection-vouchers — typed line tables and Payment Lines menu

## MODIFIED Requirements

### Requirement: Menu and backend UI

The system MUST expose Collections → Payment Vouchers and Collections → Payment Lines.
List/search for vouchers MUST show reference, customer identification, readonly
`create_date`, and status. Form MUST show statusbar, Validate/Reject when `new`,
readonly `create_date`, and chatter/activity controls. Views MUST NOT show
`received_date`.

The voucher form MUST NOT use a single all-type editable payment-lines table. It MUST
show three stacked editable tables for `bank_transfer`, `check`, and `cash_deposit`
(same `collection.voucher.line` model), in that order, each filtered to its
`document_type`. Each table MUST hide `document_type` and MUST default new rows to that
table’s type. Field sets MUST be:

- `bank_transfer`: `document_id`, `amount`, `from_account`, `to_account`,
  `voucher_number`, `voucher_date`
- `check`: `document_id`, `amount`, `check_number`, `check_bank`, `check_type`,
  `check_issue_date`, `check_payment_date`
- `cash_deposit`: `document_id`, `amount`

A voucher MUST still allow mixed supported document types across those tables. The form
MUST NOT provide an editable table for `unsupported` lines. (Previously: Collections →
Payment Vouchers only; form used one editable `payment_ids` list showing `document_type`
and optional mixed columns.)

#### Scenario: Menu and form behaviors

- GIVEN the module installed and a voucher in `new`
- WHEN an internal user opens Collections → Payment Vouchers then the form
- THEN list/search MUST show reference, customer identification, `create_date`, status
- AND form MUST show statusbar, Validate/Reject, readonly `create_date`,
  chatter/activity UI without `received_date`
- AND form MUST show three stacked editable typed line tables (`bank_transfer`, `check`,
  `cash_deposit`) and MUST NOT show a single all-type payment-lines list

#### Scenario: Typed table defaults and fields

- GIVEN a voucher form open for editing
- WHEN an internal user adds a row in the bank transfer, check, or cash deposit table
- THEN the new line MUST receive that table’s `document_type`
- AND the table MUST expose only that type’s field set including `document_id`
- AND MUST NOT show a `document_type` column

#### Scenario: Mixed types on one voucher

- GIVEN a voucher with at least one bank transfer line and one check line
- WHEN the form is opened
- THEN each line MUST appear only in its matching typed table

#### Scenario: Payment Lines menu read-only browse

- GIVEN the module installed and existing payment lines
- WHEN an internal user opens Collections → Payment Lines
- THEN the action MUST list `collection.voucher.line` records
- AND create/edit from that action MUST be disabled
- AND search MUST allow filtering by line fields including `document_type`,
  `document_id`, `amount`, type-specific payment fields, and related voucher

#### Scenario: UI create_date visibility

- GIVEN an existing voucher
- WHEN list, search, kanban, or form is opened
- THEN readonly `create_date` MUST be visible and not editable

## ADDED Requirements

### Requirement: Unsupported lines remain non-editable on voucher form

`unsupported` payment lines MUST remain persistable (e.g. MCP) but MUST NOT appear in
the three typed editable form tables. Operators MUST be able to find them via
Collections → Payment Lines (e.g. filter `document_type=unsupported`).

#### Scenario: Unsupported line not in typed form tables

- GIVEN a voucher that has an `unsupported` payment line
- WHEN an internal user opens the voucher form
- THEN that line MUST NOT appear in the bank transfer, check, or cash deposit tables

#### Scenario: Unsupported line visible in Payment Lines menu

- GIVEN an `unsupported` payment line exists
- WHEN an internal user opens Collections → Payment Lines and filters to `unsupported`
- THEN that line MUST be listed
