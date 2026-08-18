# Tasks: Chatter Voucher Attachments

## Review Workload Forecast

| Field                   | Value              |
| ----------------------- | ------------------ |
| Estimated changed lines | 700–1100           |
| 400-line budget risk    | High               |
| Chained PRs recommended | Yes                |
| Suggested split         | PR 1 → PR 2 → PR 3 |
| Delivery strategy       | auto-chain         |
| Chain strategy          | stacked-to-main    |

Decision needed before apply: No Chained PRs recommended: Yes Chain strategy:
stacked-to-main 400-line budget risk: High

### Suggested Work Units

Seedian root tests. Harness N/A (`TransactionCase`).

| Unit | Goal                                                                              | PR   | Test                                                                     | Rollback                                                           |
| ---- | --------------------------------------------------------------------------------- | ---- | ------------------------------------------------------------------------ | ------------------------------------------------------------------ |
| 1    | Mixin, drop Binary, migrate `19.0.1.13.0`, picker, reset; widgets + MCP post glue | PR 1 | `invoke test -m collection` (`tests/test_collection_voucher.py`)         | migrate dir, model, views, manifest, MCP persist                   |
| 2    | MCP nest unchanged; persist + exact-retry tests                                   | PR 2 | `invoke test -m collection` (`tests/test_collection_mcp_tool.py`)        | `tools/collection_voucher.py` + MCP tests                          |
| 3    | Review URL/queue/rotation; remaining tests; docs                                  | PR 3 | `invoke test -m collection` (`tests/test_collection_document_review.py`) | review URL, `static/src/document_review/*`, `AGENTS.md`, `readme/` |

Nebula/`auto-assign-open-sheet` out of scope. Threat matrix N/A.

## Phase 1: Migrate + model (PR 1)

- [x] 1.1 RED `tests/test_collection_voucher.py` + `tests/test_collection_mail.py`:
      proof = `message_main_attachment_id`; extras do not steal; non-image extra cannot
      become proof; MIME picker `image/*`+PDF.
- [x] 1.2 GREEN `models/collection_voucher.py`: inherit `mail.thread.main.attachment`;
      override picker; drop Binary fields.
- [x] 1.3 RED replace main → pending + clear audit + rotation 0; extras do not reset;
      clear → rotation 0, keep decided; omit valid; invalid `UserError`.
- [x] 1.4 GREEN write-reset on main; keep `attachment_rotation`.
- [x] 1.5 RED SQL migrate: `res_field=attachment` → chatter main; empty filename →
      `proof.bin`; leftover field rows gone.
- [x] 1.6 GREEN `migrations/19.0.1.13.0/pre-migrate.py` + `post-migrate.py`;
      `__manifest__.py` `19.0.1.13.0`.
- [x] 1.7 RED `tests/test_collection_ui.py`: no Binary widgets; chatter remains; picker
      accept `image/*`+PDF.
- [x] 1.8 GREEN `views/collection_views.xml`: drop Binary widgets;
      `<chatter open_attachments="True"/>`.
- [x] 1.9 RED `tests/test_collection_mcp_tool.py`: one nest → chatter designated proof
      (smoke).
- [x] 1.10 GREEN `tools/collection_voucher.py`: savepoint `message_post` after create;
      nest unchanged; no Binary vals.
- [x] 1.11 GREEN helpers in
      `tests/test_collection_{acl,document_review,document_review_flag,mcp_tool}.py`:
      `message_post` only.

## Phase 2: MCP tests (PR 2)

- [x] 2.1 RED `TestCollectionMcpAttachment`: omit valid; MIME/b64 `UserError` no writes;
      chatter proof not `res_field=attachment`.
- [x] 2.2 GREEN validate nest then post; fail-closed before writes.
- [x] 2.3 RED exact-retry with/without nest: return all; no add/replace/compare.
- [x] 2.4 GREEN exact-retry / UniqueViolation replay: no post, no nest compare.

## Phase 3: Document review + docs (PR 3)

- [x] 3.1 RED `tests/test_collection_document_review.py`: queue pending+main;
      empty/cross-sheet; `/web/content/{id}` (no `field=`); image+PDF; OWL no base64;
      viewer states; extras skip rotation reset; replace/clear → 0; stale if proof
      missing.
- [x] 3.2 GREEN `models/collection_voucher.py`: eligibility on main;
      `_attachment_content_url` → `/web/content/{id}`; payload from `ir.attachment`. OWL
      keeps `current.attachment_url`.
- [x] 3.3 GREEN `AGENTS.md` + `readme/DESCRIPTION.md`: chatter proof; no Binary.

## Phase 4: Upgrade / verify

- [x] 4.1 Seedian root: `invoke install -m collection` (pre before drop).
- [x] 4.2 Scoped `pre-commit run --files` on changed paths.
- [x] 4.3 `invoke test -m collection`.
