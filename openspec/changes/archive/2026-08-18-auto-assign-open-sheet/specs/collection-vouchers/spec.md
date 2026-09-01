# Delta for collection-vouchers

## ADDED Requirements

### Requirement: Create auto-assign to open sheet

On voucher create, when `seller_id` is set and `sheet_id` is omitted, the system MUST
auto-assign: unique open sheet → assign; none → create one open sheet then assign; more
than one open → `UserError` with no write. Null `seller_id` MUST leave the voucher
unassigned. Explicit `sheet_id` MUST be honored when the target is the same seller and
`open`; assign to a closed sheet MUST fail. Write of `seller_id` on an existing voucher
MUST NOT auto-assign. The system MUST NOT backfill existing unassigned vouchers.

#### Scenario: UI or ORM create with seller assigns

- GIVEN a seller with exactly one open sheet
- WHEN a voucher is created with that `seller_id` and omitted `sheet_id`
- THEN the voucher MUST be assigned to that open sheet

#### Scenario: Create without seller stays unassigned

- GIVEN a voucher create with null `seller_id` and omitted `sheet_id`
- WHEN create completes
- THEN the voucher MUST persist unassigned

#### Scenario: Explicit sheet_id honored when open

- GIVEN an open same-seller sheet
- WHEN a voucher is created with that `seller_id` and explicit `sheet_id`
- THEN the voucher MUST be assigned to that sheet

#### Scenario: Assign to closed sheet fails

- GIVEN a closed same-seller sheet
- WHEN a voucher is created or written with that `sheet_id`
- THEN the write MUST fail

#### Scenario: Later seller write does not auto-assign

- GIVEN an existing unassigned voucher
- WHEN `seller_id` is written
- THEN `sheet_id` MUST remain empty

#### Scenario: No open sheet creates then assigns

- GIVEN a seller with zero open sheets
- WHEN a voucher is created with that `seller_id` and omitted `sheet_id`
- THEN one open sheet MUST be created for that seller
- AND the voucher MUST be assigned to it

#### Scenario: More than one open rejects create

- GIVEN a seller with more than one open sheet
- WHEN a voucher is created with that `seller_id` and omitted `sheet_id`
- THEN create MUST raise `UserError` with no voucher written

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
All-new create MUST auto-assign sheets via the same ORM create rules as UI voucher
create (`seller_id` set, `sheet_id` omitted). Exact replay MUST NOT attach, move, or
clear sheets (including leftover unassigned). The tool MUST NOT accept `sheet_id` in the
payload and MUST NOT return `sheet_id`. Response MUST include each voucher
`id`/`name`/`state` and `document_id` (`state` is voucher state). Idempotency by
`document_id`: all-new → create N vouchers; every submitted `document_id` already exists
→ return ALL those vouchers unchanged; in-call duplicate or partial overlap → reject
with no writes. Submitted `document_id`s that already exist on different vouchers MUST
succeed as exact replay (MUST NOT reject as a cross-voucher conflict). Exact replay MUST
ignore `customer_identification`, nested attachments, and `seller_id`, and MUST NOT
mutate matching vouchers (including legacy null `seller_id` and `sheet_id`). Attachment
atomicity and `document_id` uniqueness rules remain unchanged. (Previously: All-new
stamped `seller_id` but did not assign sheets; exact replay ignored customer,
attachments, and `seller_id` with no sheet attach or move.)

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

#### Scenario: All-new with unique open assigns the batch

- GIVEN unused `document_id`s, a valid `seller_id`, and that seller has exactly one open
  sheet
- WHEN `create_collection_vouchers` runs
- THEN every created voucher MUST be assigned to that sheet
- AND response MUST include each voucher `id`/`name`/`state` and `document_id`
- AND MUST NOT include `sheet_id`

#### Scenario: All-new with no open creates one open sheet and assigns all

- GIVEN unused `document_id`s, a valid `seller_id`, and that seller has zero open sheets
- WHEN `create_collection_vouchers` runs
- THEN one open sheet MUST be created
- AND every created voucher MUST be assigned to it

#### Scenario: All-new with more than one open rejected

- GIVEN unused `document_id`s, a valid `seller_id`, and that seller has more than one
  open sheet
- WHEN `create_collection_vouchers` runs
- THEN the call MUST raise `UserError` with no vouchers written

#### Scenario: Exact replay does not change sheet_id

- GIVEN every submitted `document_id` already exists, including leftover unassigned
  vouchers
- WHEN the payload is retried
- THEN each matching voucher’s `sheet_id` MUST be unchanged
- AND no sheet MUST be created or attached
