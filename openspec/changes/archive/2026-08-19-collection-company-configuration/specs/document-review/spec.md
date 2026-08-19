# Delta for document-review

## ADDED Requirements

### Requirement: Review snapshots isolated by company

Each Document Review snapshot MUST belong to the same company as its voucher. Users MUST
see snapshots only for companies they are allowed, the same as vouchers. Dedicated
groups MUST NOT be added. Write and unlink of snapshots MUST remain denied.

#### Scenario: Snapshot follows voucher company

- GIVEN a voucher in company A with a snapshot
- WHEN the snapshot is read
- THEN it MUST belong to company A

#### Scenario: Other-company snapshots hidden

- GIVEN a snapshot of a company B voucher and a user not allowed company B
- WHEN they read review history
- THEN that snapshot MUST NOT be visible
- AND its id MUST NOT be disclosed

#### Scenario: Allowed-company history still readable

- GIVEN an internal user allowed company A and snapshots on an A voucher
- WHEN they open Payment Vouchers history
- THEN those snapshots MUST be listed readonly in revision order

## MODIFIED Requirements

### Requirement: Per-company Document Review flag

Each company MUST have a boolean Document Review flag defaulting to OFF. Settings admins
MUST toggle it at `/odoo/settings#collections` under Collection Settings. When ON,
existing Document Review requirements MUST still apply. Voucher `state` and review audit
columns MUST remain on Payment Vouchers views regardless of the flag. Saving other
Collection Settings MUST preserve this flag. The flag MUST still gate review queue and
mutation operations as today.
(Previously: Settings labels were "Settings"; other Collection Settings fields did not
exist.)

#### Scenario: Default off

- GIVEN a fresh install or upgrade
- WHEN the current company's flag is read
- THEN Document Review MUST be OFF

#### Scenario: Settings admin toggle

- GIVEN a Settings administrator
- WHEN they change Document Review at `/odoo/settings#collections`
- THEN the current company's flag MUST persist that value

#### Scenario: Voucher state and audit remain

- GIVEN Document Review is OFF
- WHEN an internal user opens Payment Vouchers views
- THEN voucher `state` and review audit columns MUST still appear

#### Scenario: Flag preserved when Collection Settings are saved

- GIVEN Document Review ON or OFF and other Collection Settings edited
- WHEN Collection Settings are saved
- THEN `document_review_enabled` MUST remain the prior value unless the admin changed
  that flag in the same save

#### Scenario: Flag still gates review when ON or OFF

- GIVEN Document Review OFF
- WHEN an internal user calls `get_review_queue`, `action_review_approve`,
  `action_review_reject`, or `action_review_set_rotation`
- THEN the system MUST refuse (not empty-queue success)
- AND when the flag is ON those operations MUST still run for internal users on an
  allowed-company sheet
