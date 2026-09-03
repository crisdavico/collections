# Delta for collection-vouchers

## MODIFIED Requirements

### Requirement: Voucher allocation membership

Each voucher MAY have `allocation_id`. Write of `allocation_id` MUST be refused unless current and target (if set) are both `draft` or unset. Unlink MUST be allowed when voucher `state` is `draft` and `allocation_id` is unset or `draft`. Unlink MUST be refused when allocation is `confirmed`. Removing a voucher from a draft allocation MUST NOT project voucher amounts onto residual. Residual MUST remain `total_debt − total_applied`. MUST NOT refuse unlink because leftover-voucher residual would be `< 0`. Invoice lines MUST NOT be auto-edited. All three voucher states MAY be allocated.
(Previously: Unlink when `state` is `pending`; projected residual − voucher amount `< 0` refused.)

#### Scenario: allocation_id write on draft or unset

- GIVEN current and target are both `draft` or unset
- WHEN `allocation_id` is written
- THEN the write MUST succeed

#### Scenario: Confirmed membership write refused

- GIVEN current or target is `confirmed`
- WHEN `allocation_id` is written
- THEN MUST refuse and stored `allocation_id` MUST be unchanged

#### Scenario: Pending unlink on draft or unset

- GIVEN a draft voucher with allocation unset or `draft`
- WHEN deleted
- THEN the system MUST allow the delete and MUST NOT refuse because leftover-voucher residual would change

#### Scenario: Draft unlink MUST NOT use leftover-voucher residual

- GIVEN a draft voucher on a draft allocation
- WHEN the voucher is deleted
- THEN unlink MUST succeed, invoice lines MUST NOT be auto-edited, and residual MUST stay debt − applied (MUST NOT ± voucher amount)

### Requirement: Partner write follows allocation

When `partner_id` changes, the system MUST compute `allocation_id` before persist and MUST write `partner_id` and `allocation_id` in the same vals (per record when outcomes differ). MUST NOT `sudo()`. While the sheet is `open`, any voucher state MAY change Customer. Same-value `partner_id` MUST NOT recompute allocation. `confirmed` current allocation MUST refuse the move with no field change. Draft source MUST NOT refuse because residual is 0 or because leftover-voucher residual would be `< 0`. MUST attach the unique draft same-sheet allocation for the new partner without leftover-voucher residual or `residual_reason` checks; otherwise MUST leave unallocated and MUST post chatter for that outcome.
(Previously: Draft source with projected residual − voucher amount `< 0` refused; attach required residual rules including `residual_reason`.)

#### Scenario: Same-write partner and allocation

- GIVEN an open-sheet voucher on draft allocation A (partner P) and unique draft same-sheet allocation B (partner Q)
- WHEN `partner_id` is written to Q
- THEN `partner_id` MUST be Q and `allocation_id` MUST be B in one write

#### Scenario: Fully applied source allowed

- GIVEN an open-sheet voucher on a draft allocation whose residual is 0
- WHEN `partner_id` is written to another customer
- THEN the write MUST succeed and residual MUST NOT ± voucher amount

#### Scenario: Target attaches without leftover residual check

- GIVEN an open-sheet unallocated voucher and unique draft same-sheet allocation for Q
- WHEN `partner_id` is written to Q
- THEN `allocation_id` MUST become that allocation and MUST NOT require leftover-voucher residual or `residual_reason`

#### Scenario: Target left unallocated when no unique draft allocation

- GIVEN an open-sheet voucher and no unique draft same-sheet allocation for Q
- WHEN `partner_id` is written to Q
- THEN `partner_id` MUST be Q, `allocation_id` unset, and chatter MUST record unallocated

#### Scenario: Confirmed source refused

- GIVEN an open-sheet voucher whose `allocation_id` is `confirmed`
- WHEN `partner_id` is written
- THEN MUST refuse and both fields MUST be unchanged

#### Scenario: Approved or rejected voucher may move

- GIVEN an open-sheet voucher in `draft`, `validated_seller`, or `validated_collections` with no confirmed freeze
- WHEN `partner_id` is written to another customer
- THEN the write MUST succeed and `state` MUST stay unchanged

### Requirement: Voucher lifecycle

| Key | Rule |
| --- | --- |
| `draft` | ORM/UI default; only unlinkable; form Validate by Seller source |
| `validated_seller` | MCP stamp; Seller target; Review queue |
| `validated_collections` | Document Review Approve only |

MUST NOT have Reject or `rejected`. Form **Validate by Seller** MUST work only from `draft` and MUST NOT stamp reviewer/time. Validated by Collections MUST be only via Review Approve (no form button). Intercept MUST refuse raw `validated_collections`; `validated_seller` only via Seller action or MCP create. Statusbar MUST NOT be clickable. Unlink only when `state` is `draft` and `allocation_id` unset or `draft`. Draft plus confirmed MUST be refused. Unlink MUST NOT project voucher amounts onto residual and MUST NOT refuse because leftover-voucher residual would be `< 0`. Invoice lines MUST NOT be auto-edited. Validate by Seller MUST remain if Review is OFF. Review RPCs stay in `document-review`.
(Previously: Projected residual `< 0` refused unlink without editing invoice lines.)

#### Scenario: Approve from pending

- GIVEN a `draft` voucher
- WHEN Validate by Seller runs
- THEN `state` MUST be `validated_seller` and reviewer/time MUST NOT be recorded

#### Scenario: Reject from pending

- GIVEN a `draft` voucher
- WHEN Reject is invoked
- THEN Reject MUST NOT exist and `state` MUST stay `draft`

#### Scenario: Terminal states block transitions

- GIVEN `validated_seller` or `validated_collections`
- WHEN Validate by Seller is attempted
- THEN `state` MUST NOT change

#### Scenario: Collections only via Document Review

- GIVEN `validated_seller`
- WHEN a form button or raw write targets `validated_collections`
- THEN MUST refuse; Review Approve MUST be the only path

#### Scenario: Delete from pending

- GIVEN `draft` with allocation unset or `draft`
- WHEN deleted
- THEN the system MUST allow the delete and MUST NOT refuse because leftover-voucher residual would change

#### Scenario: Delete blocked when not pending

- GIVEN `validated_seller` or `validated_collections`
- WHEN deleted
- THEN the system MUST refuse the delete

#### Scenario: Delete pending on confirmed allocation refused

- GIVEN a draft voucher on a confirmed allocation
- WHEN deleted
- THEN MUST refuse and both records MUST remain

#### Scenario: Delete on draft MUST NOT use leftover-voucher residual

- GIVEN a draft voucher on a draft allocation
- WHEN deleted
- THEN unlink MUST succeed, invoice lines MUST NOT be auto-edited, and residual MUST stay debt − applied

#### Scenario: Kanban drag is audited

- GIVEN Payment Vouchers after this change
- WHEN stages kanban or clickable statusbar would write state
- THEN stages kanban MUST NOT exist and statusbar MUST NOT be clickable

#### Scenario: Approve and Reject remain when review is off

- GIVEN Document Review OFF and a `draft` voucher
- WHEN Validate by Seller runs on Payment Vouchers
- THEN `state` MUST become `validated_seller`

#### Scenario: Default pending

- GIVEN a newly created ORM/UI voucher
- WHEN `state` is read without a prior decision
- THEN `state` MUST be `draft`
