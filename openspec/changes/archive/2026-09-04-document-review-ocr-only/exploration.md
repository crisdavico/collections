## Exploration: OCR-only Document Review client

### Current State

Document Review is a sheet-scoped OWL client (`collection.document_review`) over
`collection.voucher`. Queue eligibility is `validated_seller` + designated proof +
open sheet. Provenance copies `ocr_*` / `seller_*` of `_REVIEW_EDITABLE_FIELDS`
already exist (`copy=False`; `write()` rejects those keys after create).

**Queue payload** (`_review_queue_payload`) already includes current typed payment
fields plus every `ocr_*` and `seller_*` copy. Empty provenance stays empty (amount
`0.0`, other keys `False`). There is **no** `seller_changed_fields` key anywhere in
the addon.

**OWL three-way UI** (`document_review_action.xml`): each field is three controls in
one `.slot` — readonly OCR, readonly seller, editable current (`t-on-input` /
`t-on-change` → `onFieldInput`). Typed groups use `_layerHasDocumentType`, which
ORs `document_type`, `ocr_document_type`, and `seller_document_type`, so a type
change already shows both bank-transfer and check blocks. `document_id` is hidden.
Empty provenance still binds (no `t-if` on OCR/seller presence).

**Approve** sends `buildApproveVals(this.current)` (current keys only; skips
`ocr_*`/`seller_*`). Server `_editable_review_vals` keeps those keys, then
`_write_review_decision` **writes them onto current** before stamping
`validated_collections` and snapshotting **current**. Empty `vals` already snapshots
current unchanged (`test_document_review_approve_empty_vals_snapshots_current`).
Correction tests (`test_reviewer_correction_matches_snapshot_current_only`,
`test_approve_persists_check_fields`, `test_approve_persists_cash_deposit_fields`)
require the rewrite.

**Payment Voucher form** (must stay unchanged): notebook Current / Raw OCR / Seller
Confirmed. Current is editable; provenance pages are `readonly="1"`. Typed
`invisible=` on provenance pages is `(layer_type != X) and (document_type != X)`.
Covered by `tests/test_collection_ui.py` (dirty on another agent — do not edit).

**Tests** in `tests/test_collection_document_review.py` lock three-way OWL
(`test_owl_keeps_type_visibility_hides_document_id_and_shows_provenance` asserts
editable `current.amount`), `buildApproveVals` sending current keys, queue
provenance, and correction persistence. There is no Hoot/JS unit suite; OWL is
asserted by reading source.

**SCSS**: `--rose` is used for leftover `.btn.no` (old Reject), not field warnings.
No inline-warning styles exist.

Canonical spec `openspec/specs/document-review/spec.md` still requires typed
**editable** current fields, three-way side-by-side, and “corrections MUST persist”
on approve.

### Affected Areas

- `openspec/specs/document-review/spec.md` — MODIFY three-way + editable +
  correction-persistence requirements (delta later under this change).
- `tests/test_collection_document_review.py` — failing coverage first (strict TDD):
  `seller_changed_fields`, OCR-only OWL, no current edits, approve does not rewrite
  current; rewrite existing three-way / `buildApproveVals` / correction tests.
- `models/collection_voucher.py` — compute `seller_changed_fields` on
  `_review_queue_payload`; stop applying client `vals` onto current on approve.
  Keep `ocr_*`/`seller_*`/current payload keys and snapshot-of-current persistence.
- `static/src/document_review/document_review_action.xml` — one readonly `ocr_*`
  control per field; drop seller and current widgets; inline warning with seller
  value; dual typed groups from OCR ∪ seller type.
- `static/src/document_review/document_review_action.esm.js` — drop `onFieldInput`;
  stop `buildApproveVals` rewrites; type getters from OCR ∪ seller (not current).
- `static/src/document_review/document_review_helpers.esm.js` — approve payload
  without current edits (empty/`False` vals or omit).
- `static/src/document_review/document_review_action.scss` — warning styles.
- `__manifest__.py` — later bump from whatever is current (dirty tree is
  `19.0.1.35.0`; plan said `19.0.1.36.0`). No DB migration (no stored fields).
- **Out of scope / do not touch:** Payment Voucher form
  (`views/collection_views.xml`), `tests/test_collection_ui.py`, leftover
  `openspec/changes/collection-receipts/`, other dirty files on the parallel agent.

### Approaches

1. **Server-computed `seller_changed_fields` + OCR-only OWL + ignore client vals**
   — Payload adds a dict (or name list) of typed `ocr_*` vs `seller_*` diffs.
   Empty-empty (legacy) omitted; seller empty after a non-empty OCR value included
   with explicit empty. OWL renders `ocr_*` plus warning from that map. Approve
   ignores/refuses extra_vals so current stays authoritative; snapshot still reads
   current after the state write.
   - Pros: one equality rule; OWL stays dumb; matches product; empty-vals approve
     path already proven.
   - Cons: must rewrite several existing review tests; must define empty
     normalization (False/`""`/amount `0.0`).
   - Effort: Medium

2. **Client-only comparison** — OWL diffs `ocr_*` vs `seller_*` locally; no payload
   key; server approve still ignore vals.
   - Pros: smaller Python surface.
   - Cons: duplicates empty/legacy rules in JS; source-string tests cannot prove
     equality; drift vs MCP-stamped False vs `0.0`.
   - Effort: Medium

3. **Keep three-way, add warnings** — leave editable current; overlay seller diffs.
   - Pros: smallest OWL delete.
   - Cons: contradicts confirmed product (OCR-only, no current controls, no
     rewrite).
   - Effort: Low (rejected)

### Recommendation

Approach 1.

- Add `seller_changed_fields` in `_review_queue_payload` by comparing each name in
  `_REVIEW_EDITABLE_FIELDS` (`ocr_{name}` vs `seller_{name}`). Treat False / `None`
  / `""` and monetary `0.0` as empty. Both empty → omit (legacy, no warning).
  Otherwise include the field with the **seller** value (False when seller
  changed-to-empty). Keep existing current/`ocr_*`/`seller_*` keys.
- OWL: one readonly `ocr_*` input per field; no seller column; no current
  `t-on-input`. If the field is in `seller_changed_fields`, show an inline warning
  containing the seller value (empty shown as empty, not omitted). Typed blocks:
  bank transfer iff OCR **or** seller type is `bank_transfer`; check iff OCR **or**
  seller type is `check`. Drop current type from `_layerHasDocumentType`.
- Approve: OWL must not send current edits (`{}` / omit). Server must **not** apply
  `_editable_review_vals` onto current (ignore or refuse non-empty vals). Snapshot
  still copies current after the audited state write — existing empty-vals test is
  the keep path.
- Form three-way notebook stays as-is. Manifest bump only at apply; no migration.

### Risks

- Existing Document Review tests currently **require** three-way editable current
  and correction rewrite; they will fail until rewritten in the same change.
- `test_collection_ui.py` (parallel-agent dirty) must keep passing without form
  edits — do not fold form three-way into this change.
- Monetary `0.0` cannot distinguish “legacy empty amount” from a genuine zero;
  follow today’s empty-provenance convention (`0.0` = empty).
- Parallel dirty `__manifest__.py` is `19.0.1.35.0`; bump at apply to next unused
  version, not a hardcoded `19.0.1.36.0` if the other change lands first.
- Ignoring vs refusing leftover client `vals`: ignoring is compatible with old OWL;
  refusing is fail-closed. Prefer ignore-empty-and-nonempty so current cannot be
  rewritten, and drop `buildApproveVals` current keys on the client.
- No stored-field change, but queue JSON shape grows; sanitizeQueueItem already
  copies unknown keys (`false` → `""`), which is what warnings need for empty
  seller values.

### Ready for Proposal

Yes. Confirmed product is implementable against current code: payload already has
layers; approve-without-vals already snapshots current; the work is a spec delta
(OCR-only + seller-diff warnings + no current rewrite), server diff map, OWL
simplification, and rewriting Document Review tests — not the Payment Voucher form.
