# Delta for Collection Receipts

## ADDED Requirements

### Requirement: Frozen sheet refuses cash replacement create

When the sheet is `closed` or `cancelled`, create of `collection.cash.replacement` MUST
be refused. Audited Close, Cancel, and Reinstate MUST NOT create replacement rows. MUST
NOT `sudo()`. (Previously: Replacement create was context-gated only.)

#### Scenario: Frozen sheet refuses replacement create

- GIVEN a closed or cancelled sheet
- WHEN a cash replacement create is attempted
- THEN MUST refuse with no persist

#### Scenario: Cancel still does not reverse

- GIVEN replacement rows on a closed sheet
- WHEN Cancel then Reinstate run
- THEN no replacement create MUST occur
- AND existing `replace` rows MUST remain

## MODIFIED Requirements

### Requirement: Freeze and issued immutability

When the sheet is `closed` or `cancelled`, receipt and value create, write, and unlink
MUST be refused except audited Close (`draft` → `closed`), Cancel (`closed` → `draft`),
and Reinstate. A receipt in `issued` MUST be immutable (create of values, write, and
unlink refused) even if the allocation is later drafted. MUST NOT `sudo()`. (Previously:
Freeze refused write and unlink only; Close issued via `create_receipt`.)

#### Scenario: Closed sheet refuses receipt write

- GIVEN a closed or cancelled sheet with receipts
- WHEN receipt or value write or unlink is attempted
- THEN MUST refuse and stored rows MUST be unchanged

#### Scenario: Issued receipt immutable

- GIVEN an issued receipt
- WHEN write or unlink is attempted
- THEN MUST refuse

#### Scenario: Frozen sheet refuses receipt create

- GIVEN a closed or cancelled sheet
- WHEN receipt or value create is attempted
- THEN MUST refuse with no persist

#### Scenario: Cancel reopens closed not issued

- GIVEN a closed sheet with a `closed` receipt and an `issued` receipt
- WHEN Cancel runs
- THEN the `closed` receipt MUST become `draft` with no `external_receipt_id`
- AND the `issued` receipt MUST remain `issued`

### Requirement: ERP identity and state

`external_receipt_id` MUST be unique among non-null values. Receipt `state` MUST be
`draft`, `closed`, or `issued` only. Default MUST be `draft`. Close MUST set local
`draft` receipts to `closed` and MUST NOT stamp `external_receipt_id`. Historical
`issued` receipts MUST keep `issued` and their external identity. Raw `state` write MUST
be rejected except audited `draft` → `closed` and `closed` → `draft`. (Previously:
`state` was `draft` or `issued` only; Close stamped `issued` via `create_receipt`.)

#### Scenario: Unique external id

- GIVEN a receipt with `external_receipt_id` E
- WHEN another receipt is stored with the same non-null E
- THEN MUST refuse
- AND a second null `external_receipt_id` MUST persist

#### Scenario: Close leaves draft receipts closed locally

- GIVEN a grouped draft receipt on a proposal sheet
- WHEN Close runs
- THEN `state` MUST be `closed` and `external_receipt_id` MUST remain unset
- AND MUST NOT call `create_receipt`

#### Scenario: Historical issued keeps identity

- GIVEN an issued receipt with non-null `external_receipt_id`
- WHEN Close, Cancel, or Reinstate runs on its sheet
- THEN `state` MUST remain `issued` and `external_receipt_id` MUST be unchanged

#### Scenario: Raw receipt state write rejected

- GIVEN a draft or closed receipt
- WHEN `state` is written except via audited Close or Cancel
- THEN the write MUST be rejected and stored `state` MUST be unchanged

### Requirement: Read-mostly views

Receipt UI MUST be read-mostly. Historical `issued` and `external_receipt_id` MUST NOT
be stamped by operator form edit or by Close. Collection Receipts list, search, and form
MUST NOT expose `external_receipt_id`. The allocation form Receipts list MUST NOT expose
`external_receipt_id`. List tags MUST be `<list>` (MUST NOT `<tree>`). (Previously:
Issuance was owned by the ERP Close hand-off.)

#### Scenario: Form does not issue

- GIVEN a draft receipt on a draft allocation
- WHEN an operator opens the receipt or allocation form
- THEN they MUST NOT stamp `issued` or set `external_receipt_id` as a normal form edit
- AND Collection Receipts views and the allocation Receipts list MUST NOT show
  `external_receipt_id`

#### Scenario: Closed is a legal receipt state

- GIVEN a closed receipt after Close
- WHEN an operator opens the receipt form
- THEN `state` MUST show `closed`
- AND they MUST NOT stamp `issued` or `external_receipt_id`

## REMOVED Requirements

### Requirement: Close dispatches create_receipt

(Reason: Close is local-only and MUST NOT consult the connector or call
`create_receipt`.) (Migration: Keep connector `create_receipt` unused from Close.
Rewrite tests that expect Close dispatch. Historical `issued` receipts keep state and
external identity. Zero- receipt Close success is specified under Open/closed
lifecycle.)
