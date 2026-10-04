# Tasks: Document Review editable OCR prefill

## Phase 1: Spec + RED tests

- [x] 1.1 Delta `openspec/specs/document-review/spec.md` (and live spec).
- [x] 1.2 Rewrite Document Review OWL + approve persistence tests (RED).
- [x] 1.3 Flip ACL internal-approve amount assertion.

## Phase 2: GREEN OWL

- [x] 2.1 Helpers: `initDraftFromOcr`, `buildApproveVals`.
- [x] 2.2 Action JS: draft, type from draft, `onFieldInput`, approve vals.
- [x] 2.3 XML one editable control; drop seller-warning; SCSS.

## Phase 3: GREEN server + version

- [x] 3.1 `_editable_review_vals` + apply before `_write_review_decision`.
- [x] 3.2 Manifest `19.0.1.38.0`; AGENTS + company-migration tests; no migrate folder.
- [x] 3.3 `invoke test -m collection --mode=update`; scoped pre-commit; module already
      upgraded during tests; `invoke start` to restore the stack.
