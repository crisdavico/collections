# Delta for Collection Sheets

## MODIFIED Requirements

### Requirement: Sheet form notebook

Sheet form MUST show one Allocations notebook page (MUST NOT hide it). That list MUST
show Customer (`partner_id`) after name and before `state`. The form MUST NOT expose
`voucher_ids`. A saved sheet MUST expose a counted Vouchers action for that sheet's
members only. An unsaved sheet MUST hide and refuse that action. Unlink MUST remain via
voucher `sheet_id`.

(Previously: Notebook showed Vouchers (`voucher_ids`) and Allocations.)

#### Scenario: Allocations-only notebook with Customer

- GIVEN a saved sheet
- WHEN the form opens
- THEN the notebook MUST show Allocations only
- AND allocations MUST show Customer after name and before `state`
- AND `voucher_ids` MUST NOT appear on the form

#### Scenario: Saved sheet opens filtered vouchers

- GIVEN a saved sheet with members
- WHEN the Vouchers action runs
- THEN only vouchers with that `sheet_id` MUST appear
- AND Collections → Payment Vouchers MUST remain the menu destination

#### Scenario: Unsaved sheet hides and refuses voucher action

- GIVEN a new unsaved sheet
- WHEN the form is viewed or the Vouchers action invoked
- THEN the action MUST be hidden and invocation MUST be refused
