# Proposal: Voucher OCR Provenance

## Proposal question round

Locked: typed columns; snapshot model; nested MCP; `_write_review_decision` snapshots
only (form Approve/Reject do not); Nebula contract only.

## Intent

Reviewers need typed raw OCR vs seller-confirmed vs current review copies, plus
immutable Document Review history. Current payment fields stay the editable copy.

## Scope

### In Scope

- `ocr_*`/`seller_*` of `_REVIEW_EDITABLE_FIELDS` (`copy=False`); no identity/attachment
  copies
- MCP nests `raw_ocr`/`seller_confirmed`; `document_id`/`attachment` outside; no base64
- All-new: seller-confirmed == top-level; current copies seller; bad/one-sided/mismatch
  fails the batch before write; omitted nests → null provenance
- Exact replay ignores nests; no backfill/mutation
- Snapshot on `_write_review_decision` (approve incl. unchanged **and** reject); reopen
  appends another revision; form `action_approve`/`action_reject` do **not** snapshot
- Three-way UI on form and Document Review; type-specific visibility; voucher history
- `write()` rejects provenance keys; snapshot read + gated create; no write/unlink/
  `sudo()`/new groups/`ir.rule`
- Existing rows: current kept; raw/seller null; no fabricated snapshots
- `19.0.1.14.0`; additive nulls; no backfill; leave chatter migrate scripts
- Cash-deposit `voucher_number`/`voucher_date` stored in all three layers

### Out of Scope

Nebula code; attachments/base64; `chatter-voucher-attachments`; JSON/flattened MCP;
form-path snapshots; `collection-sheets`/`seller-lookup`.

## Capabilities

### New Capabilities

None

### Modified Capabilities

- `collection-vouchers`: provenance fields; nested MCP; replay ignore; write guards;
  snapshot ACL; additive migration
- `document-review`: three-way UI; Document Review snapshots; queue provenance; history

## Approach

Stamp on all-new MCP create in the existing savepoint. Reuse `_PAYMENT_OPTIONAL_FIELDS`
equality. Snapshots only from `_write_review_decision`. Queue payload includes readonly
provenance. Context-gated snapshot create.

## Affected Areas

|Area|Impact|Description|
|---|---|---|
|`models/collection_voucher.py`|Modified|Fields, guards, snapshots, queue|
|`models/collection_voucher_review_snapshot.py`|New|Immutable snapshot|
|`tools/collection_voucher.py`|Modified|Nested parse; all-new stamp|
|`views/collection_views.xml`|Modified|Three-way + history|
|`static/src/document_review/`|Modified|OWL side-by-side|
|`security/ir.model.access.csv`|Modified|Snapshot ACL|
|`__manifest__.py`|Modified|`19.0.1.14.0`|
|`tests/test_collection_*.py`|Modified|MCP, review, ACL, UI|

## Risks

|Risk|Likelihood|Mitigation|
|---|---|---|
|400-line review budget|High|Chain model/MCP/ACL, form, OWL|
|Form path has no history|Med|Explicit in-scope|
|MCP drops nests until Odoo ships|Med|Ship Odoo first|
|omit/null/`""` false reject|Med|Reuse optional-field parse|
|RPC overwrite of provenance|High|`write()` rejects keys|

## Rollback Plan

Revert the addon commit. Upgrade does not drop additive columns or snapshot rows.
Uninstall is not clean if snapshots exist (needs reverse migrate). Leave
`19.0.1.13.0` chatter scripts.

## Dependencies

Coordinated Nebula change (out of repo) for nests. Independent of
`chatter-voucher-attachments`.

## Success Criteria

- [ ] Unchanged seller: current == seller == raw
- [ ] Seller correction: current == seller; raw differs
- [ ] Reviewer correction persisted; snapshot matches
- [ ] Unchanged approval still snapshots
- [ ] Reopen re-review appends; prior unchanged
- [ ] Exact replay ignores nests; no provenance/history mutation
- [ ] Bad/one-sided/mismatch fails batch before write
- [ ] No base64 in provenance, logs, or MCP nests
- [ ] Manual/omitted nests: empty provenance
- [ ] Existing rows: current kept; raw/seller null; zero snapshots
- [ ] Form Approve/Reject does not snapshot
