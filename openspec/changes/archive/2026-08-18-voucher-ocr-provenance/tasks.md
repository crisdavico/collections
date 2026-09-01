# Tasks: Voucher OCR Provenance

## Review Workload Forecast

| Field                   | Value                        |
| ----------------------- | ---------------------------- |
| Estimated changed lines | 700–1100                     |
| 400-line budget risk    | High                         |
| Chained PRs recommended | Yes                          |
| Suggested split         | PR1 → PR2 → PR3 (work units) |
| Delivery strategy       | ask-on-risk                  |
| Chain strategy          | stacked-to-main              |

Decision needed before apply: Yes Chained PRs recommended: Yes Chain strategy:
stacked-to-main 400-line budget risk: High

### Suggested Work Units

| Unit | Goal                     | Likely PR | Focused test command        | Runtime harness                           | Rollback boundary                                                          |
| ---- | ------------------------ | --------- | --------------------------- | ----------------------------------------- | -------------------------------------------------------------------------- |
| 1    | Model + MCP + ACL        | PR 1      | `invoke test -m collection` | `invoke install -m collection` then tests | snapshot+voucher+MCP+ACL+manifest `19.0.1.14.0`+tests+`AGENTS.md`+readme   |
| 2    | Form three-way + history | PR 2      | `invoke test -m collection` | same upgrade then tests                   | `views/collection_views.xml`, `tests/test_collection_ui.py`                |
| 3    | OWL + queue payload      | PR 3      | `invoke test -m collection` | same upgrade then tests                   | `_review_queue_payload`, `static/src/document_review/`, DR queue/OWL tests |

Alt upgrade:
`docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init`. Lint:
`pre-commit run --files odoo/custom/src/private/collection/**`. No 1.14 migrate; leave
`migrations/19.0.1.13.0/`. Threat matrix N/A.

## Phase 1: Model, MCP, ACL (PR 1)

- [x] 1.1 RED `tests/test_collection_mcp_tool.py`: omitted nests → null provenance;
      UI/ORM create allowed; no base64 in nests/logs.
- [x] 1.2 RED MCP: unchanged seller (all three equal); seller correction (raw differs;
      current==seller==top-level); cash-deposit `voucher_number`/`voucher_date` in all
      layers; `document_id`/attachment/identity outside nests.
- [x] 1.3 RED MCP: one-sided, malformed, mismatch fail-closed before write; nest
      `document_type` required; reuse `_PAYMENT_OPTIONAL_FIELDS` equality.
- [x] 1.4 RED MCP: exact replay + UniqueViolation ignore nests (no backfill). Parse
      nests on create path only, after existing-document check, before savepoint — not
      in `_collection_parse_payment_vals`.
- [x] 1.5 RED `tests/test_collection_acl.py` + voucher: `write()` rejects
      `ocr_*`/`seller_*`; `create()` may stamp; existing rows keep current, provenance
      null, zero snapshots.
- [x] 1.6 RED snapshot ACL: read + gated create (`collection_review_snapshot`);
      write/unlink denied; no sudo/groups/`ir.rule`; portal denied.
- [x] 1.7 RED `tests/test_collection_document_review.py`: `_write_review_decision`
      approve (incl. empty vals) and reject snapshot; form
      `action_approve`/`action_reject` MUST NOT; reopen appends revision; reviewer
      correction matches current; raw/seller unchanged.
- [x] 1.8 GREEN `models/collection_voucher.py`: `ocr_*`/`seller_*` (`copy=False`,
      `_REVIEW_EDITABLE_FIELDS`); `write()` reject; snapshot only from
      `_write_review_decision` after decision write. New
      `models/collection_voucher_review_snapshot.py` (UNIQUE voucher+revision); import;
      ACL CSV; `__manifest__.py` `19.0.1.14.0`.
- [x] 1.9 GREEN `tools/collection_voucher.py`: nests `raw_ocr`+`seller_confirmed`;
      create-path stamp; replay unchanged. Nebula: nested provenance; top-level current;
      `document_id`/attachment outside.
- [x] 1.10 Docs with MCP: `AGENTS.md` MCP bullet + `readme/DESCRIPTION.md`. Run unit
      tests + scoped pre-commit.

## Phase 2: Form three-way + history (PR 2)

- [x] 2.1 RED `tests/test_collection_ui.py`: notebook Current/Raw/Seller; type
      `invisible=` all layers; hide `document_id` on provenance pages; cash-deposit keys
      stored (UI may hide); allow history `<list>`, forbid `payment_ids`; history
      readonly by revision.
- [x] 2.2 GREEN `views/collection_views.xml` notebook + One2many history `<list>`.

## Phase 3: OWL + queue (PR 3)

- [x] 3.1 RED `tests/test_collection_document_review.py`: queue readonly
      `ocr_*`/`seller_*` (empty not fabricated); no `datas`/base64; OWL keeps
      `isBankTransfer`/`isCheck`; no `document_id`; `buildApproveVals` current-only;
      empty provenance loads.
- [x] 3.2 GREEN `_review_queue_payload`; `document_review_action.xml` +
      `document_review_helpers.esm.js`.
