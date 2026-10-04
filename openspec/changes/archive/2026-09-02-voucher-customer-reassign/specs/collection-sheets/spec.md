# Delta for Collection Sheets

## ADDED Requirements

### Requirement: Reassign header action and kanban

A saved `open` sheet MUST expose a header action (after Document Review; hidden when
unsaved or not `open`) that opens that sheet's members in a dedicated customer-grouped
kanban. The action MUST `ensure_one`, MUST refuse unsaved sheets, and MUST refuse when
`state != open`. The action `views` list MUST be the reassign kanban then form and MUST
NOT open the Payment Vouchers state kanban.

The reassign kanban MUST group by `partner_id`, MUST allow record drag, and MUST disable
create, quick create, group create, group delete, group edit, and group drag.
`partner_id` MUST be present and MUST NOT be readonly. The Payment Vouchers
state-grouped kanban MUST remain unchanged.

#### Scenario: Open saved sheet opens customer kanban

- GIVEN a saved open sheet with members
- WHEN the reassign header action runs
- THEN only that sheet's vouchers MUST appear grouped by Customer

#### Scenario: Closed sheet refuses reassign action

- GIVEN a saved closed sheet
- WHEN the form is viewed or the reassign action is invoked
- THEN the action MUST be hidden
- AND invocation MUST be refused

#### Scenario: Unsaved sheet refuses reassign action

- GIVEN a new unsaved sheet
- WHEN the form is viewed or the reassign action is invoked
- THEN the action MUST be hidden
- AND invocation MUST be refused

#### Scenario: No Edit Delete or Add column

- GIVEN the reassign kanban
- WHEN it opens
- THEN group edit, group delete, and add-column MUST be unavailable
- AND create and quick create MUST be disabled

#### Scenario: partner_id not readonly on reassign kanban

- GIVEN the reassign kanban
- WHEN the arch is read
- THEN `partner_id` MUST be present
- AND MUST NOT be readonly

#### Scenario: Frozen state kanban unchanged

- GIVEN Collections → Payment Vouchers kanban
- WHEN it opens
- THEN grouping MUST remain by `state`
- AND create and edit MUST remain enabled
- AND the reassign kanban MUST be a distinct view

## MODIFIED Requirements

### Requirement: Closed sheet membership freeze

While a sheet is `closed`, membership MUST NOT be added, removed, or reassigned via
sheet members or voucher `sheet_id`, and voucher `partner_id` MUST NOT change. Operators
MUST Reopen first. Freeze applies while the sheet exists; sheet delete is not a
membership edit. Closed `partner_id` writes MUST raise the same membership `UserError`
as closed `sheet_id` membership writes.

(Previously: Freeze applied only to membership / `sheet_id`, not Customer.)

#### Scenario: Freeze add, remove, and reassign

- GIVEN a closed sheet with members
- WHEN add, remove, or reassign of membership is attempted
- THEN the write MUST be rejected and membership MUST be unchanged

#### Scenario: Closed partner_id reuses membership UserError

- GIVEN a voucher on a closed sheet
- WHEN `partner_id` is written
- THEN the write MUST raise the membership `UserError`
- AND `partner_id` MUST be unchanged
