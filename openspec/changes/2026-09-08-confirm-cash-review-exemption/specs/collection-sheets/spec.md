# Delta for Collection Sheets

## MODIFIED Requirements

### Requirement: Confirm review gate

Confirm MUST run only from `submitted`. The system MUST raise `UserError` and MUST NOT
change sheet or allocation `state` unless every member voucher has `state`
`validated_collections`, and the `UserError` MUST name the offending vouchers. Members
whose `document_type` is in `CONFIRM_REVIEW_EXEMPT_TYPES` (today `cash` only) carry no
designated proof, so Document Review can never reach them: `validated_seller` MUST be
enough for those, while `draft` MUST still block. `seller_deposit` MUST NOT be exempt
and MUST reach `validated_collections`. An empty member set MUST pass. Missing
designated proof, Document Review OFF, or any non-exempt member not
`validated_collections` MUST block Confirm. Confirm MUST set the sheet to `proposal` and
MUST NOT confirm allocations. (Previously: every member, `cash` included, had to be
`validated_collections`; the error did not name offenders. Before that: Confirm ran only
from `open`.)

#### Scenario: All members validated_collections

- GIVEN a submitted sheet whose every member is `validated_collections`
- WHEN Confirm runs
- THEN `state` MUST become `proposal`
- AND every allocation MUST remain `draft`

#### Scenario: Empty members pass Confirm

- GIVEN a submitted sheet with no member vouchers
- WHEN Confirm runs
- THEN `state` MUST become `proposal`

#### Scenario: Unreviewed member blocks Confirm

- GIVEN a submitted sheet with at least one non-exempt member not
  `validated_collections`
- WHEN Confirm runs
- THEN MUST raise `UserError` and `state` MUST remain `submitted`
- AND the message MUST name that voucher

#### Scenario: Seller-validated cash member passes Confirm

- GIVEN a submitted sheet whose only member is a `cash` voucher in `validated_seller`
- AND `cash_declared_at` is set
- WHEN Confirm runs
- THEN `state` MUST become `proposal`
- AND the cash voucher MUST stay `validated_seller`

#### Scenario: Draft cash member blocks Confirm

- GIVEN a submitted sheet with a `draft` `cash` member
- WHEN Confirm runs
- THEN MUST raise `UserError` and `state` MUST remain `submitted`

#### Scenario: Seller-validated seller_deposit member blocks Confirm

- GIVEN a submitted sheet with a `seller_deposit` member in `validated_seller`
- WHEN Confirm runs
- THEN MUST raise `UserError` and `state` MUST remain `submitted`
