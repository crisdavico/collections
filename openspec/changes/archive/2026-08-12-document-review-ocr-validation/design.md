# Design: Document Review OCR Validation

## Technical Approach

Replace Document Review mocks with ORM-backed queue/approve/reject. Store review
status + audit on `collection.voucher.line`; guard `action_validate` while attached
lines are pending. Last attached approve may validate the voucher; line reject rejects
it. Viewer uses authenticated `/web/content` (no base64 in OWL). Keep menu + tag
`collection.document_review`. Out of scope: confidence, stamps, notes, Nebula.

## Architecture Decisions

| Decision           | Options                        | Choice                                       | Rationale                                  |
| ------------------ | ------------------------------ | -------------------------------------------- | ------------------------------------------ |
| Review state       | Header vs line                 | Line `review_status` + audit                 | Queue/attachment are line-scoped           |
| Queue              | All new vs attached pending    | `new` ∧ `pending` ∧ attachment               | Locked proposal                            |
| Mutations          | Ad-hoc OWL writes vs model API | Public queue/approve/reject                  | Atomic guards; thin OWL                    |
| Aggregate          | Manual only vs auto validate   | Auto validate when all attached approved     | Faster queue; form Validate kept + guarded |
| Binary             | Base64 state vs content URL    | `/web/content?model=…&id=…&field=attachment` | Session + ACL                              |
| Attachment replace | Keep vs reset                  | Reset `pending`, clear audit                 | Avoid stale approval                       |
| ACL                | New group vs existing          | `base.group_user` only                       | No ACL expansion                           |
| Migration          | Script vs defaults             | Additive default `pending`                   | No data migration                          |

## Data Flow

```
OWL → orm.call queue/approve/reject
        → line (eligible) → write + audit
            ├ approve → all attached approved? → voucher.action_validate()
            └ reject  → voucher.action_reject()
Viewer ← GET /web/content (session; record ACL)
```

Race: re-check eligibility in-transaction; stale concurrent call → `UserError`. OWL
notifies and reloads queue.

## File Changes

| File                                                | Action | Description                                          |
| --------------------------------------------------- | ------ | ---------------------------------------------------- |
| `models/collection_voucher_line.py`                 | Modify | Fields; queue/approve/reject; attach write → pending |
| `models/collection_voucher.py`                      | Modify | Validate blocks attached pending                     |
| `static/src/document_review/*.{esm.js,xml,scss}`    | Modify | ORM UI; real viewer; drop mocks/stamps/notes         |
| `views/collection_document_review_views.xml`        | Keep   | Menu/action/tag/path                                 |
| `tests/test_collection_document_review.py`          | Create | Eligibility, aggregate, races, empty, reset          |
| `tests/test_collection_{voucher,payment,acl,ui}.py` | Modify | Guard, reset, ACL, menu/tag                          |
| `__manifest__.py`                                   | Modify | Version bump on apply                                |

## Interfaces / Contracts

**Fields:** `review_status` (`pending|approved|rejected`, default `pending`,
`copy=False`); `reviewed_by`; `reviewed_at`.

**Eligible:** voucher `new`, status `pending`, attachment present.

**Queue (`@api.model`):** ordered payloads with ids, voucher ref, readonly
`document_id`, `document_type`, editable type fields, position/total, filename, content
URL. Never datas/base64.

**Approve:** require eligible; write editable vals (not `document_id`); set
approved+audit; if all attached siblings approved → `action_validate()`.

**Reject:** require eligible; set rejected+audit; `action_reject()`.

**`action_validate`:** error if any line has attachment and status `pending`. Unattached
lines do not block. Terminal immutability unchanged.

**OWL:** `orm` + notifications; typed inputs; img vs PDF from MIME/filename; next after
success or empty; loading/error/empty states.

## Testing Strategy

Strict TDD: `invoke test -m collection`.

| Layer   | What                                                                    | Approach                           |
| ------- | ----------------------------------------------------------------------- | ---------------------------------- |
| Unit    | Queue, approve/reject, aggregate, validate guard, attach→pending, races | New review tests + voucher/payment |
| ACL     | Portal denied; internal OK                                              | Extend `test_collection_acl.py`    |
| UI arch | Menu/tag survive                                                        | Extend `test_collection_ui.py`     |
| E2E     | N/A                                                                     | Unavailable                        |

## Threat Matrix

N/A — no shell/VCS/PR/executable classification; reuses Odoo content route with existing
ACL (no `sudo`).

| Workflow risk           | Response                                     |
| ----------------------- | -------------------------------------------- |
| Concurrent/stale review | Guarded transitions + UserError + OWL reload |
| Binary 403/404          | Viewer error state                           |
| Approved then new file  | Reset pending on attachment write            |

## Migration / Rollout

Additive upgrade; default `pending`. No `migrations/` unless defaults fail. Rollback:
prior module version + upgrade; unused columns harmless.

## Delivery slices (ask-on-risk / stacked-to-main)

Forecast **>400 LOC** → stacked PRs before apply.

1. Model fields/guards/tests (no OWL)
2. OWL ORM path (editors + RPC + empty/error)
3. Binary viewer (image/PDF + load/error)

`Decision needed before apply: Yes` · `Chained PRs recommended: Yes` ·
`400-line budget risk: High`

## Open Questions

- None blocking.
