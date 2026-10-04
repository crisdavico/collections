# Proposal: Seller deposit reaches Document Review

## Intent

`create_seller_deposit` creates the remittance voucher at `validated_seller` and then
immediately writes `validated_collections` under `collection_audited_state`. That write
is the only path to `validated_collections` outside Document Review, and it contradicts
the live `collection-vouchers` lifecycle table (`validated_collections` — Document
Review Approve only) and the tool's own requirement (`state` MUST be
`validated_seller`). The deposit slip is a reviewable proof: it MUST land in the sheet's
Document Review queue like every other typed voucher, and only Review Approve MUST
promote it.

## Scope

### In Scope

- `tools/collection_seller_deposit.py`: drop the audited `validated_collections` write;
  the tool returns the voucher at `validated_seller`
- Tool `description` and docstring stop advertising the auto-validate
- Delta + live `collection-vouchers` spec: the tool MUST NOT stamp
  `validated_collections`
- `tests/test_collection_mcp_seller_deposit.py`: `validated_seller` outcome,
  review-queue membership, approve promotes and replaces cash
- Manifest `19.0.1.47.0` (no stored fields / no migrate)

### Out of Scope

- Making the nested `attachment` required (a slip MAY be posted later via chatter)
- `CONFIRM_REVIEW_EXEMPT_TYPES` — `seller_deposit` stays non-exempt, so a sheet with an
  unreviewed deposit stays unconfirmable
- The replacement trigger, which already hooks the write into `validated_collections`
- Document Review eligibility (`validated_seller` + designated proof, unchanged)
- Creating a `seller_deposit` from the sheet form

## Capabilities

### Modified Capabilities

- `collection-vouchers`: MCP `create_seller_deposit` leaves the deposit at
  `validated_seller`; `validated_collections` stays Document Review Approve only.

## Approach

Delete the trailing `voucher.with_context(collection_audited_state=True).write(...)`.
Create already stamps `validated_seller` in the create vals, which `create` allows and
`_intercept_state_write` never sees. Cash replacement is unaffected: it triggers on the
write into `validated_collections`, which now happens at Review Approve.

## Affected Areas

| Area                                          | Impact   | Description                        |
| --------------------------------------------- | -------- | ---------------------------------- |
| `tools/collection_seller_deposit.py`          | Modified | No audited promote; description    |
| `tests/test_collection_mcp_seller_deposit.py` | Modified | `validated_seller`; queue; approve |
| `tests/test_collection_company_migration.py`  | Modified | `19.0.1.47.0` + leftover pin       |
| `openspec/specs/collection-vouchers/spec.md`  | Modified | Delta in this change               |
| `__manifest__.py`, `AGENTS.md`                | Modified | `19.0.1.47.0`                      |

## Risks

| Risk                                       | Likelihood | Mitigation                           |
| ------------------------------------------ | ---------- | ------------------------------------ |
| Deposit without a slip blocks Confirm      | Med        | Intended; slip attachable in chatter |
| Review OFF leaves the deposit unpromotable | Low        | Same as every other non-cash type    |
| Cash replacement never runs                | Low        | Approve-path replacement test        |

## Rollback Plan

Restore the audited write, the tests, the spec, the manifest. No DB reverse (no stored
fields, no migrate folder).

## Success Criteria

- [ ] `create_seller_deposit` returns and persists `validated_seller`
- [ ] A deposit with a slip appears in `get_review_queue` for its sheet
- [ ] Review Approve promotes it and runs cash replacement
- [ ] Confirm still blocks while the deposit is `validated_seller`
- [ ] `invoke test -m collection --mode=update` passes
