# collection-vouchers Specification

## Purpose

Manual vouchers: sequence, pending→approved/rejected, chatter/activities, one voucher
per payment. No WhatsApp/API/agent.

## Requirements

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

### Requirement: Mail thread and activities

Each voucher MUST support messaging and activities. MUST track `state`, `seller_id`, `sheet_id`, `document_type`, and `amount` in chatter.
(Previously: `state` SHOULD be tracked; seller/sheet/type/amount were untracked.)

#### Scenario: Chatter and activities available

- GIVEN an open voucher form
- WHEN a message is posted or an activity scheduled
- THEN it MUST persist on that voucher

#### Scenario: State change tracked

- GIVEN a `draft` voucher
- WHEN Validate by Seller runs
- THEN chatter MUST record the state change

### Requirement: Authorization for internal users

Internal users (`base.group_user`) MUST have full CRUD on vouchers of companies they are
allowed. The system MUST NOT grant ACL on `collection.voucher.line`. Dedicated groups
MUST NOT be added. Allowed-company record rules MUST hide other companies. (Previously:
No record rules; vouchers were company-blind.)

#### Scenario: Internal user CRUD

- GIVEN an authenticated internal user
- WHEN they CRUD a voucher of an allowed company
- THEN ACL MUST allow the operation

#### Scenario: Non-internal user denied

- GIVEN a user without internal-user privileges
- WHEN they attempt voucher CRUD
- THEN the system MUST deny access

### Requirement: Deferred integrations not required

Completeness MUST NOT require HTTP API, WhatsApp metadata, or agent calls. Each voucher MUST require a `res.partner` Customer (`partner_id`). Optional per-voucher image/PDF attachments are an allowed capability and MUST NOT be required for completeness of unrelated voucher features.
(Previously: Completeness scenario named approve or reject.)

#### Scenario: Completeness without deferred features

- GIVEN backend-only voucher management
- WHEN operators create, edit, or Validate by Seller
- THEN success MUST NOT depend on deferred integrations
- AND success MUST NOT require that vouchers have attachments

### Requirement: Payment document_id uniqueness

Vouchers MUST support nullable Char `document_id` unique among non-null values across
all companies. UI vouchers without `document_id` MUST remain allowed. MCP MUST require
non-empty `document_id` per payment. (Previously: Global uniqueness with no
cross-company replay rule; that reject-not-replay behavior is now specified under
Cross-company document_id reject not replay.)

#### Scenario: Manual payment without document_id still OK

- GIVEN a user saving a UI voucher without `document_id`
- WHEN saved
- THEN the voucher MUST persist

### Requirement: MCP optional payment attachment on create

`create_collection_allocation` MAY accept one optional nested attachment per
payment with required `name`, `mimetype`, and base64 `datas` when present.
Declared `mimetype` MUST match content detection (`image/*` or PDF only);
mismatch or bad base64 MUST raise `UserError` with no writes. Create with
attachments MUST persist all vouchers and files atomically under a savepoint
by posting each nest onto the new voucher chatter via `message_post` (MUST
NOT write Binary `attachment`). Exact same-company `document_id` reuse MUST
NOT add, replace, or compare attachments (even when a voucher has none) and
MUST continue to allocation. All-new and conflict rules MUST remain unchanged
except as this change specifies for company, seller, and type gates.
(Previously: Nested attachments were accepted by MCP `create_collection_vouchers`.)

#### Scenario: MCP create with nested attachment

- GIVEN unused `document_id`s and a payment with valid nested attachment
- WHEN `create_collection_allocation` runs
- THEN vouchers and the nested file MUST persist atomically under a savepoint
- AND the file MUST appear on that voucher's chatter as designated proof

#### Scenario: MCP attachment MIME mismatch rejected

- GIVEN nested attachment with mismatched or non-image/non-PDF `mimetype`
- WHEN `create_collection_allocation` runs
- THEN MUST raise `UserError` with no writes

#### Scenario: Exact-retry skips attachment writes

- GIVEN every submitted `document_id` already exists in the same company
- WHEN retried with or without nested attachments
- THEN matching vouchers MUST be unchanged; attachments MUST NOT be
  written/replaced/compared
- AND the write MUST continue to allocation

### Requirement: Concurrent and stale review attempts

Approve MUST refuse stale or concurrent attempts when the voucher is ineligible (not `validated_seller`, or designated proof absent) and MUST NOT corrupt state. Reject MUST NOT exist.
(Previously: Eligibility was not `pending`; approve or reject.)

#### Scenario: Concurrent or stale review attempt

- GIVEN a voucher already decided or ineligible (not `validated_seller`, or proof absent)
- WHEN approve is attempted again
- THEN MUST refuse and MUST NOT alter decided state

### Requirement: Attachment replacement resets review to pending

Replacing designated proof (`message_main_attachment_id` to a different attachment) MUST set `state` to `validated_seller` and MUST clear reviewer/time. Extra chatter files that do not change designated proof MUST NOT reset review, audit, or rotation. Clearing proof MUST reset rotation to 0 and MUST NOT reopen a decided voucher. Omit/empty and MIME rules unchanged.
(Previously: Replacement reset `state` to `pending` from `approved`/`rejected`.)

#### Scenario: Attachment replacement resets voucher state

- GIVEN `validated_seller` or `validated_collections` with designated proof
- WHEN designated proof changes to a different valid file
- THEN `state` MUST be `validated_seller` and reviewer/time MUST clear

#### Scenario: Extra chatter files do not reset review

- GIVEN designated proof in `validated_seller` or `validated_collections`
- WHEN an extra chatter file is added without changing designated proof
- THEN `state` and reviewer/time MUST stay unchanged

#### Scenario: Clearing proof does not reopen

- GIVEN `validated_seller` or `validated_collections` with designated proof
- WHEN proof is cleared with no replacement
- THEN `state` MUST stay decided and rotation MUST be 0

### Requirement: Voucher fields and defaults

Each `collection.voucher` MUST represent one payment. MUST require `partner_id` (label Customer; tracking; index; `ondelete` restrict). MUST NOT store `customer_identification` or `received_date`. Registration time MUST be automatic ORM `create_date` (readonly; MUST NOT be overridable). ORM/UI create MUST default `state` to `draft`. MCP `_collection_create_vouchers` MUST stamp `validated_seller`. Currency MUST be company default. Upgrade MUST NOT backfill `partner_id`.
(Previously: Create defaulted `state` to `pending` for ORM/UI and MCP.)

#### Scenario: Defaults on create

- GIVEN a new voucher saved without overriding defaults
- WHEN create completes
- THEN `state` MUST be `draft`, `create_date` automatic, company currency, and no `received_date`

#### Scenario: MCP create stamps validated_seller

- GIVEN `_collection_create_vouchers` on all-new fused create
- WHEN persist completes
- THEN each new voucher `state` MUST be `validated_seller`

#### Scenario: Required fields

- GIVEN a voucher missing `partner_id`
- WHEN saved
- THEN the system MUST reject the save

#### Scenario: create_date not overridable

- GIVEN create vals with custom creation time or `received_date`
- WHEN create runs via UI or MCP
- THEN creation time MUST NOT be caller-overridable and `received_date` MUST NOT persist

#### Scenario: Char customer_identification gone

- GIVEN the voucher model after this change
- WHEN fields are inspected
- THEN `customer_identification` MUST NOT exist and `partner_id` MUST be required

### Requirement: Voucher lifecycle

| Key | Rule |
| --- | --- |
| `draft` | ORM/UI default; only unlinkable; form Validate by Seller source |
| `validated_seller` | MCP stamp; Seller target; Review queue |
| `validated_collections` | Document Review Approve only |

MUST NOT have Reject or `rejected`. Form **Validate by Seller** MUST work only from `draft` and MUST NOT stamp reviewer/time. Validated by Collections MUST be only via Review Approve (no form button). Intercept MUST refuse raw `validated_collections`; `validated_seller` only via Seller action or MCP create. Statusbar MUST NOT be clickable. Unlink only when `state` is `draft` and `allocation_id` unset or `draft`. Draft plus confirmed MUST be refused. Unlink MUST NOT project voucher amounts onto residual and MUST NOT refuse because leftover-voucher residual would be `< 0`. Invoice lines MUST NOT be auto-edited. Validate by Seller MUST remain if Review is OFF. Review RPCs stay in `document-review`.
(Previously: `pending`/`approved`/`rejected`; Approve/Reject with reviewer; kanban drag; unlink pending; projected residual `< 0` refused.)

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

### Requirement: Payment field contract

Each voucher MUST persist `document_type` `bank_transfer` | `check` | `cash_deposit` |
`unsupported` and nullable payment fields (OCR validators NOT required): `amount`,
`from_account`, `to_account`, `voucher_number`, `voucher_date`, `check_number`,
`check_bank`, `check_issue_date`, `check_payment_date`, `check_type` Selection
`common`/`deferred`. `unsupported` MUST persist without other payment fields.

#### Scenario: Persist type-specific fields

- GIVEN `bank_transfer`, `check`, and `cash_deposit` vouchers with payment fields filled
  (`check_type` `common` or `deferred`)
- WHEN saved
- THEN each voucher MUST persist those values

#### Scenario: Unsupported and partial entry

- GIVEN an `unsupported` voucher plus a partial supported-type voucher
- WHEN saved
- THEN both MUST persist

### Requirement: Payment Vouchers UI

MUST expose Collections → Payment Vouchers as the only create/edit surface (`view_mode`
`list,form`; create and edit enabled). MUST `<delete>` stages kanban. MUST NOT keep
Reassign Customers kanban. Menu Payment Vouchers MUST stay `sequence=10`. Form MUST show
non-clickable statusbar, **Validate by Seller** when `draft`, readonly `create_date`,
type-specific payment fields, chatter/activity; MUST NOT show `received_date`,
Approve/Reject, a Collections button, History, or payment-line tables. `partner_id` MUST
have no bound-partner domain. Clearing `sheet_id` on an open member MUST unlink;
non-open-sheet membership writes MUST be rejected. MUST NOT expose sheet-form member
list or Payment Lines.

| Surface | MUST |
| --- | --- |
| List visible | `name`, `create_date`, `sheet_id`, `seller_id`, `document_type`, `amount`, `state` |
| List hide | `partner_id`, `company_id`, `document_id` optional hide; `currency_id` column-invisible |
| Search | one filter per state; one per `document_type`; Created On `date="create_date"`; keep name/customer/seller/sheet |

(Previously: MUST keep Reassign Customers kanban; closed-sheet membership writes
rejected.)

#### Scenario: Menu and form behaviors

- GIVEN the module installed and a `draft` voucher
- WHEN Payment Vouchers form opens
- THEN list MUST show `name`, `create_date`, `sheet_id`, `seller_id`, `document_type`,
  `amount`, `state`
- AND form MUST show non-clickable statusbar, Validate by Seller, readonly
  `create_date`, type-specific fields, chatter; MUST NOT show `received_date`,
  Approve/Reject, Collections, History, or payment-line tables

#### Scenario: Kanban grouped by state

- GIVEN Payment Vouchers
- WHEN views load
- THEN stages kanban MUST NOT exist, `view_mode` MUST be `list,form`, and Reassign
  Customers kanban MUST NOT remain

#### Scenario: Payment Lines menu absent

- GIVEN the module installed
- WHEN menus load
- THEN Collections → Payment Lines MUST NOT appear

#### Scenario: Menu sequence locked

- GIVEN Collections menus
- WHEN sequences are inspected
- THEN Payment Vouchers MUST be `sequence=10`

#### Scenario: Search filters

- GIVEN Payment Vouchers search
- WHEN filters are inspected
- THEN one filter per voucher state and per `document_type` MUST exist, and Created On
  MUST be a date filter on `create_date`

#### Scenario: UI create_date visibility

- GIVEN an existing voucher
- WHEN list, search, or form is opened
- THEN readonly `create_date` MUST be visible and not editable

#### Scenario: Customer field has no domain

- GIVEN Payment Vouchers list, search, or form
- WHEN Customer is opened
- THEN the field MUST be `partner_id` with no bound-connector domain

#### Scenario: sheet_id on list form search

- GIVEN an existing voucher with or without a sheet
- WHEN list, form, or search is opened
- THEN list MUST show visible `sheet_id`, form editable `sheet_id` when the sheet is
  `open` or the voucher is unassigned, search field and group-by

#### Scenario: Clear sheet_id unlinks open membership

- GIVEN a voucher assigned to an open sheet
- WHEN `sheet_id` is cleared on the form and saved
- THEN the voucher MUST be unassigned and the sheet MUST persist

#### Scenario: Closed-sheet unlink denied

- GIVEN a voucher assigned to a proposal, closed, or cancelled sheet
- WHEN `sheet_id` is cleared or changed on the form
- THEN the write MUST be rejected and membership MUST be unchanged

### Requirement: Unsupported vouchers remain persistable

`unsupported` vouchers MUST remain persistable (e.g. MCP) and MUST be findable via
Collections → Payment Vouchers (e.g. filter `document_type=unsupported`).

#### Scenario: Unsupported voucher visible in Payment Vouchers

- GIVEN an `unsupported` voucher exists
- WHEN an internal user opens Collections → Payment Vouchers and filters to
  `unsupported`
- THEN that voucher MUST be listed

### Requirement: Optional image or PDF attachment per voucher

Each `collection.voucher` MAY store one optional designated proof as a chatter
`ir.attachment` (empty `res_field`, linked via `mail.message`). Omit/empty MUST remain
valid. Proof files MUST be `copy=False` and under existing internal-user voucher ACL.
Setting or replacing designated proof MUST validate base64 and detected MIME (`image/*`
or PDF only); MUST raise `UserError` otherwise. (Previously: Proof was Binary
`attachment=True` plus filename via `ir.attachment`.)

#### Scenario: Omit attachment valid

- GIVEN a voucher with no attachment
- WHEN saved
- THEN the voucher MUST persist

#### Scenario: Valid file persists

- GIVEN a saved voucher and a valid image/PDF proof
- WHEN the proof is posted on the voucher chatter
- THEN the file MUST persist as an `ir.attachment` on that thread
- AND MUST NOT persist as Binary field `attachment`

#### Scenario: Invalid content rejected

- GIVEN invalid base64 or non-image/non-PDF MIME
- WHEN a designated proof is set or replaced
- THEN MUST raise `UserError` and MUST NOT persist the file

### Requirement: Attachment widgets on Payment Vouchers views

Payment Vouchers form, list, and kanban MUST NOT include Binary attachment or filename
widgets. Form chatter MAY remain so internal users MAY attach after the voucher is
saved. Where a file picker applies to designated proof, browser accept MUST be limited
to `image/*` and PDF. (Previously: Form, list, and kanban required Binary attachment and
filename widgets.)

#### Scenario: Payment Vouchers views omit Binary widgets

- GIVEN Collections → Payment Vouchers
- WHEN an internal user opens form, list, or kanban
- THEN Binary attachment and filename widgets MUST NOT be present
- AND form chatter MUST remain available for attaching files after save

### Requirement: Destructive reset of legacy header and line data

On apply, the system MAY discard legacy header vouchers, payment lines, chatter, and
attachments. The system MUST NOT convert header+line rows, chatter, or attachments into
standalone vouchers.

#### Scenario: Upgrade without conversion

- GIVEN a database with header vouchers and payment lines
- WHEN this change is applied
- THEN legacy header/line data MAY be absent
- AND historical vouchers MUST NOT be required as converted standalone records

### Requirement: Voucher seller field

Each `collection.voucher` MUST support `seller_id` targeting an internal user (not
portal/share). NEW create via UI, ORM, import, or MCP MUST require `seller_id`. The
system MUST NOT backfill existing null rows. List, form, and search MUST expose
`seller_id`. (Previously: ORM/RPC creates without seller remained allowed.)

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
when auto-create is OFF (see collection-sheets). (Previously: Auto-assign always ran;
one-open was per seller across all companies.)

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

### Requirement: Designated proof is message_main_attachment_id

Each voucher's designated proof MUST be `message_main_attachment_id`. MCP create MUST
post at most one nested proof per payment. Extra chatter files MAY exist after save.
MIME allow-list (`image/*` or PDF) MUST apply only when setting or replacing designated
proof and when validating MCP nests. Extra chatter files MUST NOT be restricted to that
allow-list. A non-image/non-PDF file MUST NOT become designated proof.

#### Scenario: MCP nest becomes designated proof

- GIVEN an all-new MCP payment with one valid nested image/PDF
- WHEN create completes
- THEN that file MUST be `message_main_attachment_id`
- AND MUST be visible on the voucher chatter

#### Scenario: Extra files do not steal proof

- GIVEN a voucher whose designated proof is already set
- WHEN an extra chatter file is attached
- THEN `message_main_attachment_id` MUST remain the prior proof

#### Scenario: Non-image extra cannot become proof

- GIVEN a voucher with empty designated proof
- WHEN a non-image/non-PDF chatter file is attached
- THEN `message_main_attachment_id` MUST remain empty

### Requirement: Pre-upgrade migration of Binary proofs

On upgrade to this change, each voucher that had a Binary field attachment MUST keep
that file as designated chatter proof, using the prior `attachment_filename` (or
`proof.bin` when empty). After upgrade, Binary `attachment` and `attachment_filename`
MUST NOT remain, and leftover `res_field=attachment` rows MUST NOT remain inaccessible.

#### Scenario: Binary field attachment migrates

- GIVEN a voucher with a Binary field attachment and `attachment_filename`
- WHEN this change is applied
- THEN that file MUST be the chatter designated proof
- AND `res_field` MUST NOT remain `attachment`

#### Scenario: Empty filename fallback

- GIVEN a Binary field attachment with empty `attachment_filename`
- WHEN this change is applied
- THEN designated proof `name` MUST be `proof.bin`

### Requirement: Typed provenance copies of payment fields

Each voucher MUST persist typed raw-OCR and seller-confirmed copies of the payment
review field set. Current columns MUST remain the editable copy. Provenance MUST NOT
include `document_id`, `partner_id`, customer identification, `seller_id`, attachment,
or base64, and MUST NOT copy with the voucher. Cash-deposit MAY store `voucher_number`
and `voucher_date` in all three layers even when UI hides them. Voucher write MUST
reject provenance keys after create. (Previously: Exclusion named Char
`customer_identification`.)

#### Scenario: Identity and proof stay outside provenance

- GIVEN an all-new MCP payment with `document_id`, customer, seller, and attachment
- WHEN create completes
- THEN provenance MUST contain only payment review fields
- AND MUST NOT contain `document_id`, customer, seller, attachment, or base64

#### Scenario: Cash-deposit extra keys stored in all layers

- GIVEN a cash-deposit payment whose nests include `voucher_number` and `voucher_date`
- WHEN all-new create completes
- THEN they MUST persist in all three layers
- AND UI MAY hide them for `cash_deposit`

#### Scenario: Voucher write rejects provenance keys

- GIVEN an existing voucher
- WHEN write includes raw or seller-confirmed field keys
- THEN the write MUST be rejected
- AND stored provenance MUST remain unchanged

### Requirement: MCP nested provenance on all-new create

`create_collection_allocation` MAY accept nested `raw_ocr` and
`seller_confirmed` with the same typed keys as current fields. When both
nests are present, seller-confirmed MUST equal top-level fields; current MUST
initialize from seller-confirmed; raw MUST persist as submitted. Omitting
both nests MUST leave empty provenance; UI/ORM create MUST remain allowed.
Malformed, one-sided, or mismatched nests MUST fail the batch with no writes.
Exact same-company `document_id` reuse MUST ignore those nests with no
provenance mutation and MUST continue to allocation.
(Previously: Nested provenance was accepted by MCP `create_collection_vouchers`.)

#### Scenario: Unchanged seller confirmation

- GIVEN unused `document_id`s and both nests equal to top-level payment fields
- WHEN all-new create runs
- THEN raw, seller-confirmed, and current MUST be equal

#### Scenario: Seller correction

- GIVEN raw nest differs from seller-confirmed, and seller-confirmed equals
  top-level
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
- WHEN `create_collection_allocation` runs
- THEN the call MUST fail with no writes

#### Scenario: Exact replay ignores provenance nests

- GIVEN every submitted `document_id` already exists in the same company, with
  or without stored provenance
- WHEN retried with different or omitted nests
- THEN matching vouchers MUST return unchanged
- AND provenance and snapshots MUST NOT be written, backfilled, or mutated

### Requirement: Immutable review snapshots and ACL

MUST store immutable Document Review snapshots (revision, reviewer, time, decision, current payment fields). Internal users MUST read snapshots for allowed companies and MUST NOT write or unlink, add dedicated groups, or sudo. Snapshots MUST follow voucher company isolation. Form Validate by Seller MUST NOT append snapshots. Snapshot `decision` MUST stay `approved`\|`rejected`.
(Previously: Form Approve and Reject MUST NOT append snapshots.)

#### Scenario: Internal users read history without client mutation

- GIVEN an internal user and snapshots of an allowed-company voucher
- WHEN they read snapshots
- THEN ACL MUST allow read and MUST deny client write or unlink

#### Scenario: Form Approve and Reject do not snapshot

- GIVEN a draft voucher on Payment Vouchers
- WHEN form Validate by Seller runs
- THEN voucher state MUST change as specified and no snapshot MUST be appended

### Requirement: Additive upgrade without provenance backfill

Upgrade MUST add nullable provenance with no backfill or fabricated snapshots.

#### Scenario: Existing rows keep current and empty provenance

- GIVEN vouchers created before this change
- WHEN the upgrade is applied
- THEN current payment fields MUST remain
- AND raw and seller-confirmed MUST be empty
- AND those vouchers MUST have no snapshots

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

Existing vouchers MUST stay visible and operable if their seller is later disabled. MUST NOT hide or delete them for that reason.
(Previously: Operable scenario used `pending` Approve/Reject.)

#### Scenario: Disabled-seller voucher stays visible

- GIVEN a voucher whose seller is later removed from the enabled list
- WHEN an allowed-company user opens Payment Vouchers
- THEN that voucher MUST still be listed

#### Scenario: Disabled-seller voucher remains operable

- GIVEN a `draft` voucher whose seller is later disabled
- WHEN Validate by Seller runs without changing seller or type
- THEN `validated_seller` MUST persist and the voucher MUST NOT be deleted

### Requirement: Cross-company document_id reject not replay

`document_id` uniqueness MUST remain global among non-null values. When a new
write collides with another company's `document_id`, the system MUST reject
it (MUST NOT replay) and MUST NOT disclose that voucher's id or name. A user
who can read both companies MUST NOT receive the other company's voucher as
an MCP replay via `create_collection_allocation`.
(Previously: Multi-company MCP replay named `create_collection_vouchers`.)

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
- WHEN they call `create_collection_allocation` in company A with D
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
- AND the second MUST take the seller company or the default company when the seller has
  none

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

### Requirement: Voucher allocation membership

Each voucher MAY have `allocation_id`. Write of `allocation_id` MUST be refused unless current and target (if set) are both `draft` or unset. Unlink MUST be allowed when voucher `state` is `draft` and `allocation_id` is unset or `draft`. Unlink MUST be refused when allocation is `confirmed`. Removing a voucher from a draft allocation MUST NOT project voucher amounts onto residual. Residual MUST remain `total_debt − total_applied`. MUST NOT refuse unlink because leftover-voucher residual would be `< 0`. Invoice lines MUST NOT be auto-edited. All three voucher states MAY be allocated.
(Previously: Unlink when voucher `state` is `pending`; projected residual − voucher amount `< 0` refused.)

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

When `partner_id` changes, the system MUST NOT auto-compute or auto-write
`allocation_id`. An allocated voucher MUST be unassigned before Customer MAY change; a
`partner_id` write while `allocation_id` is set MUST raise `UserError` with no persist.
MUST NOT `sudo()`. Same-value `partner_id` MUST NOT recompute allocation. `confirmed`
current allocation MUST refuse the move with no field change. While the sheet is `open`
and the voucher is unassigned, any voucher state MAY change Customer.
(Previously: Customer change auto-attached the unique draft same-sheet allocation or
left the voucher unallocated with chatter.)

#### Scenario: Allocated customer change refused

- GIVEN an open-sheet voucher with `allocation_id` set
- WHEN `partner_id` is written to another customer
- THEN MUST raise `UserError`
- AND `partner_id` and `allocation_id` MUST be unchanged

#### Scenario: Unassign then customer change

- GIVEN an open-sheet voucher on a draft allocation
- WHEN `allocation_id` is cleared then `partner_id` is written to another customer
- THEN `partner_id` MUST persist and `allocation_id` MUST remain unset

#### Scenario: Same-value partner write

- GIVEN an open-sheet voucher on a draft allocation
- WHEN `partner_id` is written to the same customer
- THEN both fields MUST remain unchanged

#### Scenario: Confirmed source refused

- GIVEN an open-sheet voucher whose `allocation_id` is `confirmed`
- WHEN `partner_id` is written
- THEN MUST refuse and both fields MUST be unchanged

#### Scenario: Unassigned voucher may change customer

- GIVEN an open-sheet unallocated voucher in `draft`, `validated_seller`, or
  `validated_collections`
- WHEN `partner_id` is written to another customer
- THEN the write MUST succeed and `state` MUST stay unchanged

#### Scenario: Fully applied source no longer auto-moves

- GIVEN an open-sheet voucher on a draft allocation whose residual is 0
- WHEN `partner_id` is written to another customer without unassigning
- THEN MUST raise `UserError` and both fields MUST be unchanged

### Requirement: Voucher partner-allocation constrain

When `allocation_id` is set, voucher `partner_id` MUST equal that allocation's
`partner_id` after any write of `partner_id` or `allocation_id`. A mismatch MUST
raise `UserError` with no persist.

#### Scenario: Constrain mismatch refused

- GIVEN a voucher and an allocation whose partners differ
- WHEN `allocation_id` is written without matching `partner_id` in the same vals
- THEN the write MUST be refused
- AND stored `partner_id` and `allocation_id` MUST be unchanged

### Requirement: Internal collection payment helpers

Internal `_collection_*` helpers on `muk_mcp.mixin` MUST remain (parse payment
vals, attachment nest, provenance nests, create vouchers, submit-order
payload, classify/replay/conflict, require internal seller). They MUST NOT be
registered as MCP tools. `create_collection_allocation` MUST reuse them.
Payment items MUST omit `customer_identification`; helpers MUST take
top-level identification and replicate it per payment. Exact same-company
`document_id` set MUST be reusable by allocation (continue; MUST NOT
voucher-only early-return). Partial overlap and other-company hits MUST stay
generic conflict with no writes. Optional nested `attachment` and
`raw_ocr`/`seller_confirmed` parse rules MUST still apply on the fused write.

#### Scenario: Helpers not discovered as MCP tools

- GIVEN the MCP registry for `registry=mcp`
- WHEN tools are discovered
- THEN `create_collection_vouchers` MUST NOT appear
- AND `_collection_*` helpers MUST NOT have `@mcp_tool` or a `muk_mcp.tool` row

#### Scenario: Allocation reuses helpers

- GIVEN inline payments with top-level identification
- WHEN `create_collection_allocation` runs
- THEN helpers MUST parse payments, nests, and payload order
- AND MUST NOT require per-payment `customer_identification`

### Requirement: Voucher state SQL remap

Upgrade SQL MUST remap `collection.voucher.state` before ORM browse: `pending`→`draft`, `approved`→`validated_collections`, `rejected`→`draft`. Leftover old keys MUST collapse. MUST NOT keep voucher `rejected`.

#### Scenario: Remap before ORM

- GIVEN rows in `pending`, `approved`, `rejected`
- WHEN this upgrade runs
- THEN they MUST be `draft`, `validated_collections`, `draft`
- AND ORM MUST NOT see leftover old keys

### Requirement: Sheet-state voucher field guards

Voucher membership (`sheet_id` add, remove, or reassign) and voucher business fields
MUST be writable only while the sheet is `open` (or the voucher is unassigned). When the
sheet is `proposal`, `closed`, or `cancelled`, those writes MUST raise `UserError` with
no persist, including via form or RPC. Chatter MUST remain writable. Partner-allocation
constrain MUST still apply.
(Previously: Membership freeze was closed-only; business fields had no sheet-state
guard.)

#### Scenario: Open membership and business fields writable

- GIVEN a voucher on an open sheet
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
