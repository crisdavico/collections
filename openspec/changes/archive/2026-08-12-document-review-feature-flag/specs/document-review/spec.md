# Delta for Document Review

## ADDED Requirements

### Requirement: Per-company Document Review flag

Each company MUST have a boolean Document Review flag defaulting to OFF. Settings
admins MUST toggle it at `/odoo/settings#collections`. When ON, existing Document
Review requirements MUST still apply. Line `state` and review audit columns MUST
remain on payment-line views regardless of the flag.

#### Scenario: Default off

- GIVEN a fresh install or upgrade
- WHEN the current company's flag is read
- THEN Document Review MUST be OFF

#### Scenario: Settings admin toggle

- GIVEN a Settings administrator
- WHEN they change Document Review at `/odoo/settings#collections`
- THEN the current company's flag MUST persist that value

#### Scenario: Line state and audit remain

- GIVEN Document Review is OFF
- WHEN an internal user opens payment-line views
- THEN line `state` and review audit columns MUST still appear

### Requirement: Document Review menu and RPCs when flag is off

When OFF, the Document Review menu MUST NOT appear. Operations `get_review_queue`,
`action_review_approve`, `action_review_reject`, and `action_review_set_rotation`
MUST refuse, including for internal users, and MUST NOT succeed as an empty queue.
Direct `/odoo/document-review` MUST still be refused via those operations. When ON,
only internal users MUST access them.

#### Scenario: Menu hidden when off

- GIVEN Document Review is OFF
- WHEN menus load
- THEN Document Review MUST NOT appear

#### Scenario: Review operations refuse when off

- GIVEN Document Review is OFF
- WHEN an internal user calls `get_review_queue`, `action_review_approve`,
  `action_review_reject`, or `action_review_set_rotation`, including via
  `/odoo/document-review`
- THEN the system MUST refuse (not empty-queue success)

#### Scenario: Internal ACL when on

- GIVEN Document Review is ON
- WHEN a non-internal user attempts those review operations
- THEN the system MUST deny access
