# Proposal: Document Review editable OCR prefill

## Intent

Document Review currently shows a readonly OCR value plus a seller-change warning, and
**Aprobar y seguir** ignores client edits. Reviewers need one editable field per payment
value, prefilled from OCR (current fallback), with approval saving those edits onto
current — never onto immutable `ocr_*`.

## Scope

### In Scope

- OWL: one editable control per typed field; drop seller-warning lines
- Prefill from `ocr_*` when non-empty, else unprefixed current
- Approve applies whitelist `_REVIEW_EDITABLE_FIELDS` onto current, then snapshots
- Rewrite Document Review tests; delta `document-review`
- Manifest bump `19.0.1.38.0` (no stored fields / no migrate)

### Out of Scope

- Payment Vouchers form three-way notebook
- Changing `ocr_*` / `seller_*` after create
- Reject RPC; Nebula; receipts; queue `seller_changed_fields` payload (keep)

## Capabilities

### Modified Capabilities

- `document-review`: OWL one editable OCR-prefilled control; Approve rewrites current
  from sanitized client vals; snapshots match corrected current.

## Approach

Client draft per queue item. Server `_editable_review_vals` strips non-current keys.
Lock, write current, then `_write_review_decision`. Empty/omit vals still approve
without rewriting.

## Affected Areas

| Area                                       | Impact   | Description                         |
| ------------------------------------------ | -------- | ----------------------------------- |
| `models/collection_voucher.py`             | Modified | Apply sanitized approve vals        |
| `static/src/document_review/*`             | Modified | Editable OCR-prefill OWL            |
| `tests/test_collection_document_review.py` | Modified | Persist edits; one editable control |
| `tests/test_collection_acl.py`             | Modified | Approve vals persist for internals  |
| `openspec/specs/document-review/spec.md`   | Modified | Delta in this change                |
| `__manifest__.py`, `AGENTS.md`             | Modified | `19.0.1.38.0`                       |

## Risks

| Risk                      | Likelihood | Mitigation                  |
| ------------------------- | ---------- | --------------------------- |
| Review tests require flip | High       | Same-change TDD rewrite     |
| Forged `ocr_*` / ids      | Med        | Whitelist current keys only |
| 400-line review budget    | Med        | Focused OWL + approve only  |

## Rollback Plan

Revert OWL, helpers, `_editable_review_vals`, tests, spec, manifest. Restore OCR-only
readonly plus ignore-vals. No DB reverse.

## Success Criteria

- [ ] One editable control per field, prefilled OCR then current
- [ ] No seller-warning / dual OCR+seller widgets in Document Review
- [ ] Approve writes current only; `ocr_*`/`seller_*` stay
- [ ] Snapshot matches corrected current
- [ ] Form three-way unchanged
- [ ] `invoke test -m collection --mode=update` passes
