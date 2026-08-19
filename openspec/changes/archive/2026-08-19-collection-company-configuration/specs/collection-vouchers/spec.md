# Delta for collection-vouchers

## ADDED Requirements

### Requirement: Collection Settings persistence

Each company MUST persist Collection Settings: enabled sellers, `auto_create_sheet`
(default ON), and allowed document types (transfer, check, cash deposit, Unsupported).
Settings action and menu labels MUST be **Collection Settings**. An empty enabled-seller
list MUST mean none for NEW work. All four types MUST start enabled. Unsupported MUST
remain independently configurable. Saving these fields MUST NOT clear
`document_review_enabled`.

#### Scenario: Collection Settings labels

- GIVEN the module is installed
- WHEN an internal Settings admin opens Collections settings
- THEN the action and menu labels MUST be Collection Settings

#### Scenario: Empty enabled sellers means none for new work

- GIVEN a company with no enabled sellers
- WHEN a new voucher is created via UI, ORM, import, or MCP
- THEN the create MUST be rejected with no write

#### Scenario: Defaults enable auto-create and all four types

- GIVEN a fresh install or a company with no prior Collection Settings
- WHEN settings are read
- THEN `auto_create_sheet` MUST be ON
- AND transfer, check, cash deposit, and Unsupported MUST all be enabled

#### Scenario: Unsupported is configurable

- GIVEN Unsupported is disabled for the company
- WHEN a new voucher is created with `document_type` `unsupported`
- THEN the create MUST be rejected
- AND existing `unsupported` vouchers MUST remain visible

### Requirement: Company ownership of vouchers

Every voucher MUST have a required company. Users MUST see and operate only vouchers of
companies they are allowed. Dedicated groups MUST NOT be added.

#### Scenario: Company required on create

- GIVEN a new voucher
- WHEN saved
- THEN it MUST belong to a company
- AND that company MUST be one the user is allowed

#### Scenario: Other-company vouchers hidden

- GIVEN a voucher in a company the user is not allowed
- WHEN they search or open Payment Vouchers
- THEN that voucher MUST NOT be visible
- AND they MUST NOT read its id or name

### Requirement: Enabled seller and allowed type on new voucher work

NEW voucher create (UI, ORM, import, MCP) MUST require an enabled seller for that
company and an allowed `document_type`. Writes of `seller_id` or `document_type` on a
voucher MUST pass the same gates. Exact same-company MCP replay is exempt (see MCP).

#### Scenario: ORM and import create require an enabled seller

- GIVEN a seller not on the company's enabled list
- WHEN a voucher is created via ORM or import with that seller
- THEN the create MUST be rejected with no write

#### Scenario: UI create offers only enabled sellers and allowed types

- GIVEN a company with a non-empty enabled-seller list and a subset of types enabled
- WHEN an internal user opens a new Payment Vouchers form
- THEN seller choices MUST be those enabled sellers
- AND type choices MUST be those allowed types

#### Scenario: Disallowed type rejected on new work

- GIVEN a type disabled for the company
- WHEN a new voucher is created or `document_type` is written to that type
- THEN the write MUST be rejected

#### Scenario: Seller write to a disabled seller rejected

- GIVEN an existing voucher and a seller not enabled for its company
- WHEN `seller_id` is written to that seller
- THEN the write MUST be rejected
- AND the stored seller MUST be unchanged

### Requirement: Historical vouchers remain operable

Existing vouchers MUST stay visible and operable if their seller is later disabled. The
system MUST NOT hide or delete them for that reason.

#### Scenario: Disabled-seller voucher stays visible

- GIVEN a voucher whose seller is later removed from the enabled list
- WHEN an allowed-company user opens Payment Vouchers
- THEN that voucher MUST still be listed

#### Scenario: Disabled-seller voucher remains operable

- GIVEN a `pending` voucher whose seller is later disabled
- WHEN Approve or Reject runs without changing seller or type
- THEN the decision MUST persist
- AND the voucher MUST NOT be deleted

### Requirement: Cross-company document_id reject not replay

`document_id` uniqueness MUST remain global among non-null values. When a new write
collides with another company's `document_id`, the system MUST reject it (MUST NOT
replay) and MUST NOT disclose that voucher's id or name. A user who can read both
companies MUST NOT receive the other company's voucher as an MCP replay.

#### Scenario: Global uniqueness still holds

- GIVEN a non-null `document_id` already stored
- WHEN another voucher is saved with the same `document_id` in any company
- THEN the save MUST be rejected

#### Scenario: Other-company collision undisclosed

- GIVEN `document_id` D exists only on a company B voucher
- WHEN company A creates via UI, ORM, import, or MCP with D
- THEN the operation MUST fail with a generic error
- AND the response MUST NOT include company B's voucher id or name

#### Scenario: Multi-company reader must not replay the other company

- GIVEN a user allowed to read companies A and B, and D exists only on B
- WHEN they call `create_collection_vouchers` in company A with D
- THEN the call MUST be rejected with no writes
- AND MUST NOT return B's voucher as replay

### Requirement: Upgrade stamps voucher company and seeds settings

On upgrade the system MUST: stamp each voucher's company from its sheet when set,
otherwise from the seller's company or the database default company; repair voucher and
sheet company so a member matches its sheet; seed each company's enabled sellers from
sellers used on that company's vouchers and sheets; enable all four document types;
convert sequences so each company has its own voucher numbering and no company-less
sequence steals numbers. The system MUST NOT hide or delete historical vouchers.

#### Scenario: Voucher company from sheet then seller or default

- GIVEN a voucher with a sheet company, and another with no sheet and a seller company
- WHEN upgrade runs
- THEN the first MUST take the sheet company
- AND the second MUST take the seller company or the default company when the seller
  has none

#### Scenario: Repair voucher and sheet company consistency

- GIVEN a member voucher whose company differs from its sheet
- WHEN upgrade runs
- THEN the voucher company MUST match the sheet company

#### Scenario: Seed sellers and enable four types

- GIVEN historical vouchers and sheets with sellers
- WHEN upgrade runs
- THEN those sellers MUST be enabled for their stamped company
- AND all four document types MUST be enabled

#### Scenario: Per-company voucher sequences without a company-less thief

- GIVEN a former company-less voucher sequence
- WHEN upgrade runs and two companies then create vouchers
- THEN each company MUST receive isolated `COL/<year>/<number>` names
- AND a company-less sequence MUST NOT consume either company's numbers

## MODIFIED Requirements

### Requirement: Voucher sequence naming

The system MUST assign each new voucher a unique persisted name matching
`COL/<year>/<number>` via sequence code `collection.voucher`. Numbering MUST be isolated
per company. Each payment MUST consume one sequence number of that voucher's company.
(Previously: One global sequence numbered all companies together.)

#### Scenario: Sequence assigned on create

- GIVEN an internal user creates a voucher
- WHEN saved the first time
- THEN name MUST match `COL/<current-year>/<number>` and be unique

#### Scenario: Numbers isolated per company

- GIVEN companies A and B each create a new voucher
- WHEN both saves complete
- THEN each company's names MUST number independently of the other

### Requirement: Authorization for internal users

Internal users (`base.group_user`) MUST have full CRUD on vouchers of companies they
are allowed. The system MUST NOT grant ACL on `collection.voucher.line`. Dedicated
groups MUST NOT be added. Allowed-company record rules MUST hide other companies.
(Previously: No record rules; vouchers were company-blind.)

#### Scenario: Internal user CRUD

- GIVEN an authenticated internal user
- WHEN they CRUD a voucher of an allowed company
- THEN ACL MUST allow the operation

#### Scenario: Non-internal user denied

- GIVEN a user without internal-user privileges
- WHEN they attempt voucher CRUD
- THEN the system MUST deny access

### Requirement: Payment document_id uniqueness

Vouchers MUST support nullable Char `document_id` unique among non-null values across
all companies. UI vouchers without `document_id` MUST remain allowed. MCP MUST require
non-empty `document_id` per payment.
(Previously: Global uniqueness with no cross-company replay rule; that reject-not-replay
behavior is now specified under Cross-company document_id reject not replay.)

#### Scenario: Manual payment without document_id still OK

- GIVEN a user saving a UI voucher without `document_id`
- WHEN saved
- THEN the voucher MUST persist

### Requirement: MCP optional payment attachment on create

`create_collection_vouchers` MAY accept one optional nested attachment per payment with
required `name`, `mimetype`, and base64 `datas` when present. Declared `mimetype` MUST
match content detection (`image/*` or PDF only); mismatch or bad base64 MUST raise
`UserError` with no writes. Create with attachments MUST persist all vouchers and files
atomically under a savepoint by posting each nest onto the new voucher chatter via
`message_post` (MUST NOT write Binary `attachment`). Exact same-company retry by
`document_id` MUST return all matching vouchers and MUST NOT add, replace, or compare
attachments (even when a voucher has none). All-new and conflict rules MUST remain
unchanged except as this change specifies for company, seller, and type gates.
(Previously: Exact-retry matched any company.)

#### Scenario: MCP create with nested attachment

- GIVEN unused `document_id`s and a payment with valid nested attachment
- WHEN `create_collection_vouchers` runs
- THEN vouchers and the nested file MUST persist atomically under a savepoint
- AND the file MUST appear on that voucher's chatter as designated proof

#### Scenario: MCP attachment MIME mismatch rejected

- GIVEN nested attachment with mismatched or non-image/non-PDF `mimetype`
- WHEN `create_collection_vouchers` runs
- THEN MUST raise `UserError` with no writes

#### Scenario: Exact-retry skips attachment writes

- GIVEN every submitted `document_id` already exists in the same company
- WHEN retried with or without nested attachments
- THEN all matching vouchers return unchanged; attachments MUST NOT be
  written/replaced/compared

### Requirement: MCP tool create_collection_vouchers

The system MUST expose `create_collection_vouchers` via `@mcp_tool` on `muk_mcp.mixin`
(`category=write`, `registry=mcp`), method-discovered — MUST NOT use a DB `muk_mcp.tool`
record. Calls MUST use the authenticated user (MUST NOT `sudo()`); voucher ACL and
allowed-company rules MUST apply. Input MUST require `customer_identification`,
non-empty `payments`, and top-level `seller_id`; MUST NOT accept `received_date`.
`seller_id` MUST identify an existing internal user; missing, portal/share, or unknown
ids MUST be rejected with no writes. All-new create MUST also require that seller
enabled for the voucher company and each payment `document_type` allowed. Each MCP
payment MUST include non-empty `document_id` and existing payment fields
(`document_type` required). Create MUST persist one voucher per payment atomically
(`state=pending`, company currency) and MUST stamp `seller_id` only on all-new create.
All-new create MUST follow the same ORM sheet rules as UI voucher create (`seller_id`
set, `sheet_id` omitted), including `auto_create_sheet`. Exact same-company replay MUST
skip enabled-seller and allowed-type gates, MUST NOT attach, move, or clear sheets
(including leftover unassigned), and MUST ignore `customer_identification`, nested
attachments, provenance nests, and `seller_id`. The tool MUST NOT accept `sheet_id` in
the payload and MUST NOT return `sheet_id`. Response MUST include each voucher
`id`/`name`/`state` and `document_id` (`state` is voucher state). Idempotency by
`document_id` is per the current company: all-new in that company → create N vouchers;
every submitted `document_id` already exists on that company → return ALL those vouchers
unchanged; in-call duplicate or partial overlap in that company → reject with no writes.
Submitted `document_id`s that already exist on different vouchers of that company MUST
succeed as exact replay. A hit only in another company MUST reject, not replay, with no
ids or names disclosed.
(Previously: Replay was global; all-new did not gate enabled seller or type;
auto-assign always ran.)

#### Scenario: All-new create

- GIVEN an internal user, unused payment `document_id`s, a valid enabled internal
  `seller_id`, and allowed types
- WHEN `create_collection_vouchers` runs with valid customer, payments, and `seller_id`
- THEN one voucher per payment MUST be created atomically with that `seller_id`
- AND response MUST include each voucher `id`/`name`/`state` and `document_id`

#### Scenario: Exact-retry returns all vouchers

- GIVEN every submitted `document_id` already exists in the same company, including
  legacy null `seller_id` or a now-disabled seller
- WHEN the same payload is retried with any `seller_id` or a now-disallowed type
- THEN all matching vouchers MUST return unchanged with no new rows
- AND customer identification, nested attachments, `seller_id`, and type gates MUST be
  skipped
- AND matching vouchers MUST NOT be mutated

#### Scenario: Duplicate document_id in call

- GIVEN two payments in one call share a `document_id`
- WHEN `create_collection_vouchers` runs
- THEN the call MUST be rejected with no writes

#### Scenario: Partial-conflict

- GIVEN some submitted `document_id`s exist in the current company and others do not
- WHEN `create_collection_vouchers` runs
- THEN the call MUST be rejected with no writes

#### Scenario: Existing document_ids on different vouchers succeed

- GIVEN submitted `document_id`s already exist on more than one voucher of the current
  company
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

- GIVEN unused `document_id`s, a valid enabled `seller_id`, `auto_create_sheet` ON, and
  that seller has exactly one open sheet in that company
- WHEN `create_collection_vouchers` runs
- THEN every created voucher MUST be assigned to that sheet
- AND response MUST include each voucher `id`/`name`/`state` and `document_id`
- AND MUST NOT include `sheet_id`

#### Scenario: All-new with no open creates one open sheet and assigns all

- GIVEN unused `document_id`s, a valid enabled `seller_id`, `auto_create_sheet` ON, and
  that seller has zero open sheets in that company
- WHEN `create_collection_vouchers` runs
- THEN one open sheet MUST be created
- AND every created voucher MUST be assigned to it

#### Scenario: All-new with more than one open rejected

- GIVEN unused `document_id`s, a valid enabled `seller_id`, `auto_create_sheet` ON, and
  that seller has more than one open sheet in that company
- WHEN `create_collection_vouchers` runs
- THEN the call MUST raise `UserError` with no vouchers written

#### Scenario: Exact replay does not change sheet_id

- GIVEN every submitted `document_id` already exists in the same company, including
  leftover unassigned vouchers
- WHEN the payload is retried
- THEN each matching voucher’s `sheet_id` MUST be unchanged
- AND no sheet MUST be created, attached, or mutated

#### Scenario: All-new empty or disabled seller rejected

- GIVEN unused `document_id`s and a seller missing from the company's enabled list
  (including an empty list)
- WHEN `create_collection_vouchers` runs
- THEN the call MUST be rejected with no writes

#### Scenario: All-new disallowed type rejected

- GIVEN unused `document_id`s, an enabled seller, and a disabled `document_type`
- WHEN `create_collection_vouchers` runs
- THEN the call MUST be rejected with no writes

#### Scenario: All-new with auto_create_sheet off stays unassigned

- GIVEN unused `document_id`s, an enabled seller, `auto_create_sheet` OFF, omitted
  `sheet_id`, and zero or one open sheet for that seller in that company
- WHEN `create_collection_vouchers` runs
- THEN vouchers MUST be created with no `sheet_id`
- AND no sheet MUST be created or attached

### Requirement: Voucher seller field

Each `collection.voucher` MUST support `seller_id` targeting an internal user (not
portal/share). NEW create via UI, ORM, import, or MCP MUST require `seller_id`. The
system MUST NOT backfill existing null rows. List, form, and search MUST expose
`seller_id`.
(Previously: ORM/RPC creates without seller remained allowed.)

#### Scenario: Legacy null remains valid

- GIVEN an existing voucher with null `seller_id`
- WHEN loaded or saved without assigning a sheet
- THEN the voucher MUST persist with null seller

#### Scenario: ORM create without seller

- GIVEN an internal user creates a voucher via ORM without `seller_id`
- WHEN create runs
- THEN the create MUST be rejected with no write

#### Scenario: Form create requires seller

- GIVEN a new Payment Vouchers form
- WHEN saved without `seller_id`
- THEN the system MUST reject the save

#### Scenario: Seller visible on list form search

- GIVEN an existing voucher with or without seller
- WHEN list, form, or search is opened
- THEN `seller_id` MUST be visible

### Requirement: Create auto-assign to open sheet

On voucher create, when `auto_create_sheet` is ON, `seller_id` is set, and `sheet_id` is
omitted, the system MUST auto-assign within that voucher's company: unique open sheet
for that company and seller → assign; none → create one open sheet then assign; more
than one open in that company → `UserError` with no write. When `auto_create_sheet` is
OFF, create MUST skip automatic create AND assign (voucher stays unassigned unless
`sheet_id` is explicit). Explicit `sheet_id` MUST be honored when the target is the same
company, same seller, and `open`; assign to a closed sheet MUST fail. Write of
`seller_id` on an existing voucher MUST NOT auto-assign. The system MUST NOT backfill
existing unassigned vouchers. List Action and explicit sheet create remain available
when auto-create is OFF (see collection-sheets).
(Previously: Auto-assign always ran; one-open was per seller across all companies.)

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

### Requirement: Immutable review snapshots and ACL

The system MUST store immutable Document Review snapshots (revision, reviewer, time,
decision, and current payment fields). Internal users MUST read history of snapshots
for companies they are allowed and MUST NOT write or unlink snapshots, add dedicated
groups, or sudo. Snapshots MUST follow the same company isolation as vouchers. Form
Approve and Reject MUST NOT append snapshots.
(Previously: No record rules on snapshots.)

#### Scenario: Internal users read history without client mutation

- GIVEN an internal user and existing snapshots of an allowed-company voucher
- WHEN they read voucher history
- THEN ACL MUST allow read
- AND client write or unlink of snapshots MUST be denied

#### Scenario: Form Approve and Reject do not snapshot

- GIVEN a pending voucher on Payment Vouchers
- WHEN form Approve or Reject runs
- THEN voucher state MUST change as today
- AND no snapshot MUST be appended

### Requirement: MCP nested provenance on all-new create

`create_collection_vouchers` MAY accept nested `raw_ocr` and `seller_confirmed` with
the same typed keys as current fields. When both nests are present, seller-confirmed
MUST equal top-level fields; current MUST initialize from seller-confirmed; raw MUST
persist as submitted. Omitting both nests MUST leave empty provenance; UI/ORM create
MUST remain allowed. Malformed, one-sided, or mismatched nests MUST fail the batch
with no writes. Exact same-company replay MUST ignore those nests with no provenance
mutation.
(Previously: Exact replay matched any company.)

#### Scenario: Unchanged seller confirmation

- GIVEN unused `document_id`s and both nests equal to top-level payment fields
- WHEN all-new create runs
- THEN raw, seller-confirmed, and current MUST be equal

#### Scenario: Seller correction

- GIVEN raw nest differs from seller-confirmed, and seller-confirmed equals top-level
- WHEN all-new create runs
- THEN raw MUST persist unchanged
- AND seller-confirmed and current MUST contain the correction

#### Scenario: Both nests omitted leave empty provenance

- GIVEN UI or MCP create with neither `raw_ocr` nor `seller_confirmed`
- WHEN create completes
- THEN raw and seller-confirmed MUST be empty
- AND current payment fields MUST persist as submitted

#### Scenario: Bad provenance fails the batch

- GIVEN a payment with one-sided, malformed, or mismatched nests
- WHEN `create_collection_vouchers` runs
- THEN the call MUST fail with no writes

#### Scenario: Exact replay ignores provenance nests

- GIVEN every submitted `document_id` already exists in the same company, with or
  without stored provenance
- WHEN retried with different or omitted nests
- THEN matching vouchers MUST return unchanged
- AND provenance and snapshots MUST NOT be written, backfilled, or mutated
