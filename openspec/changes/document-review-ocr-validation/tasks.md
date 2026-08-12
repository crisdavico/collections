# Tasks: Document Review OCR Validation

## Review Workload Forecast

| Field                   | Value                                       |
| ----------------------- | ------------------------------------------- |
| Estimated changed lines | 500–800                                     |
| 400-line budget risk    | High                                        |
| Chained PRs recommended | Yes                                         |
| Suggested split         | PR1 model → PR2 OWL ORM → PR3 binary viewer |
| Delivery strategy       | ask-on-risk                                 |
| Chain strategy          | stacked-to-main                             |

Decision needed before apply: Yes Chained PRs recommended: Yes Chain strategy:
stacked-to-main 400-line budget risk: High

### Suggested Work Units

| Unit | Goal                                                                | Likely PR   | Focused test command                                          | Runtime harness                                                               | Rollback boundary                                                                               |
| ---- | ------------------------------------------------------------------- | ----------- | ------------------------------------------------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| 1    | Review fields, queue/approve/reject, validate guard, attach→pending | PR 1        | `invoke test -m collection` (document_review+voucher+payment) | `docker exec -i seedian-odoo-1 odoo -d devel -u collection --stop-after-init` | `models/collection_voucher*.py`, `tests/test_collection_document_review.py` (+ voucher/payment) |
| 2    | OWL ORM queue, typed editors, nav, empty/error; drop mocks          | PR 2        | `invoke test -m collection` (ui+document_review)              | Document Review: empty + multi-line nav                                       | `static/src/document_review/*`                                                                  |
| 3    | Auth binary image/PDF viewer + load/error/empty                     | PR 3        | `invoke test -m collection` (URL+ui)                          | Image + PDF in Document Review                                                | viewer in `document_review_action.*`                                                            |
| 4    | ACL + menu/tag; upgrade + full test + pre-commit                    | PR1–3/final | `invoke test -m collection`; scoped pre-commit                | Upgrade `collection` on devel                                                 | `tests/test_collection_{acl,ui}.py`, `__manifest__.py`                                          |

Threat matrix: N/A. Workflow risks in 1.3, 3.2, 4.1.

## Phase 1: Model review workflow (PR 1)

- [x] 1.1 RED `tests/test_collection_document_review.py`: queue eligibility + empty
      queue (document-review scenarios)
- [x] 1.2 RED: default `pending`/audit; approve persists edits; reject; aggregate
      validate; line reject→voucher reject (collection-vouchers)
- [x] 1.3 RED: stale/concurrent refuse; attachment write resets pending+clears audit;
      `action_validate` blocked while attached pending
- [x] 1.4 GREEN `models/collection_voucher_line.py`:
      `review_status`/`reviewed_by`/`reviewed_at` (`copy=False`); queue/approve/reject;
      attach write→pending
- [x] 1.5 GREEN `models/collection_voucher.py`: refuse `action_validate` if any attached
      line `pending`
- [x] 1.6 RED→GREEN extend `tests/test_collection_voucher.py` +
      `tests/test_collection_payment.py` for guard + reset
- [x] 1.7 REFACTOR private helpers; keep public queue/approve/reject contracts (no
      base64 in queue)

## Phase 2: OWL ORM client (PR 2)

- [x] 2.1 RED extend `tests/test_collection_ui.py`: menu/action/tag
      `collection.document_review` survive
- [x] 2.2 GREEN `static/src/document_review/document_review_action.esm.js` + `.xml`: ORM
      queue; typed editors by `document_type`; readonly `document_id`/voucher/position;
      nav + next after decision; empty state; drop mocks/stamps/notes
- [x] 2.3 GREEN wire approve/reject RPCs + notifications; reload queue on `UserError`
- [x] 2.4 REFACTOR thin OWL; never put attachment datas/base64 in component state

## Phase 3: Binary viewer (PR 3)

- [ ] 3.1 RED assert queue payload content URL only (no `datas`/base64) in
      `tests/test_collection_document_review.py`
- [ ] 3.2 GREEN `/web/content` image vs PDF viewer + loading/error/empty in
      `document_review_action.*` (+scss)
- [ ] 3.3 REFACTOR MIME/filename branching only

## Phase 4: ACL + final verification

- [ ] 4.1 RED→GREEN `tests/test_collection_acl.py`: non-internal denied
      queue/approve/reject; internal OK
- [ ] 4.2 Bump `__manifest__.py` version; upgrade `collection` on devel
- [ ] 4.3 Run `invoke test -m collection`; fix failures mapped to spec scenarios
- [ ] 4.4 Scoped `pre-commit run --files odoo/custom/src/private/collection/**`
