# Delta for collection-vouchers

## ADDED Requirements

### Requirement: Voucher seller field

Each `collection.voucher` MUST support nullable `seller_id` targeting an internal user
(not portal/share). The system MUST NOT backfill existing rows. ORM/RPC creates without
seller MUST remain allowed. New Payment Vouchers form creates MUST require `seller_id`.
List, form, and search MUST expose `seller_id`.

#### Scenario: Legacy null remains valid

- GIVEN an existing voucher with null `seller_id`
- WHEN loaded or saved without assigning a sheet
- THEN the voucher MUST persist with null seller

#### Scenario: ORM create without seller

- GIVEN an internal user creates a voucher via ORM without `seller_id`
- WHEN create completes
- THEN the voucher MUST persist with null seller

#### Scenario: Form create requires seller

- GIVEN a new Payment Vouchers form
- WHEN saved without `seller_id`
- THEN the system MUST reject the save

#### Scenario: Seller visible on list form search

- GIVEN an existing voucher with or without seller
- WHEN list, form, or search is opened
- THEN `seller_id` MUST be visible

## MODIFIED Requirements

### Requirement: MCP tool create_collection_vouchers

The system MUST expose `create_collection_vouchers` via `@mcp_tool` on `muk_mcp.mixin`
(`category=write`, `registry=mcp`), method-discovered — MUST NOT use a DB `muk_mcp.tool`
record. Calls MUST use the authenticated user (MUST NOT `sudo()`); voucher ACL MUST
apply. Input MUST require `customer_identification`, non-empty `payments`, and top-level
`seller_id`; MUST NOT accept `received_date`. `seller_id` MUST identify an existing
internal user; missing, portal/share, or unknown ids MUST be rejected with no writes.
Each MCP payment MUST include non-empty `document_id` and existing payment fields
(`document_type` required). Create MUST persist one voucher per payment atomically
(`state=pending`, company currency) and MUST stamp `seller_id` only on all-new create.
Response MUST include each voucher `id`/`name`/`state` and `document_id`. Idempotency by
`document_id`: all-new → create N vouchers; every submitted `document_id` already exists
→ return ALL those vouchers unchanged; in-call duplicate or partial overlap → reject
with no writes. Submitted `document_id`s that already exist on different vouchers MUST
succeed as exact replay (MUST NOT reject as a cross-voucher conflict). Exact replay MUST
ignore `customer_identification`, nested attachments, and `seller_id`, and MUST NOT
mutate matching vouchers (including legacy null `seller_id`). Attachment atomicity and
`document_id` uniqueness rules remain unchanged. (Previously: Input required only
`customer_identification` and payments; no `seller_id`; exact replay ignored customer
and attachments only.)

#### Scenario: All-new create

- GIVEN an internal user, unused payment `document_id`s, and a valid internal
  `seller_id`
- WHEN `create_collection_vouchers` runs with valid customer, payments, and `seller_id`
- THEN one voucher per payment MUST be created atomically with that `seller_id`
- AND response MUST include each voucher `id`/`name`/`state` and `document_id`

#### Scenario: Exact-retry returns all vouchers

- GIVEN every submitted `document_id` already exists, including legacy null `seller_id`
- WHEN the same payload is retried with any `seller_id`
- THEN all matching vouchers MUST return unchanged with no new rows
- AND customer identification, nested attachments, and `seller_id` MUST be ignored
- AND matching vouchers MUST NOT be mutated

#### Scenario: Duplicate document_id in call

- GIVEN two payments in one call share a `document_id`
- WHEN `create_collection_vouchers` runs
- THEN the call MUST be rejected with no writes

#### Scenario: Partial-conflict

- GIVEN some submitted `document_id`s exist and others do not
- WHEN `create_collection_vouchers` runs
- THEN the call MUST be rejected with no writes

#### Scenario: Existing document_ids on different vouchers succeed

- GIVEN submitted `document_id`s already exist on more than one voucher
- WHEN `create_collection_vouchers` runs
- THEN the call MUST succeed as exact replay
- AND response MUST include all those vouchers

#### Scenario: ACL denial for non-permitted user

- GIVEN a caller without voucher create rights
- WHEN `create_collection_vouchers` runs
- THEN access MUST be denied with no writes

#### Scenario: Missing or invalid seller_id rejected

- GIVEN a payload missing `seller_id`, or with a portal/share or unknown user
- WHEN `create_collection_vouchers` runs
- THEN the call MUST be rejected with no writes
