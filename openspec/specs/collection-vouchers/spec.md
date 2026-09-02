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

Each voucher MUST support messaging and activities. Voucher fields including `state`
SHOULD be tracked in chatter. (Previously: Chatter lived on the header; scenarios used
header state `new`.)

#### Scenario: Chatter and activities available

- GIVEN an open voucher form
- WHEN a message is posted or an activity scheduled
- THEN it MUST persist on that voucher

#### Scenario: State change tracked

- GIVEN a voucher in `pending`
- WHEN approved or rejected
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

Completeness MUST NOT require HTTP API, WhatsApp metadata, or agent calls. Each voucher
MUST require a `res.partner` Customer (`partner_id`). Optional per-voucher image/PDF
attachments are an allowed capability and MUST NOT be required for completeness of
unrelated voucher features. (Previously: Completeness MUST NOT require partner/CRM
linkage.)

#### Scenario: Completeness without deferred features

- GIVEN backend-only voucher management
- WHEN operators create, edit, approve, or reject vouchers
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

Approve and reject MUST refuse stale or concurrent attempts when the voucher is no
longer eligible (not `pending`, or designated proof (`message_main_attachment_id`) no
longer present) and MUST NOT corrupt review or voucher state. (Previously: Eligibility
failed when Binary attachment was no longer present.)

#### Scenario: Concurrent or stale review attempt

- GIVEN a voucher already decided or otherwise ineligible for review (not `pending`, or
  designated proof no longer present)
- WHEN approve or reject is attempted again
- THEN the system MUST refuse the action and MUST NOT alter terminal or decided state

### Requirement: Attachment replacement resets review to pending

Replacing a voucher's designated proof (a change of `message_main_attachment_id` to a
different attachment) MUST reset that voucher's `state` to `pending` and MUST clear
prior reviewer/time audit for a fresh review. Extra chatter files that do not change
`message_main_attachment_id` MUST NOT reset review, audit, or rotation. Clearing
designated proof MUST reset rotation to 0 and MUST NOT reopen a decided voucher.
Omit/empty and MIME validation rules remain unchanged. (Previously: Replacement was a
write of new Binary content.)

#### Scenario: Attachment replacement resets voucher state

- GIVEN a voucher previously `approved` or `rejected` with a designated proof
- WHEN `message_main_attachment_id` changes to a different valid proof
- THEN `state` MUST become `pending`
- AND prior reviewer/time audit MUST be cleared for re-review

#### Scenario: Extra chatter files do not reset review

- GIVEN a voucher with designated proof in `approved` or `rejected`
- WHEN an extra chatter file is added without changing `message_main_attachment_id`
- THEN `state` and reviewer/time audit MUST remain unchanged

#### Scenario: Clearing proof does not reopen

- GIVEN a voucher in `approved` or `rejected` with designated proof
- WHEN designated proof is cleared with no replacement
- THEN `state` MUST remain decided
- AND rotation MUST reset to 0

### Requirement: Voucher fields and defaults

Each `collection.voucher` MUST represent one payment. The system MUST require
`partner_id` (label Customer; tracking; index; `ondelete` restrict). The system MUST NOT
store or accept `customer_identification` or `received_date`. Registration time MUST be
automatic ORM `create_date` (readonly; MUST NOT be overridable by MCP, create vals, or
editable views). On create, `state` MUST default to `pending`. Currency MUST be the
company default (no multi-currency UX). Upgrade MUST NOT backfill `partner_id`.
(Previously: Required Char `customer_identification`.)

#### Scenario: Defaults on create

- GIVEN a new voucher saved without overriding defaults
- WHEN create completes
- THEN `create_date` MUST be automatic, `state` `pending`, currency company default
- AND `received_date` MUST NOT exist

#### Scenario: Required fields

- GIVEN a voucher missing `partner_id`
- WHEN saved
- THEN the system MUST reject the save

#### Scenario: create_date not overridable

- GIVEN a create that supplies custom creation time or `received_date`
- WHEN create runs via UI or MCP
- THEN creation time MUST NOT be caller-overridable and `received_date` MUST NOT persist

#### Scenario: Char customer_identification gone

- GIVEN the voucher model after this change
- WHEN fields are inspected
- THEN `customer_identification` MUST NOT exist
- AND `partner_id` MUST be required

### Requirement: Voucher lifecycle

States MUST be `pending`, `approved`, and `rejected`. Approve and Reject MUST apply only
from `pending` and MUST NOT alter terminal states. Delete MUST be allowed only when
`state` is `pending` and `allocation_id` is unset or `draft`. Pending plus `confirmed`
MUST be refused. Removing a pending voucher from a draft allocation MUST refuse when
projected residual (current residual minus voucher amount, currency compare) is `< 0`
and MUST NOT auto-edit invoice lines. Any user-driven change from `pending` to
`approved` or `rejected` (including kanban drag) MUST record reviewer and review time
the same as Approve/Reject. Approve/Reject on Payment Vouchers MUST remain available
whether Document Review is ON or OFF. Review queue RPCs remain governed by
`document-review`. Confidence, per-field stamps, and reviewer-note persistence MUST
NOT be required.
(Previously: Delete allowed for any pending voucher; allocated unlink was refused.)

#### Scenario: Approve from pending

- GIVEN a voucher in `pending`
- WHEN approved
- THEN `state` MUST become `approved`
- AND reviewer and review time MUST be recorded

#### Scenario: Reject from pending

- GIVEN a voucher in `pending`
- WHEN rejected
- THEN `state` MUST become `rejected`
- AND reviewer and review time MUST be recorded

#### Scenario: Terminal states block transitions

- GIVEN a voucher in `approved` or `rejected`
- WHEN Approve or Reject is attempted
- THEN `state` MUST NOT change

#### Scenario: Delete from pending

- GIVEN a voucher in `pending` with allocation unset or `draft` and projected
  residual ≥ 0
- WHEN deleted
- THEN the system MUST allow the delete

#### Scenario: Delete blocked when not pending

- GIVEN a voucher in `approved` or `rejected`
- WHEN deleted
- THEN the system MUST refuse the delete

#### Scenario: Delete pending on confirmed allocation refused

- GIVEN a pending voucher on a confirmed allocation
- WHEN deleted
- THEN the system MUST refuse the delete
- AND the voucher and allocation MUST remain

#### Scenario: Delete pending on draft with negative residual refused

- GIVEN a pending voucher on a draft allocation whose residual would become
  `< 0`
- WHEN deleted
- THEN the system MUST refuse the delete
- AND invoice lines MUST NOT be auto-edited

#### Scenario: Kanban drag is audited

- GIVEN a `pending` voucher on a state-grouped kanban
- WHEN an internal user drags it to `approved` or `rejected`
- THEN `state` MUST change to that value
- AND reviewer and review time MUST be recorded as for Approve/Reject

#### Scenario: Approve and Reject remain when review is off

- GIVEN Document Review is OFF and a voucher in `pending`
- WHEN Approve or Reject is used on Payment Vouchers
- THEN `state` MUST become `approved` or `rejected` respectively

#### Scenario: Default pending

- GIVEN a newly created voucher
- WHEN `state` is read without a prior decision
- THEN `state` MUST be `pending`

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

The system MUST expose Collections → Payment Vouchers as the only create/edit surface
(kanban, list, form; create and edit enabled). Kanban MUST group by `state`. List/search
MUST show reference, Customer (`partner_id`), readonly `create_date`, status, and
payment fields. Form MUST show statusbar, Approve/Reject when `pending`, readonly
`create_date`, type-specific payment fields, chatter/activity, and MUST NOT show
`received_date`. List, search, kanban, and form MUST show `partner_id` without a
bound-partner domain. List MUST expose optional hidden `sheet_id`; form MUST expose it
editable; search MUST expose field and group-by; kanban MUST NOT add it. Clearing
`sheet_id` on an open member MUST unlink; closed-sheet membership writes MUST be
rejected. MUST NOT expose a sheet-form voucher member list, Payment Lines, or
payment-line tables.

(Previously: Sheet member list was a voucher UI surface; list, form, and search omitted
`sheet_id`.)

#### Scenario: Menu and form behaviors

- GIVEN the module installed and a voucher in `pending`
- WHEN Payment Vouchers form opens
- THEN list/search MUST show reference, Customer, `create_date`, status
- AND form MUST show statusbar, Approve/Reject, readonly `create_date`, type-specific
  payment fields, chatter/activity, and MUST NOT show `received_date` or payment-line
  tables

#### Scenario: Kanban grouped by state

- GIVEN Payment Vouchers kanban
- WHEN it opens
- THEN vouchers MUST be grouped by `state`
- AND create and edit MUST be enabled

#### Scenario: Payment Lines menu absent

- GIVEN the module installed
- WHEN menus load
- THEN Collections → Payment Lines MUST NOT appear

#### Scenario: UI create_date visibility

- GIVEN an existing voucher
- WHEN list, search, kanban, or form is opened
- THEN readonly `create_date` MUST be visible and not editable

#### Scenario: Customer field has no domain

- GIVEN Payment Vouchers list, search, kanban, or form
- WHEN Customer is opened
- THEN the field MUST be `partner_id`
- AND MUST NOT restrict choices to bound connector customers

#### Scenario: sheet_id on list form search

- GIVEN an existing voucher with or without a sheet
- WHEN list, form, or search is opened
- THEN list MUST show optional hidden `sheet_id`, form editable `sheet_id`, and search a
  `sheet_id` field and group-by
- AND kanban MUST NOT show `sheet_id`

#### Scenario: Clear sheet_id unlinks open membership

- GIVEN a voucher assigned to an open sheet
- WHEN an internal user clears `sheet_id` on the voucher form and saves
- THEN the voucher MUST become unassigned and the sheet MUST persist

#### Scenario: Closed-sheet unlink denied

- GIVEN a voucher assigned to a closed sheet
- WHEN an internal user clears or changes `sheet_id` on the voucher form
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

The system MUST store immutable Document Review snapshots (revision, reviewer, time,
decision, and current payment fields). Internal users MUST read history of snapshots for
companies they are allowed and MUST NOT write or unlink snapshots, add dedicated groups,
or sudo. Snapshots MUST follow the same company isolation as vouchers. Form Approve and
Reject MUST NOT append snapshots. (Previously: No record rules on snapshots.)

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

Each voucher MAY have `allocation_id`. Write of `allocation_id` MUST be refused
unless current and target (if set) are both `draft` or unset. Unlink MUST be
allowed when `state` is `pending` and `allocation_id` is unset or `draft`,
subject to residual projection. Unlink MUST be refused when allocation is
`confirmed`. Removing a voucher from a draft allocation MUST project residual
as current residual minus that voucher's amount (currency compare). If
projected residual is `< 0`, unlink MUST be refused; invoice lines MUST NOT be
auto-edited.
(Previously: Write required current and target confirmed or unset; unlink
refused while allocated.)

#### Scenario: allocation_id write on draft or unset

- GIVEN current and target are both `draft` or unset
- WHEN `allocation_id` is written
- THEN the write MUST succeed

#### Scenario: Confirmed membership write refused

- GIVEN current or target is `confirmed`
- WHEN `allocation_id` is written
- THEN the write MUST be refused
- AND stored `allocation_id` MUST be unchanged

#### Scenario: Pending unlink on draft or unset

- GIVEN a pending voucher with allocation unset or `draft` and projected
  residual ≥ 0
- WHEN deleted
- THEN the system MUST allow the delete

#### Scenario: Draft residual underflow refuses unlink

- GIVEN a pending voucher on a draft allocation whose residual would become
  `< 0`
- WHEN the voucher is deleted
- THEN unlink MUST be refused
- AND invoice lines MUST NOT be auto-edited

### Requirement: Partner write follows allocation

When `partner_id` changes, the system MUST compute `allocation_id` before persist
and MUST write `partner_id` and `allocation_id` in the same vals (per record when
outcomes differ). MUST NOT `sudo()`. While the sheet is `open`, any voucher state
MAY change Customer. Same-value `partner_id` MUST NOT recompute allocation.

`confirmed` current allocation MUST refuse the move with no field change.
Draft source with projected residual (current residual minus voucher amount,
currency compare) `< 0` MUST refuse with no field change.

MUST attach the unique draft same-sheet allocation for the new partner when
projected residual satisfies residual rules; otherwise MUST leave unallocated and
MUST post chatter for that outcome.
(Previously: Attach/detach used confirmed allocations; non-confirmed
`validated`/`rejected` sources refused the move.)

#### Scenario: Same-write partner and allocation

- GIVEN an open-sheet voucher on draft allocation A (partner P) and unique
  draft same-sheet allocation B (partner Q) with attachable residual
- WHEN `partner_id` is written to Q
- THEN `partner_id` MUST be Q and `allocation_id` MUST be B
- AND both fields MUST persist in one write

#### Scenario: Fully applied source refused

- GIVEN an open-sheet voucher on a draft allocation whose residual is 0
- WHEN `partner_id` is written to another customer
- THEN the write MUST be refused
- AND `partner_id` and `allocation_id` MUST be unchanged

#### Scenario: Target attaches when residual holds

- GIVEN an open-sheet unallocated voucher and unique draft same-sheet
  allocation for Q with attachable residual
- WHEN `partner_id` is written to Q
- THEN `allocation_id` MUST become that allocation

#### Scenario: Target left unallocated when residual does not hold

- GIVEN an open-sheet voucher and no unique draft same-sheet allocation for Q
  that satisfies residual rules (including empty allocation, residual 0, no
  `residual_reason`)
- WHEN `partner_id` is written to Q
- THEN `partner_id` MUST be Q and `allocation_id` MUST be unset
- AND chatter MUST record that the voucher was left unallocated

#### Scenario: Confirmed source refused

- GIVEN an open-sheet voucher whose `allocation_id` is `confirmed`
- WHEN `partner_id` is written
- THEN the write MUST be refused
- AND `partner_id` and `allocation_id` MUST be unchanged

#### Scenario: Approved or rejected voucher may move

- GIVEN an open-sheet voucher in `approved` or `rejected` with no blocking residual
- WHEN `partner_id` is written to another customer
- THEN the write MUST succeed
- AND `state` MUST stay `approved` or `rejected`

### Requirement: Voucher partner-allocation constrain

When `allocation_id` is set, voucher `partner_id` MUST equal that allocation's
`partner_id` after any write of `partner_id` or `allocation_id`. A mismatch MUST
raise `UserError` with no persist.

#### Scenario: Constrain mismatch refused

- GIVEN a voucher and an allocation whose partners differ
- WHEN `allocation_id` is written without matching `partner_id` in the same vals
- THEN the write MUST be refused
- AND stored `partner_id` and `allocation_id` MUST be unchanged

### Requirement: Context-gated partner group_expand

`partner_id` MUST use a `group_expand` method (MUST NOT be boolean `True`). When
context `collection_reassign_sheet_id` is missing, invalid, or unreadable, expand
MUST return the identity groups. When that context names a readable sheet, expand
MUST return that sheet's allocation customers union member-voucher customers
(including empty allocation columns and stray voucher customers), ordered as
`res.partner` default order.

#### Scenario: Identity expand without context

- GIVEN Payment Vouchers grouped by Customer and no readable
  `collection_reassign_sheet_id`
- WHEN group expand runs
- THEN the returned groups MUST equal the identity groups
- AND empty allocation-only customers MUST NOT be added

#### Scenario: Empty allocation columns

- GIVEN reassign context for a readable sheet that has an allocation with no
  vouchers
- WHEN group expand runs
- THEN that allocation's customer MUST appear as a column

#### Scenario: Stray extra columns

- GIVEN reassign context for a readable sheet with a member voucher whose
  customer has no allocation on that sheet
- WHEN group expand runs
- THEN that voucher's customer MUST appear as a column

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
