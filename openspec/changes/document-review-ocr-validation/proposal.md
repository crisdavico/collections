# Proposal: Document Review OCR Validation

## Intent

Reviewers must correct OCR’d payment-line fields against the attached image/PDF and
approve/reject before a voucher leaves `new`. Document Review is still mock data.

**Locked assumptions:** queue = lines on voucher `new`, review pending, attachment
present; no confidence/stamps/notes; approve saves then may validate when all attached
lines approved; line reject rejects voucher; evolve existing scaffolding.

## Scope

### In Scope

- Review queue + auth binary image/PDF viewing (no base64 in OWL)
- Editable `document_type`, `amount`, type-specific fields; readonly `document_id`,
  voucher ref, queue position
- Line `pending`/`approved`/`rejected` + reviewer/time audit
- Atomic approve/reject; `action_validate()` blocked while attached lines pending
- Tests: eligibility, image/PDF, types, persistence, aggregate validate/reject, ACL,
  races, empty queue, attachment replace → pending
- Additive upgrade; default `pending` for existing lines

### Out of Scope

- Nebula/OCR pipeline; confidence/stamps/notes; WhatsApp/API/CRM; multi-file or
  non-image/PDF; ACL changes; code in this phase

## Capabilities

### New Capabilities

- `document-review`: Queue; OWL client (ORM, typed inputs, binary URLs, load/error/empty,
  navigation, next-record); approve/reject without mocks

### Modified Capabilities

- `collection-vouchers`: Line review fields/audit; approve may validate; line reject
  rejects voucher; `action_validate()` requires attached lines reviewed; attachment
  replace resets pending; keep terminal states + internal-user ACL

## Approach

Guarded queue/approve/reject on `collection.voucher.line`; validate guard on
`collection.voucher`. Evolve `DocumentReviewAction` + assets; auth binary route.
Likely >400 LOC — stacked-to-main; ask-on-risk before `/sdd-apply`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `models/collection_voucher_line.py` | Modified | Review status, audit, queue/approve/reject |
| `models/collection_voucher.py` | Modified | Validate guard; aggregate transitions |
| `static/src/document_review/*` | Modified | Real data/viewer; drop mocks |
| `views/collection_document_review_views.xml` | Modified | Keep menu/action |
| `tests/test_collection_*.py` | Modified/New | Acceptance tests |
| `__manifest__.py` | Modified | Version bump on apply |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Concurrent/stale review | Med | Guarded transitions; clear errors |
| Diff >400 LOC | High | Stacked PRs; ask-on-risk |
| Binary URL/auth edges | Med | Loading/error states; ACL tests |
| Attachment vs reviewed | Med | Reset pending on attachment write |

## Rollback Plan

Revert prior module version and upgrade. Additive fields unused if UI gone.

## Dependencies

- Line attachments; Document Review prototype; `base.group_user`

## Success Criteria

- [ ] Queue only eligible pending attached lines on `new` vouchers
- [ ] Image/PDF via auth binary route; no base64 in OWL
- [ ] Approve persists corrections; type-specific fields work
- [ ] All attached approved → `validated`; line reject → voucher `rejected`
- [ ] `action_validate()` blocked while attached lines pending
- [ ] ACL, races, empty queue, attachment-reset tested
- [ ] Upgrade defaults lines to `pending` (no migration)
