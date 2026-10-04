# Delta for Collection Vouchers

## ADDED Requirements

### Requirement: Sheet-state voucher field guards

Voucher membership (`sheet_id` add, remove, or reassign) and voucher business fields
MUST be writable only while the sheet is `open` (or the voucher is unassigned). When the
sheet is `proposal`, `closed`, or `cancelled`, those writes MUST raise `UserError` with
no persist, including via form or RPC. Chatter MUST remain writable. Partner-allocation
constrain MUST still apply. (Previously: Membership freeze was closed-only; business
fields had no sheet-state guard.)

#### Scenario: Open membership and business fields writable

- GIVEN a voucher on an open sheet
- WHEN `sheet_id` is cleared or a business field is written lawfully
- THEN the write MUST persist

#### Scenario: Proposal closed cancelled membership refused

- GIVEN a voucher on a proposal, closed, or cancelled sheet
- WHEN `sheet_id` is cleared or changed
- THEN MUST raise `UserError` and membership MUST be unchanged

#### Scenario: Proposal closed cancelled business fields refused

- GIVEN a voucher on a proposal, closed, or cancelled sheet
- WHEN a business field is written via form or RPC
- THEN MUST raise `UserError` and stored values MUST be unchanged

#### Scenario: Chatter remains writable when frozen

- GIVEN a voucher on a proposal, closed, or cancelled sheet
- WHEN an operator posts a chatter comment
- THEN that comment MUST persist on the voucher thread

## MODIFIED Requirements

### Requirement: Payment Vouchers UI

MUST expose Collections → Payment Vouchers as the only create/edit surface (`view_mode`
`list,form`; create and edit enabled). MUST `<delete>` stages kanban. MUST NOT keep
Reassign Customers kanban. Menu Payment Vouchers MUST stay `sequence=10`. Form MUST show
non-clickable statusbar, **Validate by Seller** when `draft`, readonly `create_date`,
type-specific payment fields, chatter/activity; MUST NOT show `received_date`,
Approve/Reject, a Collections button, History, or payment-line tables. `partner_id` MUST
have no bound-partner domain. Clearing `sheet_id` on an open member MUST unlink;
non-open-sheet membership writes MUST be rejected. MUST NOT expose sheet-form member
list or Payment Lines.

| Surface      | MUST                                                                                                            |
| ------------ | --------------------------------------------------------------------------------------------------------------- |
| List visible | `name`, `create_date`, `sheet_id`, `seller_id`, `document_type`, `amount`, `state`                              |
| List hide    | `partner_id`, `company_id`, `document_id` optional hide; `currency_id` column-invisible                         |
| Search       | one filter per state; one per `document_type`; Created On `date="create_date"`; keep name/customer/seller/sheet |

(Previously: MUST keep Reassign Customers kanban; closed-sheet membership writes
rejected.)

#### Scenario: Menu and form behaviors

- GIVEN the module installed and a `draft` voucher
- WHEN Payment Vouchers form opens
- THEN list MUST show `name`, `create_date`, `sheet_id`, `seller_id`, `document_type`,
  `amount`, `state`
- AND form MUST show non-clickable statusbar, Validate by Seller, readonly
  `create_date`, type-specific fields, chatter; MUST NOT show `received_date`,
  Approve/Reject, Collections, History, or payment-line tables

#### Scenario: Kanban grouped by state

- GIVEN Payment Vouchers
- WHEN views load
- THEN stages kanban MUST NOT exist, `view_mode` MUST be `list,form`, and Reassign
  Customers kanban MUST NOT remain

#### Scenario: Payment Lines menu absent

- GIVEN the module installed
- WHEN menus load
- THEN Collections → Payment Lines MUST NOT appear

#### Scenario: Menu sequence locked

- GIVEN Collections menus
- WHEN sequences are inspected
- THEN Payment Vouchers MUST be `sequence=10`

#### Scenario: Search filters

- GIVEN Payment Vouchers search
- WHEN filters are inspected
- THEN one filter per voucher state and per `document_type` MUST exist, and Created On
  MUST be a date filter on `create_date`

#### Scenario: UI create_date visibility

- GIVEN an existing voucher
- WHEN list, search, or form is opened
- THEN readonly `create_date` MUST be visible and not editable

#### Scenario: Customer field has no domain

- GIVEN Payment Vouchers list, search, or form
- WHEN Customer is opened
- THEN the field MUST be `partner_id` with no bound-connector domain

#### Scenario: sheet_id on list form search

- GIVEN an existing voucher with or without a sheet
- WHEN list, form, or search is opened
- THEN list MUST show visible `sheet_id`, form editable `sheet_id` when the sheet is
  `open` or the voucher is unassigned, search field and group-by

#### Scenario: Clear sheet_id unlinks open membership

- GIVEN a voucher assigned to an open sheet
- WHEN `sheet_id` is cleared on the form and saved
- THEN the voucher MUST be unassigned and the sheet MUST persist

#### Scenario: Closed-sheet unlink denied

- GIVEN a voucher assigned to a proposal, closed, or cancelled sheet
- WHEN `sheet_id` is cleared or changed on the form
- THEN the write MUST be rejected and membership MUST be unchanged

### Requirement: Partner write follows allocation

When `partner_id` changes, the system MUST NOT auto-compute or auto-write
`allocation_id`. An allocated voucher MUST be unassigned before Customer MAY change; a
`partner_id` write while `allocation_id` is set MUST raise `UserError` with no persist.
MUST NOT `sudo()`. Same-value `partner_id` MUST NOT recompute allocation. `confirmed`
current allocation MUST refuse the move with no field change. While the sheet is `open`
and the voucher is unassigned, any voucher state MAY change Customer. (Previously:
Customer change auto-attached the unique draft same-sheet allocation or left the voucher
unallocated with chatter.)

#### Scenario: Allocated customer change refused

- GIVEN an open-sheet voucher with `allocation_id` set
- WHEN `partner_id` is written to another customer
- THEN MUST raise `UserError`
- AND `partner_id` and `allocation_id` MUST be unchanged

#### Scenario: Unassign then customer change

- GIVEN an open-sheet voucher on a draft allocation
- WHEN `allocation_id` is cleared then `partner_id` is written to another customer
- THEN `partner_id` MUST persist and `allocation_id` MUST remain unset

#### Scenario: Same-value partner write

- GIVEN an open-sheet voucher on a draft allocation
- WHEN `partner_id` is written to the same customer
- THEN both fields MUST remain unchanged

#### Scenario: Confirmed source refused

- GIVEN an open-sheet voucher whose `allocation_id` is `confirmed`
- WHEN `partner_id` is written
- THEN MUST refuse and both fields MUST be unchanged

#### Scenario: Unassigned voucher may change customer

- GIVEN an open-sheet unallocated voucher in `draft`, `validated_seller`, or
  `validated_collections`
- WHEN `partner_id` is written to another customer
- THEN the write MUST succeed and `state` MUST stay unchanged

#### Scenario: Fully applied source no longer auto-moves

- GIVEN an open-sheet voucher on a draft allocation whose residual is 0
- WHEN `partner_id` is written to another customer without unassigning
- THEN MUST raise `UserError` and both fields MUST be unchanged

## REMOVED Requirements

### Requirement: Context-gated partner group_expand

(Reason: Reassign Customers kanban is removed; `group_expand` existed only to populate
empty Customer columns on that kanban.) (Migration: Remove `_read_group_partner_ids`,
reassign context `collection_reassign_sheet_id`, and tests that assert expand columns.
Payment Vouchers grouped-by-Customer MUST use identity groups.)
