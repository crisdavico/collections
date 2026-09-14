# Tasks: Confirm cash review exemption

## Phase 1: Spec + RED tests

- [x] 1.1 Delta `openspec/specs/collection-sheets/spec.md` (and live spec).
- [x] 1.2 Sheet tests: cash `validated_seller` passes; `draft` cash blocks;
      `seller_deposit` `validated_seller` blocks; reviewed deposit passes.

## Phase 2: GREEN server

- [x] 2.1 `CONFIRM_REVIEW_EXEMPT_TYPES` in `collection_common`.
- [x] 2.2 `_vouchers_blocking_confirm()` + `action_confirm` naming offenders.

## Phase 3: Version + verify

- [x] 3.1 Manifest `19.0.1.45.0`; AGENTS + company-migration tests; no migrate folder.
- [ ] 3.2 `invoke test -m collection --mode=update`; scoped pre-commit.
