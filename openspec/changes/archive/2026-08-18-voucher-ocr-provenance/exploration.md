## Exploration: voucher-ocr-provenance

Odoo should store raw OCR and seller-confirmed payment fields as typed, read-only column
sets on `collection.voucher`, keep existing payment columns as the editable current
review copy, and append an immutable related-model snapshot on every Document Review
approve/reject. MCP stays additive: current top-level payment fields plus nested
`raw_ocr` and `seller_confirmed` objects. Exact replay ignores those nests.

**CodeGraph:** MCP `user-codegraph` was unavailable. `gentle-ai codegraph init --cwd` on
the collection git root failed with exit 127 (Windows npm `codegraph` shim; Linux `node`
missing). Investigation used Read/Grep on real paths below.

Git roots: collection addon is its own repo at `odoo/custom/src/private/collection`;
parent Doodba root is `/home/crisd/projects/seedian/seedian`. Planning cwd is the
collection repo.

### Current State

`collection.voucher` is one payment. Typed fields live once on the voucher:

| Role               | Fields                                                                                                                                                                          |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Identity / parties | `document_id`, `customer_identification`, `seller_id`, `sheet_id`                                                                                                               |
| Lifecycle          | `state`, `reviewed_by`, `reviewed_at` (last decision only)                                                                                                                      |
| Payment (current)  | `document_type`, `amount`, `from_account`, `to_account`, `voucher_number`, `voucher_date`, `check_number`, `check_bank`, `check_type`, `check_issue_date`, `check_payment_date` |
| Proof              | `message_main_attachment_id` + `attachment_rotation` (chatter; Binary widgets already gone in this tree)                                                                        |

There are **no** `ocr_*` / `seller_*` columns, **no** `fields.Json`, **no** snapshot
model, and **no** review-history One2many. `_REVIEW_EDITABLE_FIELDS` in
`models/collection_voucher.py` is exactly the payment typed set (not identity, not
attachment).

MCP `create_collection_vouchers` (`tools/collection_voucher.py`):

- Requires `customer_identification`, `seller_id`, non-empty `payments`.
- Each payment requires `document_id` + `document_type`; optional typed fields via
  `_PAYMENT_OPTIONAL_FIELDS`; optional nested `attachment`.
- All-new create is one savepoint: `Voucher.create(create_vals)` then chatter
  `message_post` sidecars. Current fields are whatever the top-level payment dict
  carried (Nebula’s effective extraction today).
- Exact replay (`_collection_replay_or_reject`) returns `{id,name,state,document_id}`
  and **does not write**. It already ignores customer, seller, attachment nests, and
  `sheet_id`. Unknown extra keys are ignored today (nests would be silently dropped).
- Fail-closed before write: in-call duplicate `document_id`, partial overlap, invalid
  type/check_type, bad attachment MIME/base64. `UniqueViolation` → invalidate + replay.
- No `sudo()`. ACL is caller env.

Document Review:

- Queue RPC `_review_queue_payload` returns **current** payment fields only.
- OWL (`static/src/document_review/document_review_action.xml`) is a single editable
  panel; type-specific visibility via `isBankTransfer` / `isCheck`.
- Approve sends `buildApproveVals` (`document_review_helpers.esm.js`) through
  `action_review_approve` → `_lock_and_ensure_review_eligible` (`FOR UPDATE`) →
  `_write_review_decision`. Empty/unchanged vals still approve. `document_id` in vals is
  stripped.
- Reject writes state/audit only (no field vals). Form `action_approve` /
  `action_reject` are a **separate** path (no field snapshot, no lock helper).
- Reopen: replacing designated proof resets `state` to `pending` and clears
  `reviewed_by` / `reviewed_at`. Terminal form reopen without a new proof is refused.

Security: `security/ir.model.access.csv` — `base.group_user` full CRUD on voucher and
sheet only. No `ir.rule`, no extra groups. Spec forbids dedicated groups/record rules on
vouchers; a **new** snapshot model can have its own ACL row.

Tests to extend: `tests/test_collection_mcp_tool.py`,
`tests/test_collection_document_review.py`, `tests/test_collection_acl.py`,
`tests/test_collection_ui.py`, plus voucher/payment create defaults. Manifest version
`19.0.1.13.0` with chatter migrate scripts already in `migrations/19.0.1.13.0/`.

Main specs: `openspec/specs/collection-vouchers/spec.md` (MCP, payment field contract,
internal CRUD, last-reviewer audit) and `openspec/specs/document-review/spec.md` (typed
editable fields, no `document_id` in OWL, approve persists corrections). Neither
mentions provenance or history.

Nebula (contract only; out of scope to implement): `map_payment` / `build_mcp_payments`
in `/home/crisd/projects/nebula/nebula-agent/src/agent/tools/collection_voucher.py` send
**effective** fields + `attachment`. Raw is `OcrResult.data`; seller-confirmed is
`_effective_extraction` (latest correction or raw). Nested provenance objects are
**not** sent yet. Typed extraction keys match Odoo payment columns (`document_type`,
amount, accounts, voucher/check dates). `document_id` and source base64 stay outside
extraction. Cash-deposit OCR may include `voucher_number` / `voucher_date` even though
Odoo UI hides those for `cash_deposit`.

Sibling changes: do **not** edit `openspec/changes/chatter-voucher-attachments/`
(attachments; keep Binary/chatter independent). `auto-assign-open-sheet` is archived as
`openspec/changes/archive/2026-08-18-auto-assign-open-sheet/` (leftover active folder
may still exist); keep independent.

### Affected Areas

- `models/collection_voucher.py` — typed `ocr_*` / `seller_*` fields; write guard;
  snapshot append from `_write_review_decision`; queue payload provenance
- `models/collection_voucher_review_snapshot.py` (new) + `models/__init__.py`
- `tools/collection_voucher.py` — nested schema, parse/validate/mismatch, stamp on
  all-new create only; replay unchanged
- `views/collection_views.xml` — three-way comparison + history list
- `static/src/document_review/document_review_action.xml` (+ helpers/JS) — side-by-side
  raw / seller / current; keep type-specific visibility and no `document_id`
- `security/ir.model.access.csv` — snapshot ACL
- `__manifest__.py` — bump past `19.0.1.13.0` (additive columns; no backfill migrate)
- `tests/test_collection_*.py` listed above
- `openspec/specs/collection-vouchers/spec.md` and `document-review/spec.md` (later
  deltas)

### Approaches

#### 1. Raw / seller storage

1. **Typed `ocr_*` / `seller_*` columns (same types as current fields)** — duplicate the
   `_REVIEW_EDITABLE_FIELDS` set twice; `copy=False`; UI `readonly="1"`.

   - Pros: Matches settled product; Monetary/Date/Selection validation; type-specific
     `invisible=` already used in `collection_views.xml`; comparable in OWL without JSON
     parsing; additive nulls for existing rows.
   - Cons: ~22 extra columns; form XML verbose.
   - Effort: Medium

2. **JSON / Jsonb blobs (`raw_ocr`, `seller_confirmed`)** — one blob each.
   - Pros: Fewer columns; schema can grow without migrate.
   - Cons: New pattern (this addon has zero Json fields; odoo-19 field guide here does
     not document `fields.Json`); weak typing vs Selection/Date/Monetary; OWL and form
     widgets cannot use stock `invisible=` on blob keys; harder mismatch compare vs
     top-level fields.
   - Effort: Medium (integration cost higher than column count suggests)

#### 2. Reviewer history

1. **Related snapshot model** (`collection.voucher.review.snapshot`) — One2many;
   voucher, revision, reviewer, timestamp, decision, full typed field set.

   - Pros: Matches settled immutable full-field snapshot; queryable; ACL per model;
     repeated reviews append; existing rows get zero rows (no fabricate).
   - Cons: Extra model + ACL + list view.
   - Effort: Medium

2. **Chatter-only** — post a note / tracking on approve.

   - Pros: No new model.
   - Cons: Not a typed full-field snapshot; not a first-class history UI; tracking is
     diffs of current fields only (`state` already tracked). Fails settled product.
   - Effort: Low

3. **JSON history field on the voucher** — append dicts on review.
   - Pros: One column.
   - Cons: Client can write the Json field under current voucher write ACL unless extra
     guards; no row-level unlink ACL; poor list UI.
   - Effort: Medium

#### 3. Current-field initialization (MCP create)

1. **Copy seller-confirmed → current on all-new create** (after requiring nested
   seller-confirmed == top-level effective fields).

   - Pros: Matches settled “current fields initialize from seller-confirmed”; one create
     dict; atomic with raw/seller stamp in the existing savepoint.
   - Cons: Parser must fail the batch if nests missing/malformed/mismatched when either
     nest is present.
   - Effort: Low–Medium (extend `_collection_parse_payment_vals`)

2. **Stamp current from top-level only; fill seller\_\* later**
   - Cons: Diverges if top-level and seller-confirmed ever differ; settled forbids that
     (seller-confirmed MUST equal top-level).
   - Effort: Low but wrong

Manual / omitted nests: leave `ocr_*` / `seller_*` null; current fields as today.

#### 4. MCP shape

1. **Nested objects** `raw_ocr` and `seller_confirmed` on each payment, same typed key
   set (`document_type`, amount, accounts, dates, checks). `document_id` and
   `attachment` stay top-level only.

   - Pros: Matches settled Nebula contract; no name collision with current fields; same
     ignore-on-replay pattern as `attachment`.
   - Cons: Schema/docs growth; must define omit vs null equality for mismatch.

2. **Flattened `ocr_*` / `seller_*` keys on the payment object**
   - Cons: 22 extra top-level keys; noisy schema; easier for agents to confuse with
     current fields.
   - Effort: Medium

Recommend nest names **`raw_ocr`** and **`seller_confirmed`** (snake_case like
`document_id`, `from_account`).

#### 5. UI

1. **Both voucher form and Document Review** — form notebook: Current (editable Payment
   group) | Raw OCR | Seller Confirmed | history list; OWL panel grows readonly
   raw/seller columns beside current inputs; same type-specific visibility; still hide
   `document_id`.

   - Pros: Matches settled “side by side” + “history from the voucher”.
   - Cons: OWL XML is already large; likely to blow the 400-line review budget if
     bundled with model+MCP.

2. **Form only** — OWL stays current-fields-only.

   - Cons: Reviewers comparing proof vs OCR would not see raw/seller in the tool they
     actually use.

3. **Document Review only**
   - Cons: History “from the voucher” would be missing on Payment Vouchers form.

#### 6. Snapshot ACL

1. **Read for `base.group_user`; create only via server context; no write/unlink** —
   CSV: `perm_read=1`, `perm_create=1`, `perm_write=0`, `perm_unlink=0`. Override
   `create` to require `collection_review_snapshot` context (same idea as
   `collection_audited_state`). `@api.private` append from `_write_review_decision`.
   `@api.ondelete` / write override to refuse. No `sudo()` (MCP tests forbid sudo on the
   write tool; keep the same discipline here). No new groups, no `ir.rule`.

   - Pros: Internal users can open history; RPC cannot mutate/delete; no sudo.
   - Cons: Guessable context flag still needs the create override.

2. **Read-only ACL + `sudo().create`**

   - Cons: sudo is a sharp edge in this addon’s MCP culture.

3. **Reuse voucher write ACL with readonly fields only**
   - Cons: Internal users can RPC-write `ocr_*` unless `write()` rejects those keys.
     Still required even with approach 1 for the voucher columns.

### Recommendation

Lock **typed columns + snapshot model + nested MCP + both UIs + context-gated snapshot
ACL**.

| Decision       | Choice                                                                                                                                                                                                                                           |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Raw / seller   | `ocr_*` and `seller_*` copies of `_REVIEW_EDITABLE_FIELDS`; `readonly` + `write()` reject after create; `copy=False`                                                                                                                             |
| Current fields | Unchanged names; MCP all-new copies seller-confirmed (validated equal to top-level)                                                                                                                                                              |
| History        | New `collection.voucher.review.snapshot`; append on `_write_review_decision` (approve **and** reject, including unchanged vals); revision sequence per voucher                                                                                   |
| MCP            | Additive nests `raw_ocr` / `seller_confirmed`; same typed keys; no `document_id`/attachment/base64 inside; malformed/mismatched/one-sided nests fail the batch **before** savepoint write; omitted both nests = empty provenance (manual MCP/UI) |
| Replay         | Existing exact-replay path: no parse-compare, no backfill, no mutation                                                                                                                                                                           |
| UI             | Form three-way + history list; OWL side-by-side using queue payload provenance                                                                                                                                                                   |
| ACL            | Snapshot read + gated create; no client write/unlink; voucher `write()` blocks provenance keys                                                                                                                                                   |
| Migration      | Bump to `19.0.1.14.0`; additive null columns; **no** data backfill                                                                                                                                                                               |
| Attachments    | Untouched; chatter change stays independent                                                                                                                                                                                                      |

**Do not reopen settled product.** One code fact that makes UI expensive (not unsafe):
OWL is a custom QWeb panel, not the voucher form, so three-way comparison is duplicated
work. Snapshot-on-Document-Review-only means **form Approve/Reject will not append
history** (different code path). That matches the settled “Document Review appends…”
wording; propose should state it explicitly.

Cash-deposit extra OCR keys (`voucher_number`, `voucher_date`) already exist as voucher
columns; store them in all three layers even if UI hides them for that type.

### Risks

- **400-line review budget:** model + 22 fields + MCP + OWL + tests will likely need
  chained PRs (model/MCP/ACL first, then form, then OWL).
- **Form vs Document Review history:** form `action_approve` will not create snapshots
  unless propose later expands scope.
- **Silent drop today:** current MCP ignores unknown keys; Nebula must not send nests
  until Odoo validates them (or Odoo ships first).
- **Mismatch equality:** omit vs `null` vs `""` must reuse `_PAYMENT_OPTIONAL_FIELDS`
  parsing or false rejects will fail whole batches.
- **Voucher write ACL:** `readonly=True` is UI-only; without a write guard, internal
  users can RPC-overwrite provenance.
- **Sibling chatter change:** `19.0.1.13.0` already owns attachment migrate; provenance
  must not touch `message_main_attachment_id` or nest `attachment`.
- **Existing rows:** raw/seller stay null; no fabricated snapshots — comparison UI must
  tolerate empty provenance.

### Ready for Proposal

Yes. Orchestrator should tell the user: exploration recommends typed `ocr_*` /
`seller_*` columns, a create-only snapshot model, nested MCP `raw_ocr` +
`seller_confirmed`, three-way UI on form and Document Review, additive migration with no
backfill, and exact replay left immutable. Next phase is `sdd-propose`.
