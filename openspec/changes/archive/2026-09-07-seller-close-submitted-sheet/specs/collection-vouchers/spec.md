# Delta for Collection Vouchers

## MODIFIED Requirements

### Requirement: Create auto-assign to open sheet

On voucher create, when `auto_create_sheet` is ON, `seller_id` is set, and `sheet_id` is
omitted, the system MUST auto-assign within that voucher's company: unique open sheet
for that company and seller → assign; none → create one open sheet then assign; more
than one open in that company → `UserError` with no write. When `auto_create_sheet` is
OFF, create MUST skip automatic create AND assign (voucher stays unassigned unless
`sheet_id` is explicit). Explicit `sheet_id` MUST be honored when the target is the same
company, same seller, and `open` or `submitted`; assign to a `proposal`, `closed`, or
`cancelled` sheet MUST fail. Write of `seller_id` on an existing voucher MUST NOT
auto-assign. The system MUST NOT backfill existing unassigned vouchers. List Action and
explicit sheet create remain available when auto-create is OFF (see collection-sheets).
(Previously: Explicit `sheet_id` honored only when the target was `open`.)

#### Scenario: UI or ORM create with seller assigns

- GIVEN `auto_create_sheet` ON and a seller with exactly one open sheet in that company
- WHEN a voucher is created with that enabled `seller_id` and omitted `sheet_id`
- THEN the voucher MUST be assigned to that open sheet

#### Scenario: Create without seller stays unassigned

- GIVEN an existing voucher with null `seller_id` and omitted `sheet_id`
- WHEN it is saved without assigning a sheet
- THEN the voucher MUST remain unassigned

#### Scenario: Explicit sheet_id honored when open

- GIVEN an open same-seller same-company sheet
- WHEN a voucher is created with that enabled `seller_id` and explicit `sheet_id`
- THEN the voucher MUST be assigned to that sheet

#### Scenario: Explicit sheet_id honored when submitted

- GIVEN a submitted same-seller same-company sheet
- WHEN a voucher is created with that enabled `seller_id` and explicit `sheet_id`
- THEN the voucher MUST be assigned to that submitted sheet

#### Scenario: Assign to closed sheet fails

- GIVEN a closed same-seller sheet
- WHEN a voucher is created or written with that `sheet_id`
- THEN the write MUST fail

#### Scenario: Later seller write does not auto-assign

- GIVEN an existing unassigned voucher
- WHEN `seller_id` is written to another enabled seller
- THEN `sheet_id` MUST remain empty

#### Scenario: No open sheet creates then assigns

- GIVEN `auto_create_sheet` ON and a seller with zero open sheets in that company
- WHEN a voucher is created with that enabled `seller_id` and omitted `sheet_id`
- THEN one open sheet MUST be created for that seller in that company
- AND the voucher MUST be assigned to it

#### Scenario: More than one open rejects create

- GIVEN `auto_create_sheet` ON and a seller with more than one open sheet in that
  company
- WHEN a voucher is created with that `seller_id` and omitted `sheet_id`
- THEN create MUST raise `UserError` with no voucher written

#### Scenario: Auto-create off skips create and assign

- GIVEN `auto_create_sheet` OFF, an enabled seller, omitted `sheet_id`, and zero open
  sheets in that company
- WHEN a voucher is created
- THEN the voucher MUST persist unassigned
- AND no sheet MUST be created

### Requirement: Sheet-state voucher field guards

Voucher membership (`sheet_id` add, remove, or reassign) and voucher business fields
MUST be writable while the sheet is `open` or `submitted` (or the voucher is
unassigned). When the sheet is `proposal`, `closed`, or `cancelled`, those writes MUST
raise `UserError` with no persist, including via form or RPC. The membership freeze
`UserError` text MUST remain
`Closed collection sheets cannot change membership. Reopen first.`
Chatter MUST remain writable. Partner-allocation constrain MUST still apply.
(Previously: Writable only while `open`; freeze while `proposal`, `closed`, or
`cancelled`.)

#### Scenario: Open membership and business fields writable

- GIVEN a voucher on an open sheet
- WHEN `sheet_id` is cleared or a business field is written lawfully
- THEN the write MUST persist

#### Scenario: Submitted membership and business fields writable

- GIVEN a voucher on a submitted sheet
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
