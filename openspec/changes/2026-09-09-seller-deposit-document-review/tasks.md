# Tasks: Seller deposit reaches Document Review

## Phase 1: Spec + RED tests

- [x] 1.1 Delta `openspec/specs/collection-vouchers/spec.md` (and live spec).
- [x] 1.2 Deposit tests: `validated_seller` outcome; slip lands in `get_review_queue`;
      Review Approve promotes and replaces cash; source no longer auto-promotes.

## Phase 2: GREEN server

- [x] 2.1 Drop the audited `validated_collections` write in
      `tools/collection_seller_deposit.py`.
- [x] 2.2 Tool `description` + docstring stop advertising the auto-validate.

## Phase 3: Version + verify

- [x] 3.1 Manifest `19.0.1.47.0`; AGENTS + company-migration tests; no migrate folder.
- [x] 3.2 `invoke test -m collection --mode=update`; scoped pre-commit.
