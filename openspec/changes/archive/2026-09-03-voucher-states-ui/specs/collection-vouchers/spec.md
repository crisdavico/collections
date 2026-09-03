# Delta for collection-vouchers

## ADDED Requirements

### Requirement: Voucher state SQL remap

Upgrade SQL MUST remap `collection.voucher.state` before ORM browse: `pending`→`draft`, `approved`→`validated_collections`, `rejected`→`draft`. Leftover old keys MUST collapse. MUST NOT keep voucher `rejected`.

#### Scenario: Remap before ORM

- GIVEN rows in `pending`, `approved`, `rejected`
- WHEN this upgrade runs
- THEN they MUST be `draft`, `validated_collections`, `draft`
- AND ORM MUST NOT see leftover old keys

## MODIFIED Requirements

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

### Requirement: Deferred integrations not required

Completeness MUST NOT require HTTP API, WhatsApp metadata, or agent calls. Each voucher MUST require a `res.partner` Customer (`partner_id`). Optional per-voucher image/PDF attachments are an allowed capability and MUST NOT be required for completeness of unrelated voucher features.
(Previously: Completeness scenario named approve or reject.)

#### Scenario: Completeness without deferred features

- GIVEN backend-only voucher management
- WHEN operators create, edit, or Validate by Seller
- THEN success MUST NOT depend on deferred integrations
- AND success MUST NOT require that vouchers have attachments

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

### Requirement: Payment Vouchers UI

MUST expose Collections → Payment Vouchers as the only create/edit surface (`view_mode` `list,form`; create and edit enabled). MUST `<delete>` stages kanban. MUST keep Reassign Customers kanban. Menu Payment Vouchers MUST stay `sequence=10`. Form MUST show non-clickable statusbar, **Validate by Seller** when `draft`, readonly `create_date`, type-specific payment fields, chatter/activity; MUST NOT show `received_date`, Approve/Reject, a Collections button, History, or payment-line tables. `partner_id` MUST have no bound-partner domain. Clearing `sheet_id` on an open member MUST unlink; closed-sheet membership writes MUST be rejected. MUST NOT expose sheet-form member list or Payment Lines.

| Surface | MUST |
| --- | --- |
| List visible | `name`, `create_date`, `sheet_id`, `seller_id`, `document_type`, `amount`, `state` |
| List hide | `partner_id`, `company_id`, `document_id` optional hide; `currency_id` column-invisible |
| Search | one filter per state; one per `document_type`; Created On `date="create_date"`; keep name/customer/seller/sheet |

(Previously: `kanban,list,form`; stages grouped by `state`; Approve/Reject when `pending`; list `partner_id` visible and `sheet_id` optional hide.)

#### Scenario: Menu and form behaviors

- GIVEN the module installed and a `draft` voucher
- WHEN Payment Vouchers form opens
- THEN list MUST show `name`, `create_date`, `sheet_id`, `seller_id`, `document_type`, `amount`, `state`
- AND form MUST show non-clickable statusbar, Validate by Seller, readonly `create_date`, type-specific fields, chatter; MUST NOT show `received_date`, Approve/Reject, Collections, History, or payment-line tables

#### Scenario: Kanban grouped by state

- GIVEN Payment Vouchers
- WHEN views load
- THEN stages kanban MUST NOT exist, `view_mode` MUST be `list,form`, and Reassign Customers kanban MUST remain

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
- THEN one filter per voucher state and per `document_type` MUST exist, and Created On MUST be a date filter on `create_date`

#### Scenario: UI create_date visibility

- GIVEN an existing voucher
- WHEN list, search, or form is opened
- THEN readonly `create_date` MUST be visible and not editable

#### Scenario: Customer field has no domain

- GIVEN Payment Vouchers list, search, form, or Reassign kanban
- WHEN Customer is opened
- THEN the field MUST be `partner_id` with no bound-connector domain

#### Scenario: sheet_id on list form search

- GIVEN an existing voucher with or without a sheet
- WHEN list, form, or search is opened
- THEN list MUST show visible `sheet_id`, form editable `sheet_id`, search field and group-by
- AND Reassign kanban MUST NOT show `sheet_id` as a card field

#### Scenario: Clear sheet_id unlinks open membership

- GIVEN a voucher assigned to an open sheet
- WHEN `sheet_id` is cleared on the form and saved
- THEN the voucher MUST be unassigned and the sheet MUST persist

#### Scenario: Closed-sheet unlink denied

- GIVEN a voucher assigned to a closed sheet
- WHEN `sheet_id` is cleared or changed on the form
- THEN the write MUST be rejected and membership MUST be unchanged

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

When `partner_id` changes, the system MUST compute `allocation_id` before persist and MUST write `partner_id` and `allocation_id` in the same vals (per record when outcomes differ). MUST NOT `sudo()`. While the sheet is `open`, any voucher state MAY change Customer. Same-value `partner_id` MUST NOT recompute allocation. `confirmed` current allocation MUST refuse the move with no field change. Draft source MUST NOT refuse because residual is 0 or because leftover-voucher residual would be `< 0`. MUST attach the unique draft same-sheet allocation for the new partner without leftover-voucher residual or `residual_reason` checks; otherwise MUST leave unallocated and MUST post chatter for that outcome.
(Previously: Last scenario named `approved`/`rejected` vouchers; projected residual − voucher amount `< 0` refused.)

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

- GIVEN an open-sheet voucher in `draft`, `validated_seller`, or `validated_collections` with no blocking residual
- WHEN `partner_id` is written to another customer
- THEN the write MUST succeed and `state` MUST stay unchanged
