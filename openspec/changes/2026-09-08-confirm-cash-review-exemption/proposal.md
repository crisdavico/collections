# Proposal: Confirm cash review exemption

## Intent

Confirm demands `validated_collections` of every sheet member. Cash vouchers carry no
designated proof, so `get_review_queue` never lists them and Document Review can never
approve them — a sheet with any cash member is unconfirmable without an audited raw
write. Cash MUST be exempt from the review gate; `seller_deposit`, whose remittance slip
is reviewable, MUST NOT be.

## Scope

### In Scope

- `CONFIRM_REVIEW_EXEMPT_TYPES = frozenset({"cash"})` in `collection_common`
- `collection.sheet._vouchers_blocking_confirm()` + `action_confirm` gate
- `UserError` names the offending vouchers (matches Seller Close)
- Delta + live `collection-sheets` spec; sheet tests
- Manifest `19.0.1.45.0` (no stored fields / no migrate)

### Out of Scope

- Seller Close gate (`draft` members still block it)
- Document Review eligibility (`validated_seller` + designated proof, unchanged)
- Declare Cash gate (collected cash > 0 still needs `cash_declared_at`)
- Making `cash` reviewable, or exempting `cash_deposit` / any other type

## Capabilities

### Modified Capabilities

- `collection-sheets`: Confirm review gate exempts `CONFIRM_REVIEW_EXEMPT_TYPES` members
  at `validated_seller`; `draft` still blocks; error names offenders.

## Approach

`action_confirm` delegates the member scan to `_vouchers_blocking_confirm()`, which
requires `validated_collections` for every type except the exempt set, where
`_SELLER_DECIDED_STATES` (`validated_seller` or `validated_collections`) suffices.

## Affected Areas

| Area                                         | Impact   | Description                          |
| -------------------------------------------- | -------- | ------------------------------------ |
| `models/collection_common.py`                | Modified | `CONFIRM_REVIEW_EXEMPT_TYPES`        |
| `models/collection_sheet.py`                 | Modified | Confirm gate + named offenders       |
| `tests/test_collection_sheet.py`             | Modified | Cash pass/draft-block; deposit block |
| `tests/test_collection_company_migration.py` | Modified | `19.0.1.45.0` + leftover pin         |
| `openspec/specs/collection-sheets/spec.md`   | Modified | Delta in this change                 |
| `__manifest__.py`, `AGENTS.md`               | Modified | `19.0.1.45.0`                        |

## Risks

| Risk                            | Likelihood | Mitigation                        |
| ------------------------------- | ---------- | --------------------------------- |
| Exemption leaks to other types  | Low        | Frozen set; deposit triangulation |
| `draft` cash slips past Confirm | Med        | Explicit draft-blocks test        |
| Undeclared cash confirmed       | Low        | Declare Cash gate untouched       |

## Rollback Plan

Revert the constant, `_vouchers_blocking_confirm`, tests, spec, manifest. No DB reverse
(no stored fields, no migrate folder).

## Success Criteria

- [ ] `cash` at `validated_seller` confirms (with cash declared)
- [ ] `draft` `cash` still blocks Confirm
- [ ] `seller_deposit` at `validated_seller` still blocks Confirm
- [ ] `UserError` names the offending vouchers
- [ ] `invoke test -m collection --mode=update` passes
