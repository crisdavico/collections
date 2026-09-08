# Delta for Collection Sheets

## ADDED Requirements

### Requirement: Frozen associate create freeze

When a sheet is `closed` or `cancelled`, create of business data on that sheet,
allocation, allocation line, receipt, receipt value, allocation revision, or cash
replacement MUST be refused. Audited Close, Cancel, and Reinstate, plus tracking and
chatter, MAY write. Member vouchers MUST freeze via the parent sheet. (Previously:
Freeze covered write and unlink, not create.)

#### Scenario: Frozen sheet refuses associate create

- GIVEN a closed or cancelled sheet
- WHEN create of an allocation, line, receipt, value, revision, or cash replacement runs
- THEN MUST refuse with no persist

#### Scenario: Proposal still allows allocation create

- GIVEN a proposal sheet
- WHEN an allocation is created lawfully
- THEN the create MUST persist

## MODIFIED Requirements

### Requirement: Open/closed lifecycle

Sheets MUST have required `state` `open`, `submitted`, `proposal`, `closed`, or
`cancelled`, default `open`. Existing `open` and `closed` rows MUST stay unchanged on
upgrade (MUST NOT remap). Legal transitions MUST be: `open` → Seller Close →
`submitted`; `submitted` → Confirm → `proposal`; `proposal` → Close → `closed`;
`submitted` or `proposal` or `closed` → Cancel → `cancelled`; `cancelled` → Reinstate →
`submitted`. Create MUST persist `open` and MUST reject any other `state`. `open` MUST
be reachable only via create. Close (`action_close`) MUST succeed only from `proposal`,
MUST NOT consult the connector, and MUST NOT call `create_receipt`. Close MUST, in one
transaction, set every local `draft` receipt to `closed` with no `external_receipt_id`,
confirm every allocation, and close the sheet. Member vouchers MUST remain
`validated_collections`. Cancel MUST succeed from `submitted`, `proposal`, or `closed`
and MUST return every allocation to `draft`. Cancel from `closed` MUST reopen local
`closed` receipts to `draft` and MUST NOT change `issued` receipts. While `cancelled`,
the sheet MUST remain frozen until Reinstate. Reinstate MUST succeed from `cancelled`
without checking one-open, MUST write `submitted` (MUST NOT write `open`), and MUST
leave allocations `draft`. Confirm MUST run only from `submitted` and MUST NOT confirm
allocations. Any internal user MAY run those audited actions. Write of raw `state` MUST
be rejected except via Seller Close, Confirm, Close, Cancel, or Reinstate. Reinstate of
a historical cancelled sheet MUST remain allowed even if the seller is later disabled.
Open and Reopen MUST NOT exist. (Previously: Close dispatched connector `create_receipt`
then confirmed allocations.)

#### Scenario: Default open on create

- GIVEN an internal user creates a sheet with a valid seller
- WHEN saved
- THEN `state` MUST be `open`

#### Scenario: Close when proposal

- GIVEN a proposal sheet with zero or more draft allocations and optional draft receipts
- WHEN an internal user Closes it
- THEN `state` MUST become `closed`
- AND every allocation MUST be `confirmed`
- AND every draft receipt MUST be `closed` with no `external_receipt_id`

#### Scenario: Close without connector succeeds

- GIVEN a proposal sheet and no company active connector
- WHEN Close runs
- THEN MUST succeed and MUST NOT call `create_receipt`

#### Scenario: Close without receipts still closes

- GIVEN a proposal sheet whose allocations have zero receipts
- WHEN Close runs
- THEN allocations MUST be `confirmed` and the sheet MUST be `closed`

#### Scenario: Close keeps voucher documentary state

- GIVEN a proposal sheet whose members are `validated_collections`
- WHEN Close runs
- THEN those vouchers MUST remain `validated_collections`

#### Scenario: Close does not rewrite issued receipts

- GIVEN a proposal sheet with a historical `issued` receipt
- WHEN Close runs
- THEN that receipt MUST remain `issued` with its `external_receipt_id`

#### Scenario: Cancel from closed reopens local receipts only

- GIVEN a closed sheet with local `closed` receipts and historical `issued` receipts
- WHEN Cancel runs
- THEN local `closed` receipts MUST be `draft` with no `external_receipt_id`
- AND `issued` receipts MUST remain `issued`
- AND freeze MUST remain until Reinstate

#### Scenario: Reinstate from cancelled to submitted

- GIVEN a cancelled sheet with draft allocations and that seller already has an `open`
  sheet in that company
- WHEN an internal user Reinstates it
- THEN `state` MUST become `submitted`
- AND every allocation MUST remain `draft`
- AND the other `open` sheet MUST remain `open`

#### Scenario: Raw state write rejected

- GIVEN a sheet
- WHEN `state` is written except via Seller Close, Confirm, Close, Cancel, or Reinstate
- THEN the write MUST be rejected

#### Scenario: Cancel from submitted proposal or closed

- GIVEN a submitted sheet with draft allocations, a proposal sheet with draft
  allocations, or a closed sheet with confirmed allocations
- WHEN Cancel runs
- THEN `state` MUST become `cancelled`
- AND every allocation MUST be `draft`

#### Scenario: Confirm from open refused

- GIVEN an open sheet whose every member is `validated_collections`
- WHEN Confirm runs
- THEN MUST refuse and `state` MUST remain `open`

#### Scenario: Submitted cannot return to open

- GIVEN a submitted sheet
- WHEN Open or a raw write of `state` `open` is attempted
- THEN MUST refuse and `state` MUST remain `submitted`

#### Scenario: Cancelled cannot return to open

- GIVEN a cancelled sheet
- WHEN Open or a raw write of `state` `open` is attempted
- THEN MUST refuse
- AND Reinstate MUST write `submitted` not `open`

#### Scenario: Proposal cannot return to submitted

- GIVEN a proposal sheet
- WHEN Seller Close or Reinstate is invoked
- THEN MUST refuse and `state` MUST remain `proposal`

#### Scenario: Illegal transition from open refused

- GIVEN an open sheet
- WHEN Close, Cancel, or Open is invoked
- THEN MUST refuse and `state` MUST remain `open`

#### Scenario: Non-open create rejected

- GIVEN create vals with `state` `submitted`, `proposal`, `closed`, or `cancelled`
- WHEN create runs
- THEN MUST be rejected with no write
