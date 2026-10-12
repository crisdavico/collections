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

- GIVEN a Collections User creates a voucher
- WHEN saved the first time
- THEN name MUST match `COL/<current-year>/<number>` and be unique

#### Scenario: Numbers isolated per company

- GIVEN companies A and B each create a new voucher
- WHEN both saves complete
- THEN each company's names MUST number independently of the other

### Requirement: Mail thread and activities

Each voucher MUST support messaging and activities. MUST track `state`, `seller_id`,
`sheet_id`, `document_type`, and `amount` in chatter. (Previously: `state` SHOULD be
tracked; seller/sheet/type/amount were untracked.)

#### Scenario: Chatter and activities available

- GIVEN an open voucher form
- WHEN a message is posted or an activity scheduled
- THEN it MUST persist on that voucher

#### Scenario: State change tracked

- GIVEN a `draft` voucher
- WHEN Validate by Seller runs
- THEN chatter MUST record the state change

### Requirement: Authorization for Collections Users

Collections Users (`collection.group_collection_user`; Collections Manager implies it)
MUST have full CRUD on vouchers of companies they are allowed. Plain internal users MUST
have no access. The system MUST NOT grant ACL on `collection.voucher.line`.
Allowed-company record rules MUST hide other companies. (Previously: every internal user
(`base.group_user`) had CRUD and dedicated groups were forbidden; before that, no record
rules made vouchers company-blind.)

#### Scenario: Collections User CRUD

- GIVEN an authenticated Collections User
- WHEN they CRUD a voucher of an allowed company
- THEN ACL MUST allow the operation

#### Scenario: User without Collections User denied

- GIVEN a user without the Collections User group (including a plain internal user)
- WHEN they attempt voucher CRUD
- THEN the system MUST deny access

### Requirement: Deferred integrations not required

Completeness MUST NOT require HTTP API, WhatsApp metadata, or agent calls. Each voucher
MUST require a `res.partner` Customer (`partner_id`). Optional per-voucher image/PDF
attachments are an allowed capability and MUST NOT be required for completeness of
unrelated voucher features. (Previously: Completeness scenario named approve or reject.)

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

`create_collection_allocation` MAY accept one optional nested attachment per payment
with required `name`, `mimetype`, and base64 `datas` when present. Declared `mimetype`
MUST match content detection (`image/*` or PDF only); `image/jpg` MUST be treated as
equivalent to `image/jpeg` (case-insensitive) when comparing declared vs detected MIME.
Mismatch or bad base64 MUST raise `UserError` with no writes. Explicit JSON `null`,
`false`, or empty attachment MUST be treated as omit. Seller-declared `cash` MUST
succeed with attachment omitted or null. Create with attachments MUST persist all
vouchers and files atomically under a savepoint by posting each nest onto the new
voucher chatter via `message_post` (MUST NOT write Binary `attachment`). Exact
same-company, same-seller `document_id` reuse whose payment fields match MUST NOT add,
replace, or compare attachments (even when a voucher has none) and MUST continue to
allocation. All-new and conflict rules
MUST remain unchanged except as this change specifies for company, seller, and type
gates. (Previously: Declared MIME had to equal detected MIME exactly; `image/jpg` vs
`image/jpeg` failed; cash-without-proof was not named.)

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

- GIVEN every submitted `document_id` already exists in the same company for the calling
  seller with the same `seller_confirmed` fields
- WHEN retried with or without nested attachments
- THEN matching vouchers MUST be unchanged; attachments MUST NOT be
  written/replaced/compared
- AND the write MUST continue to allocation

#### Scenario: image/jpg aliases to jpeg

- GIVEN JPEG bytes whose detected MIME is `image/jpeg` and declared `mimetype` is
  `image/jpg`
- WHEN `create_collection_allocation` runs
- THEN the nested proof MUST persist as designated proof
- AND MUST NOT raise MIME mismatch

#### Scenario: Cash attachment null or omit is valid

- GIVEN a `cash` payment whose `attachment` is omitted or JSON `null`
- WHEN all-new `create_collection_allocation` runs
- THEN the voucher MUST persist without designated proof
- AND MUST NOT raise for missing attachment

### Requirement: Concurrent and stale review attempts

Approve MUST refuse stale or concurrent attempts when the voucher is ineligible (not
`validated_seller`, or designated proof absent) and MUST NOT corrupt state. Reject MUST
NOT exist. (Previously: Eligibility was not `pending`; approve or reject.)

#### Scenario: Concurrent or stale review attempt

- GIVEN a voucher already decided or ineligible (not `validated_seller`, or proof
  absent)
- WHEN approve is attempted again
- THEN MUST refuse and MUST NOT alter decided state

### Requirement: Attachment replacement resets review to pending

Replacing designated proof (`message_main_attachment_id` to a different attachment) MUST
set `state` to `validated_seller` and MUST clear reviewer/time, except on `cash` and
`seller_commission` vouchers, which carry no reviewed proof and never reopen. Reopening a
`validated_collections` voucher MUST first reverse the cash it replaced. A first proof
posted after the approved proof was deleted MUST reopen review like a swap. Extra chatter
files that do not change designated proof MUST NOT reset review, audit, or rotation.
Clearing proof MUST reset rotation to 0 and MUST NOT reopen; a write clearing the proof
of a `validated_collections` voucher MUST be refused. On a `closed` or `cancelled` sheet,
replacing, clearing, or deleting the proof attachment MUST be refused; past `submitted`,
a `validated_collections` voucher MUST NOT go back to review nor lose its proof. Omit/empty
and MIME rules unchanged. (Previously: Replacement reset `state` to `pending` from
`approved`/`rejected`.)

#### Scenario: Attachment replacement resets voucher state

- GIVEN a non-cash, non-commission voucher in `validated_seller` or
  `validated_collections` with designated proof on an open or submitted sheet
- WHEN designated proof changes to a different valid file
- THEN `state` MUST be `validated_seller` and reviewer/time MUST clear

#### Scenario: Extra chatter files do not reset review

- GIVEN designated proof in `validated_seller` or `validated_collections`
- WHEN an extra chatter file is added without changing designated proof
- THEN `state` and reviewer/time MUST stay unchanged

#### Scenario: Clearing proof does not reopen

- GIVEN a `validated_seller` voucher with designated proof
- WHEN proof is cleared with no replacement
- THEN `state` MUST stay decided and rotation MUST be 0

### Requirement: Approved vouchers are frozen

A `validated_collections` voucher MUST refuse changes to the twelve
`_REVIEW_EDITABLE_FIELDS` and to `partner_id`, `company_id`, `currency_id`, and
`to_account_bank_id` with a `UserError` that points to replacing the designated proof.
Writing an unchanged value MUST still save. Only server code inside the internal
`collection_audited_state` privileged scope (Document Review correction) MAY change them,
and any amount change MUST re-check the receipt-value cap. The form MUST show those fields
readonly once the voucher is approved. (Previously: approved vouchers stayed editable from
the form and over RPC.)

#### Scenario: Approved amount edit refused

- GIVEN a `validated_collections` voucher
- WHEN a Collections User writes a different `amount` or `partner_id`
- THEN MUST raise `UserError` and MUST NOT persist
- AND on an open or submitted sheet, replacing its designated proof MUST reopen it to
  `validated_seller` instead

### Requirement: Voucher fields and defaults

Each `collection.voucher` MUST represent one payment. MUST require `partner_id` (label
Customer; tracking; index; `ondelete` restrict). MUST NOT store
`customer_identification` or `received_date`. Registration time MUST be automatic ORM
`create_date` (readonly; MUST NOT be overridable). ORM/UI create MUST default `state` to
`draft`. MCP `_collection_create_vouchers` MUST stamp `validated_seller`. Currency MUST
be company default. Upgrade MUST NOT backfill `partner_id`. (Previously: Create
defaulted `state` to `pending` for ORM/UI and MCP.)

#### Scenario: Defaults on create

- GIVEN a new voucher saved without overriding defaults
- WHEN create completes
- THEN `state` MUST be `draft`, `create_date` automatic, company currency, and no
  `received_date`

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

| Key                     | Rule                                                            |
| ----------------------- | --------------------------------------------------------------- |
| `draft`                 | ORM/UI default; only unlinkable; form Validate by Seller source |
| `validated_seller`      | MCP stamp; Seller target; Review queue                          |
| `validated_collections` | Document Review Approve only                                    |

MUST NOT have Reject or `rejected`. Form **Validate by Seller** MUST work only from
`draft` and MUST NOT stamp reviewer/time. Validated by Collections MUST be only via
Review Approve (no form button). Intercept MUST refuse raw `validated_collections`;
`validated_seller` only via Seller action or MCP create. Statusbar MUST NOT be
clickable. Unlink only when `state` is `draft` and `allocation_id` unset or `draft`.
Draft plus confirmed MUST be refused. Unlink MUST NOT project voucher amounts onto
residual and MUST NOT refuse because leftover-voucher residual would be `< 0`. Invoice
lines MUST NOT be auto-edited. Validate by Seller MUST remain if Review is OFF. Review
RPCs stay in `document-review`. (Previously: `pending`/`approved`/`rejected`;
Approve/Reject with reviewer; kanban drag; unlink pending; projected residual `< 0`
refused.)

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
- THEN the system MUST allow the delete and MUST NOT refuse because leftover-voucher
  residual would change

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
- THEN unlink MUST succeed, invoice lines MUST NOT be auto-edited, and residual MUST
  stay debt − applied

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

Each voucher MUST persist `document_type` as one of `bank_transfer`, `check`, `echeck`,
`cash_deposit`, `retention_certificate`, `cash`, `unsupported`, or `seller_deposit`,
plus nullable payment fields (OCR validators NOT required): `amount`, `from_account`,
`to_account`, `voucher_number`, `voucher_date`, `check_number`, `check_bank`,
`check_issue_date`, `check_payment_date`, `check_type` Selection `common`/`deferred`,
and `retention_kind` Selection `iva`/`ganancias`/`iibb`/`suss`/`other` (nullable).
`unsupported` MUST persist without other payment fields. `cash` MUST persist with
`amount` and optional `voucher_date` and MUST NOT require designated proof.
`seller_deposit` MUST persist with `amount`, `voucher_number`, and `voucher_date`, MAY
have designated proof, and MUST use the sentinel partner.

| `document_type`         | Type-owned fields                                                                              |
| ----------------------- | ---------------------------------------------------------------------------------------------- |
| `bank_transfer`         | `amount`, `from_account`, `to_account`, `voucher_number`, `voucher_date`                       |
| `check`                 | `amount`, `check_number`, `check_bank`, `check_issue_date`, `check_payment_date`, `check_type` |
| `echeck`                | same as `check`                                                                                |
| `cash_deposit`          | `amount`, `to_account`, `voucher_number`, `voucher_date`                                       |
| `retention_certificate` | `amount`, `voucher_number`, `voucher_date`, `retention_kind`                                   |
| `cash`                  | `amount`, `voucher_date`; no proof                                                             |
| `unsupported`           | discriminator only                                                                             |
| `seller_deposit`        | `amount`, `voucher_number`, `voucher_date`; sentinel partner                                   |

(Previously: Seven types only; no `seller_deposit`.)

#### Scenario: Persist type-specific fields

- GIVEN `bank_transfer`, `check`, and `cash_deposit` vouchers with payment fields filled
  (`check_type` `common` or `deferred`)
- WHEN saved
- THEN each voucher MUST persist those values

#### Scenario: Unsupported and partial entry

- GIVEN an `unsupported` voucher plus a partial supported-type voucher
- WHEN saved
- THEN both MUST persist

#### Scenario: Persist echeck cash and retention_certificate

- GIVEN `echeck`, `cash`, and `retention_certificate` vouchers with their type-owned
  fields filled (`retention_kind` one of the five kinds)
- WHEN saved
- THEN each voucher MUST persist those values including `retention_kind` on the
  retention certificate

#### Scenario: Cash persists without proof

- GIVEN a `cash` voucher with `amount` and no designated proof
- WHEN saved
- THEN the voucher MUST persist
- AND `message_main_attachment_id` MAY be empty

#### Scenario: Persist seller_deposit

- GIVEN a `seller_deposit` voucher with `amount`, `voucher_number`, `voucher_date`, and
  the sentinel partner
- WHEN saved
- THEN the voucher MUST persist those values
- AND `partner_id` MUST remain the sentinel

### Requirement: Payment Vouchers UI

MUST expose Collections → Payment Vouchers as the only create/edit surface (`view_mode`
`list,form`; create and edit enabled). MUST `<delete>` stages kanban. MUST NOT keep
Reassign Customers kanban. Menu Payment Vouchers MUST stay `sequence=10`. Form MUST show
non-clickable statusbar, **Validate by Seller** when `draft`, readonly `create_date`,
type-specific payment fields, chatter/activity; MUST NOT show `received_date`,
Approve/Reject, a Collections button, History, or payment-line tables. `partner_id` MUST
have no bound-partner domain. Clearing `sheet_id` on an open member MUST unlink unless
the voucher is allocated or has receipt values or cash replacements (refused);
non-open-sheet membership writes MUST be rejected. MUST NOT expose sheet-form member
list or Payment Lines.

| Surface      | MUST                                                                                                            |
| ------------ | --------------------------------------------------------------------------------------------------------------- |
| List visible | `name`, `create_date`, `sheet_id`, `seller_id`, `document_type`, `amount`, `state`                              |
| List hide    | `partner_id`, `company_id`, `document_id` optional hide; `currency_id` column-invisible                         |
| Search       | one filter per state; one per `document_type`; Created On `date="create_date"`; keep name/customer/seller/sheet |

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

- GIVEN an unallocated voucher with no receipt values assigned to an open sheet
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
- WHEN a Collections User opens Collections → Payment Vouchers and filters to
  `unsupported`
- THEN that voucher MUST be listed

### Requirement: Optional image or PDF attachment per voucher

Each `collection.voucher` MAY store one optional designated proof as a chatter
`ir.attachment` (empty `res_field`, linked via `mail.message`). Omit/empty MUST remain
valid. Proof files MUST be `copy=False` and under the Collections User voucher ACL.
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
widgets. Form chatter MAY remain so Collections Users MAY attach after the voucher is
saved. Where a file picker applies to designated proof, browser accept MUST be limited
to `image/*` and PDF. (Previously: Form, list, and kanban required Binary attachment and
filename widgets.)

#### Scenario: Payment Vouchers views omit Binary widgets

- GIVEN Collections → Payment Vouchers
- WHEN a Collections User opens form, list, or kanban
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

- GIVEN a Collections User creates a voucher via ORM without `seller_id`
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
company, same seller, and `open` or `submitted`; assign to a `proposal`, `closed`, or
`cancelled` sheet MUST fail. Write of `seller_id` on an existing voucher MUST NOT
auto-assign. The system MUST NOT backfill existing unassigned vouchers. List Action and
explicit sheet create remain available when auto-create is OFF (see collection-sheets).
(Previously: Explicit `sheet_id` honored only when the target was `open`.)

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

#### Scenario: Explicit sheet_id honored when submitted

- GIVEN a submitted same-seller same-company sheet
- WHEN a voucher is created with that enabled `seller_id` and explicit `sheet_id`
- THEN the voucher MUST be assigned to that submitted sheet

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
review field set, including `retention_kind`. Current columns MUST remain the editable
copy. Provenance MUST NOT include `document_id`, `partner_id`, customer identification,
`seller_id`, attachment, or base64, and MUST NOT copy with the voucher. Cash-deposit MAY
store `voucher_number` and `voucher_date` in all three layers even when UI hides them.
Voucher write MUST reject provenance keys after create. (Previously: Review field set
omitted `retention_kind`.)

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

#### Scenario: retention_kind stamps all three layers

- GIVEN an all-new `retention_certificate` payment whose nests include `retention_kind`
- WHEN create completes
- THEN current, `seller_retention_kind`, and `ocr_retention_kind` (when `raw_ocr` is
  present) MUST persist that kind

### Requirement: MCP nested provenance on all-new create

`create_collection_allocation` MUST require nested `seller_confirmed` and MAY accept
nested `raw_ocr` with the same typed keys as current fields, including `retention_kind`
and the seven `document_type` codes. Voucher fields MUST be derived from
`seller_confirmed`. Amounts in those nests MUST accept decimal strings. Explicit JSON
`null` or empty string on optional nest fields MUST be treated as omit. When `raw_ocr`
is present, it MUST persist as submitted; when omitted or null, `ocr_*` MUST stay empty.
Stamp `seller_*` always on all-new create. Reject `unsupported` and non-positive
`seller_confirmed` amount. Seller-declared `cash` MUST succeed with `raw_ocr` omitted or
null. UI/ORM create without nests MUST remain allowed. Malformed nests, raw without
seller, or seller≠ derived current (minus `document_id`) MUST fail the batch with no
writes. Exact same-company, same-seller `document_id` reuse MUST require
`seller_confirmed` fields equal to the stored voucher (else generic conflict), MUST
ignore `raw_ocr` with no provenance mutation, and MUST continue to allocation.
(Previously: Four-type nests;
`retention_kind` was an unknown key; cash-without- proof and decimal-string amounts were
not named.)

#### Scenario: Unchanged seller confirmation

- GIVEN unused `document_id`s and required `seller_confirmed`
- WHEN all-new create runs
- THEN seller-confirmed and current MUST be equal
- AND `seller_*` MUST be stamped

#### Scenario: Seller correction with optional raw

- GIVEN `raw_ocr` differs from `seller_confirmed`
- WHEN all-new create runs
- THEN raw MUST persist unchanged
- AND seller-confirmed and current MUST contain the correction

#### Scenario: Seller-only nest stamps seller fields

- GIVEN MCP create with `seller_confirmed` and no `raw_ocr`
- WHEN all-new create completes
- THEN `seller_*` MUST be stamped
- AND `ocr_*` MUST stay empty

#### Scenario: UI create without nests leaves empty provenance

- GIVEN UI or ORM create with neither `raw_ocr` nor `seller_confirmed`
- WHEN create completes
- THEN raw and seller-confirmed MUST be empty
- AND current payment fields MUST persist as submitted

#### Scenario: Bad provenance fails the batch

- GIVEN a payment with raw-only, malformed, or mismatched nests
- WHEN `create_collection_allocation` runs
- THEN the call MUST fail with no writes

#### Scenario: Exact replay ignores provenance nests

- GIVEN every submitted `document_id` already exists in the same company for the calling
  seller, with or without stored provenance
- WHEN retried with the same `seller_confirmed` fields and a different or omitted `raw_ocr`
- THEN matching vouchers MUST return unchanged
- AND provenance and snapshots MUST NOT be written, backfilled, or mutated

#### Scenario: Cash dump without raw_ocr

- GIVEN a `cash` `seller_confirmed` with decimal-string `amount` and `raw_ocr` omitted
  or JSON `null`
- WHEN all-new create runs
- THEN `seller_*` MUST be stamped, `ocr_*` MUST stay empty, and the voucher MUST persist

#### Scenario: Explicit null optional nest fields are omit

- GIVEN `seller_confirmed` with unused typed fields set to JSON `null`
- WHEN all-new create runs
- THEN those fields MUST be treated as omitted
- AND MUST NOT fail as unknown or required values

### Requirement: Immutable review snapshots and ACL

MUST store immutable Document Review snapshots (revision, reviewer, time, decision,
current payment fields). Collections Users MUST read snapshots for allowed companies and
MUST NOT write or unlink, or sudo; plain internal users get no access. Snapshots MUST
follow voucher
company isolation. Form Validate by Seller MUST NOT append snapshots. Snapshot
`decision` MUST stay `approved`\|`rejected`. (Previously: Form Approve and Reject MUST
NOT append snapshots.)

#### Scenario: Collections Users read history without client mutation

- GIVEN a Collections User and snapshots of an allowed-company voucher
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
(default ON), and allowed document types (all nine catalog codes). Settings action and
menu labels MUST be **Collection Settings**. An empty enabled-seller list MUST mean none
for NEW work. All nine types MUST start enabled. Unsupported MUST remain independently
configurable. Saving these fields MUST NOT clear `document_review_enabled`. (Previously:
Defaults enabled seven catalog codes.)

#### Scenario: Collection Settings labels

- GIVEN the module is installed
- WHEN an internal Settings admin opens Collections settings
- THEN the action and menu labels MUST be Collection Settings

#### Scenario: Empty enabled sellers means none for new work

- GIVEN a company with no enabled sellers
- WHEN a new voucher is created via UI, ORM, import, or MCP
- THEN the create MUST be rejected with no write

#### Scenario: Defaults enable auto-create and all nine types

- GIVEN a fresh install or a company with no prior Collection Settings
- WHEN settings are read
- THEN `auto_create_sheet` MUST be ON
- AND `bank_transfer`, `check`, `echeck`, `cash_deposit`, `retention_certificate`,
  `cash`, `unsupported`, `seller_deposit`, and `seller_commission` MUST all be enabled

#### Scenario: Unsupported is configurable

- GIVEN Unsupported is disabled for the company
- WHEN a new voucher is created with `document_type` `unsupported`
- THEN the create MUST be rejected
- AND existing `unsupported` vouchers MUST remain visible

### Requirement: Company ownership of vouchers

Every voucher MUST have a required company. Users MUST see and operate only vouchers of
companies they are allowed, and only as Collections Users.

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
voucher MUST pass the same gates. Exact same-company, same-seller MCP replay with
matching payment fields is exempt (see MCP).

#### Scenario: ORM and import create require an enabled seller

- GIVEN a seller not on the company's enabled list
- WHEN a voucher is created via ORM or import with that seller
- THEN the create MUST be rejected with no write

#### Scenario: UI create offers only enabled sellers and allowed types

- GIVEN a company with a non-empty enabled-seller list and a subset of types enabled
- WHEN a Collections User opens a new Payment Vouchers form
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

Existing vouchers MUST stay visible and operable if their seller is later disabled. MUST
NOT hide or delete them for that reason. (Previously: Operable scenario used `pending`
Approve/Reject.)

#### Scenario: Disabled-seller voucher stays visible

- GIVEN a voucher whose seller is later removed from the enabled list
- WHEN an allowed-company user opens Payment Vouchers
- THEN that voucher MUST still be listed

#### Scenario: Disabled-seller voucher remains operable

- GIVEN a `draft` voucher whose seller is later disabled
- WHEN Validate by Seller runs without changing seller or type
- THEN `validated_seller` MUST persist and the voucher MUST NOT be deleted

### Requirement: Cross-company document_id reject not replay

`document_id` uniqueness MUST remain global among non-null values. When a new write
collides with another company's `document_id`, the system MUST reject it (MUST NOT
replay) and MUST NOT disclose that voucher's id or name. A user who can read both
companies MUST NOT receive the other company's voucher as an MCP replay via
`create_collection_allocation`. (Previously: Multi-company MCP replay named
`create_collection_vouchers`.)

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

Each voucher MAY have `allocation_id`. Write of `allocation_id` MUST be refused unless
current and target (if set) are both `draft` or unset. Unlink MUST be allowed when
voucher `state` is `draft` and `allocation_id` is unset or `draft`. Unlink MUST be
refused when allocation is `confirmed`. Removing a voucher from a draft allocation MUST
NOT project voucher amounts onto residual. Residual MUST remain
`total_debt − total_applied`. MUST NOT refuse unlink because leftover-voucher residual
would be `< 0`. Invoice lines MUST NOT be auto-edited. All three voucher states MAY be
allocated. (Previously: Unlink when voucher `state` is `pending`; projected residual −
voucher amount `< 0` refused.)

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
- THEN the system MUST allow the delete and MUST NOT refuse because leftover-voucher
  residual would change

#### Scenario: Draft unlink MUST NOT use leftover-voucher residual

- GIVEN a draft voucher on a draft allocation
- WHEN the voucher is deleted
- THEN unlink MUST succeed, invoice lines MUST NOT be auto-edited, and residual MUST
  stay debt − applied (MUST NOT ± voucher amount)

### Requirement: Partner write follows allocation

When `partner_id` changes, the system MUST NOT auto-compute or auto-write
`allocation_id`. An allocated voucher MUST be unassigned before Customer MAY change; a
`partner_id` write while `allocation_id` is set MUST raise `UserError` with no persist.
MUST NOT `sudo()`. Same-value `partner_id` MUST NOT recompute allocation. `confirmed`
current allocation MUST refuse the move with no field change. While the sheet is `open`
and the voucher is unassigned, a `draft` or `validated_seller` voucher MAY change
Customer; a `validated_collections` voucher MUST refuse (approved money fields are
frozen). (Previously:
Customer change auto-attached the unique draft same-sheet allocation or left the voucher
unallocated with chatter.)

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

- GIVEN an open-sheet unallocated voucher in `draft` or `validated_seller`
- WHEN `partner_id` is written to another customer
- THEN the write MUST succeed and `state` MUST stay unchanged

#### Scenario: Fully applied source no longer auto-moves

- GIVEN an open-sheet voucher on a draft allocation whose residual is 0
- WHEN `partner_id` is written to another customer without unassigning
- THEN MUST raise `UserError` and both fields MUST be unchanged

### Requirement: Voucher partner-allocation constrain

When `allocation_id` is set, voucher `partner_id` MUST equal that allocation's
`partner_id` after any write of `partner_id` or `allocation_id`. A mismatch MUST raise
`UserError` with no persist.

#### Scenario: Constrain mismatch refused

- GIVEN a voucher and an allocation whose partners differ
- WHEN `allocation_id` is written without matching `partner_id` in the same vals
- THEN the write MUST be refused
- AND stored `partner_id` and `allocation_id` MUST be unchanged

### Requirement: Internal collection payment helpers

Internal `_collection_*` helpers on `muk_mcp.mixin` MUST remain (parse payment vals,
attachment nest, provenance nests, create vouchers, submit-order payload,
classify/replay/conflict, require internal seller). They MUST NOT be registered as MCP
tools. `create_collection_allocation` MUST reuse them. Payment items MUST omit
`customer_identification`; helpers MUST take top-level identification and replicate it
per payment. Exact same-company `document_id` set of the calling seller with matching
payment fields MUST be reusable by allocation (continue; MUST NOT voucher-only
early-return). Partial overlap, other-company or other-seller hits, and changed payment
fields MUST stay generic conflict with no writes. Optional nested `attachment` and
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

Upgrade SQL MUST remap `collection.voucher.state` before ORM browse: `pending`→`draft`,
`approved`→`validated_collections`, `rejected`→`draft`. Leftover old keys MUST collapse.
MUST NOT keep voucher `rejected`.

#### Scenario: Remap before ORM

- GIVEN rows in `pending`, `approved`, `rejected`
- WHEN this upgrade runs
- THEN they MUST be `draft`, `validated_collections`, `draft`
- AND ORM MUST NOT see leftover old keys

### Requirement: Sheet-state voucher field guards

Voucher membership (`sheet_id` add, remove, or reassign) and voucher business fields
MUST be writable while the sheet is `open` or `submitted` (or the voucher is
unassigned), except the frozen money fields of a `validated_collections` voucher and the
allocation and receipt-row sheet constraints. When the sheet is `proposal`, `closed`, or
`cancelled`, those writes MUST
raise `UserError` with no persist, including via form or RPC. The membership freeze
`UserError` text MUST remain
`Closed collection sheets cannot change membership. Reopen first.` Chatter MUST remain
writable. Partner-allocation constrain MUST still apply. (Previously: Writable only
while `open`; freeze while `proposal`, `closed`, or `cancelled`.)

#### Scenario: Open membership and business fields writable

- GIVEN a voucher on an open sheet
- WHEN `sheet_id` is cleared or a business field is written lawfully
- THEN the write MUST persist

#### Scenario: Submitted membership and business fields writable

- GIVEN a voucher on a submitted sheet
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

### Requirement: Catalog XMLIDs and 19.0.1.40.0 allow-list union

The catalog MUST include exactly these nine codes, each with a stable XMLID:

| Code                    | XMLID                                            |
| ----------------------- | ------------------------------------------------ |
| `bank_transfer`         | `collection.document_type_bank_transfer`         |
| `check`                 | `collection.document_type_check`                 |
| `cash_deposit`          | `collection.document_type_cash_deposit`          |
| `unsupported`           | `collection.document_type_unsupported`           |
| `echeck`                | `collection.document_type_echeck`                |
| `cash`                  | `collection.document_type_cash`                  |
| `retention_certificate` | `collection.document_type_retention_certificate` |
| `seller_deposit`        | `collection.document_type_seller_deposit`        |
| `seller_commission`     | `collection.document_type_seller_commission`     |

Voucher `document_type`, `ocr_document_type`, `seller_document_type`, and review
snapshot type Selection MUST include the same nine codes, sourced from the shared
`DOCUMENT_TYPE_SELECTION` tuple. `COLLECTION_TYPE_CODES` MUST keep following
`DOCUMENT_TYPE_CODES` so catalog unions cover every Selection code. Upgrade to
`19.0.1.40.0` MUST union the then-seven codes onto every company’s
`allowed_document_type_ids` and MUST NOT remove custom extra types. Upgrade to
`19.0.1.43.0` MUST union all eight codes onto every company via
`_collection_enable_all_document_types` and MUST NOT remove extras. Upgrade to
`19.0.1.48.0` MUST union all nine codes onto every company via
`_collection_enable_all_document_types` and MUST NOT remove extras. Manifest MUST be
`19.0.1.48.0`. `migrations/19.0.1.42.0/` MUST NOT exist. `migrations/19.0.1.49.0/` MUST
NOT exist. Empty-only seed MUST NOT be the upgrade path. New companies MUST start with
all nine enabled. MCP write MUST still reject `unsupported`, and MUST NOT accept
`seller_commission` from any caller: only Confirm mints it. (Previously: Eight rows,
without `seller_commission`. Before that: Exactly seven catalog codes; last allow-list
union was `19.0.1.40.0`.)

#### Scenario: Seven catalog XMLIDs exist

- GIVEN the module at `19.0.1.40.0`
- WHEN catalog records are inspected
- THEN the seven codes and XMLIDs above except `seller_deposit` and `seller_commission`
  MUST exist
- AND `UNIQUE(code)` MUST still hold

#### Scenario: Upgrade unions without dropping extras

- GIVEN a company whose allow-list has the prior four types plus a custom extra
- WHEN upgrade to `19.0.1.40.0` runs
- THEN `echeck`, `cash`, and `retention_certificate` MUST be linked
- AND the custom extra MUST remain

#### Scenario: New company starts with seven types

- GIVEN a company created after the seven-type catalog and before `seller_deposit`
- WHEN `allowed_document_type_ids` is read at that version
- THEN those seven catalog codes MUST be enabled

#### Scenario: Eight catalog XMLIDs exist

- GIVEN the module at `19.0.1.43.0`
- WHEN catalog records are inspected
- THEN the eight codes and XMLIDs above except `seller_commission` MUST exist
- AND `UNIQUE(code)` MUST still hold

#### Scenario: Upgrade to 19.0.1.43.0 unions seller_deposit

- GIVEN a company whose allow-list has the seven prior types plus a custom extra
- WHEN upgrade to `19.0.1.43.0` runs
- THEN `seller_deposit` MUST be linked
- AND the custom extra MUST remain
- AND `migrations/19.0.1.42.0/` MUST NOT exist

#### Scenario: New company starts with eight types

- GIVEN a company created after `19.0.1.43.0` and before `seller_commission`
- WHEN `allowed_document_type_ids` is read at that version
- THEN those eight catalog codes MUST be enabled

#### Scenario: Nine catalog XMLIDs exist

- GIVEN the module at `19.0.1.48.0`
- WHEN catalog records are inspected
- THEN the nine codes and XMLIDs above MUST exist
- AND `UNIQUE(code)` MUST still hold

#### Scenario: Ninth code present after upgrade

- GIVEN a company whose allow-list predates this change
- WHEN the module is upgraded
- THEN `seller_commission` MUST be allowed for that company
- AND every previously allowed code MUST remain allowed

#### Scenario: Upgrade to 19.0.1.48.0 unions seller_commission

- GIVEN a company whose allow-list has the eight prior types plus a custom extra
- WHEN upgrade to `19.0.1.48.0` runs
- THEN `seller_commission` MUST be linked
- AND the custom extra MUST remain
- AND `migrations/19.0.1.49.0/` MUST NOT exist

#### Scenario: New company allows all nine

- GIVEN a newly created company
- WHEN its allow-list is read
- THEN all nine catalog codes MUST be present

#### Scenario: MCP callers cannot mint a commission

- GIVEN an internal MCP caller
- WHEN any write tool is called with `document_type` `seller_commission`
- THEN MUST raise `UserError`
- AND no voucher MUST persist

### Requirement: Sentinel partner for customerless vouchers

The system MUST seed two noupdate sentinel partners: XMLID
`collection.partner_seller_deposit` (name `Seller Deposit`) and
`collection.partner_seller_commission` (name `Seller Commission`), both with
`company_id` unset, reachable through `_seller_deposit_partner()` and
`_seller_commission_partner()`. Seeding MUST be idempotent. `partner_id` MUST remain
required. Voucher create MUST stamp the sentinel matching `document_type` for every code
in that type→sentinel map, MUST refuse a `customer_identification`, and MUST refuse a
`partner_id` that is any partner other than that type's sentinel. Codes outside the map
MUST keep requiring a real customer `partner_id`. (Previously: One sentinel for
`seller_deposit`, stamped by a `seller_deposit`-only `_apply_seller_deposit_partner`.
Before that: Every voucher required a real customer partner; no remittance sentinel.)

#### Scenario: Deposit stamps sentinel

- GIVEN a lawful `seller_deposit` create
- WHEN persist completes
- THEN `partner_id` MUST be the sentinel
- AND MUST NOT be empty

#### Scenario: Customer identification refused

- GIVEN `create_seller_deposit` or ORM create of `seller_deposit`
- WHEN a customer identification or non-sentinel `partner_id` is supplied
- THEN MUST refuse with no write

#### Scenario: Commission stamps its own sentinel

- GIVEN a `seller_commission` voucher created with no `partner_id`
- WHEN create completes
- THEN `partner_id` MUST be `collection.partner_seller_commission`
- AND MUST NOT be the `seller_deposit` sentinel

#### Scenario: Customer partner refused on a commission

- GIVEN a `seller_commission` voucher created with a real customer `partner_id`
- WHEN create runs
- THEN MUST raise `UserError`
- AND no voucher MUST persist

#### Scenario: Sentinel seeding is idempotent

- GIVEN both sentinels already exist
- WHEN the seed functions run again
- THEN no duplicate partner MUST be created

### Requirement: Receipt values reverse relation and replaced_amount

Each voucher MUST expose `receipt_value_ids` as the inverse of
`collection.receipt.value` and a `replaced_amount` equal to Σ replacement `replace`
minus Σ `reverse` for that voucher as cash. Unassigned remittance MUST still satisfy
`partner_id` required. (Previously: Core had no reverse receipt-value relation;
`replaced_amount` did not exist.)

#### Scenario: Reverse relation lists values

- GIVEN voucher V with values on two same-sheet receipts
- WHEN `receipt_value_ids` is read
- THEN both values MUST appear

#### Scenario: replaced_amount from ledger

- GIVEN cash voucher V with replace 40 and reverse 0
- WHEN `replaced_amount` is read
- THEN it MUST equal 40

### Requirement: Cash replacement trigger

Writing voucher `state` to `validated_collections` MUST run cash replacement when that
voucher's `document_type` is in `CASH_REPLACEMENT_TYPES`, which MUST be exactly
`seller_deposit` and `seller_commission`, and the sheet still allows receipt-value
writes. The trigger MUST be that write (including audited Document Review approve and
Confirm-time commission promotion). It MUST NOT require `document_review_enabled`. It
MUST NOT hook only `action_review_approve`. Companies with Document Review OFF MUST
still replace. Vouchers already at `validated_collections` MUST NOT re-trigger.
Replacement MUST be skipped when the sheet is missing or frozen. Replacement MUST NOT
run for any other code. (Previously: The trigger matched `seller_deposit` only.)

#### Scenario: Deposit validation replaces cash

- GIVEN a submitted sheet with replaceable cash and a `seller_deposit` in
  `validated_seller`
- WHEN `state` is written to `validated_collections`
- THEN replacement rows MUST persist per Collection Receipts
- AND receipt `amount_applied` MUST be unchanged

#### Scenario: Review-off companies still replace

- GIVEN Document Review OFF and a `seller_deposit` written to `validated_collections`
- WHEN that write completes
- THEN replacement MUST run
- AND MUST NOT raise because review is off

#### Scenario: Non-transition write does not re-replace

- GIVEN a `seller_deposit` already `validated_collections` with replacement rows
- WHEN a later write does not change `state` into `validated_collections`
- THEN no additional replacement row MUST be created

#### Scenario: Commission promotion replaces cash

- GIVEN a submitted sheet with replaceable `cash` receipt values and a
  `seller_commission` at `validated_seller`
- WHEN it is written to `validated_collections`
- THEN cash MUST be replaced by that commission per Collection Receipts
- AND `replace` ledger rows MUST name the commission as `deposit_voucher_id`

#### Scenario: Re-write does not re-replace

- GIVEN a `seller_commission` already at `validated_collections`
- WHEN `validated_collections` is written again
- THEN no additional replacement row MUST be created

### Requirement: MCP write create_seller_deposit

The system MUST expose `create_seller_deposit` via `@mcp_tool` on `muk_mcp.mixin`
(`category=write`, `registry=mcp`), method-discovered; MUST NOT add a DB tool record.
Calls MUST use the authenticated user and MUST NOT `sudo()` (except to read
`collection.mcp_trusted_seller_header`). Input MUST require integer
`seller_id`, amount, `voucher_number`, `voucher_date`, and MAY accept nested
`attachment`. The tool MUST NOT accept `customer_identification` or `sheet_id` from the
caller. It MUST resolve the seller's own `submitted` sheet, stamp the sentinel partner
and `document_type` `seller_deposit`, stamp `validated_seller`, pass that `sheet_id`
explicitly, and require new-work for that seller and `seller_deposit`. The tool MUST NOT
write `validated_collections`: the deposit slip is a reviewable designated proof, so the
voucher MUST stay `validated_seller` and MUST reach `validated_collections` only through
Document Review Approve. A deposit carrying designated proof MUST appear in
`get_review_queue` for its sheet. Callers that are not Collections Users MUST receive
`AccessError`.
Errors MUST be raised, never `{"error":...}`. Zero or more than one `submitted` sheet
MUST raise `UserError`. `create_collection_allocation` MUST remain customer-required and
`open`-sheet-only. (Previously: the tool wrote `validated_collections` under
`collection_audited_state` right after create, so the slip never reached the review
queue. Before that: No MCP path could create a no-customer remittance voucher.)

#### Scenario: Internal seller creates a deposit on submitted

- GIVEN a Collections User caller and an internal seller with exactly one `submitted`
  sheet
- WHEN `create_seller_deposit` runs with amount, number, date, and optional proof
- THEN one `seller_deposit` voucher MUST persist on that sheet
- AND `partner_id` MUST be the sentinel
- AND `state` MUST be `validated_seller`
- AND no `sudo()` MUST occur

#### Scenario: Deposit slip enters the review queue

- GIVEN a `create_seller_deposit` call carrying a nested `attachment`
- WHEN `get_review_queue` runs for that sheet
- THEN the deposit MUST be listed
- AND its `state` MUST still be `validated_seller`

#### Scenario: Review Approve promotes the deposit

- GIVEN a queued `seller_deposit` with designated proof
- WHEN Document Review Approve runs
- THEN `state` MUST become `validated_collections`
- AND cash replacement MUST run per Collection Receipts

#### Scenario: Open sheet is not the deposit target

- GIVEN an internal seller with one `open` sheet and zero `submitted` sheets
- WHEN `create_seller_deposit` runs
- THEN MUST raise `UserError`
- AND no voucher MUST persist

#### Scenario: Disabled type refused

- GIVEN `seller_deposit` is not allowed for the company
- WHEN `create_seller_deposit` runs
- THEN MUST raise `UserError` with no write

#### Scenario: Non-internal deposit refused

- GIVEN a portal or public caller
- WHEN `create_seller_deposit` runs
- THEN MUST raise `AccessError`
- AND no voucher MUST persist

#### Scenario: Allocation write still requires a customer

- GIVEN `create_collection_allocation` with `document_type` `seller_deposit` or omitted
  customer identification
- WHEN the call runs
- THEN MUST refuse
- AND MUST NOT persist a remittance voucher

### Requirement: Seller deposit form fields

Payment Vouchers form MUST show `voucher_number` and `voucher_date` for `seller_deposit`
on current, OCR, and seller-confirmed layers. Search MUST include a `seller_deposit`
document-type filter. `partner_id` MUST appear exactly once per arch. The system MUST
NOT add a second Customer field for remittance. (Previously: `voucher_number` /
`voucher_date` were hidden for types other than transfer, check extras, cash deposit,
and retention.)

#### Scenario: Number and date visible for seller_deposit

- GIVEN a `seller_deposit` voucher
- WHEN Payment Vouchers form opens
- THEN `voucher_number` and `voucher_date` MUST be visible on current, OCR, and
  seller-confirmed layers

#### Scenario: Search filter exists

- GIVEN Payment Vouchers search
- WHEN filters are inspected
- THEN a `document_type` filter for `seller_deposit` MUST exist

#### Scenario: Single partner_id in arch

- GIVEN Payment Vouchers form, list, and search arch
- WHEN `partner_id` nodes are counted
- THEN each arch MUST contain exactly one `partner_id`
