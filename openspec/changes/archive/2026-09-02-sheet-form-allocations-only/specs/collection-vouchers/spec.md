# Delta for Collection Vouchers

## MODIFIED Requirements

### Requirement: Payment Vouchers UI

The system MUST expose Collections → Payment Vouchers as the only create/edit surface
(kanban, list, form; create and edit enabled). Kanban MUST group by `state`. List/search
MUST show reference, Customer (`partner_id`), readonly `create_date`, status, and
payment fields. Form MUST show statusbar, Approve/Reject when `pending`, readonly
`create_date`, type-specific payment fields, chatter/activity, and MUST NOT show
`received_date`. List, search, kanban, and form MUST show `partner_id` without a
bound-partner domain. List MUST expose optional hidden `sheet_id`; form MUST expose it
editable; search MUST expose field and group-by; kanban MUST NOT add it. Clearing
`sheet_id` on an open member MUST unlink; closed-sheet membership writes MUST be
rejected. MUST NOT expose a sheet-form voucher member list, Payment Lines, or
payment-line tables.

(Previously: Sheet member list was a voucher UI surface; list, form, and search omitted
`sheet_id`.)

#### Scenario: Menu and form behaviors

- GIVEN the module installed and a voucher in `pending`
- WHEN Payment Vouchers form opens
- THEN list/search MUST show reference, Customer, `create_date`, status
- AND form MUST show statusbar, Approve/Reject, readonly `create_date`, type-specific
  payment fields, chatter/activity, and MUST NOT show `received_date` or payment-line
  tables

#### Scenario: Kanban grouped by state

- GIVEN Payment Vouchers kanban
- WHEN it opens
- THEN vouchers MUST be grouped by `state`
- AND create and edit MUST be enabled

#### Scenario: Payment Lines menu absent

- GIVEN the module installed
- WHEN menus load
- THEN Collections → Payment Lines MUST NOT appear

#### Scenario: UI create_date visibility

- GIVEN an existing voucher
- WHEN list, search, kanban, or form is opened
- THEN readonly `create_date` MUST be visible and not editable

#### Scenario: Customer field has no domain

- GIVEN Payment Vouchers list, search, kanban, or form
- WHEN Customer is opened
- THEN the field MUST be `partner_id`
- AND MUST NOT restrict choices to bound connector customers

#### Scenario: sheet_id on list form search

- GIVEN an existing voucher with or without a sheet
- WHEN list, form, or search is opened
- THEN list MUST show optional hidden `sheet_id`, form editable `sheet_id`, and search a
  `sheet_id` field and group-by
- AND kanban MUST NOT show `sheet_id`

#### Scenario: Clear sheet_id unlinks open membership

- GIVEN a voucher assigned to an open sheet
- WHEN an internal user clears `sheet_id` on the voucher form and saves
- THEN the voucher MUST become unassigned and the sheet MUST persist

#### Scenario: Closed-sheet unlink denied

- GIVEN a voucher assigned to a closed sheet
- WHEN an internal user clears or changes `sheet_id` on the voucher form
- THEN the write MUST be rejected and membership MUST be unchanged
