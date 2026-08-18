# Tasks: `create_nebula_voucher` MCP tool

## Review Workload Forecast

| Field                   | Value                 |
| ----------------------- | --------------------- |
| Estimated changed lines | 550–750               |
| 400-line budget risk    | High                  |
| Chained PRs recommended | Yes                   |
| Suggested split         | PR1 → PR2 → PR3 → PR4 |
| Delivery strategy       | ask-on-risk           |
| Chain strategy          | stacked-to-main       |

Decision needed before apply: Yes Chained PRs recommended: Yes Chain strategy:
stacked-to-main 400-line budget risk: High

### Suggested Work Units

| Unit | Goal                                              | Likely PR | Focused test command            | Runtime harness                    | Rollback boundary                                |
| ---- | ------------------------------------------------- | --------- | ------------------------------- | ---------------------------------- | ------------------------------------------------ |
| 1    | Drop `received_date`; UI `create_date`; migration | PR 1      | `invoke test -m seedian_nebula` | `invoke install -m seedian_nebula` | voucher model/views/migration + voucher/UI tests |
| 2    | Nullable unique `document_id`                     | PR 2      | `invoke test -m seedian_nebula` | N/A — model only                   | payment model + uniqueness tests                 |
| 3    | MCP discover/create/return + ACL                  | PR 3      | `invoke test -m seedian_nebula` | MCP `_call` in tests               | `tools/`, manifest/`__init__`, MCP+ACL tests     |
| 4    | Idempotency + UniqueViolation replay              | PR 4      | `invoke test -m seedian_nebula` | MCP `_call` conflicts              | tool idempotency/race + tests                    |

## Phase 1: received_date → create_date (Unit 1)

- [x] 1.1 RED: `tests/test_seedian_nebula_voucher.py` — no `received_date`; auto
      `create_date`; reject `received_date` vals.
- [x] 1.2 RED: `tests/test_seedian_nebula_ui.py` — readonly `create_date` in views; no
      `received_date` in arch.
- [x] 1.3 GREEN: Drop `received_date` from `models/seedian_nebula_voucher.py`.
- [x] 1.4 GREEN: Views → readonly `create_date` in `views/seedian_nebula_views.xml`.
- [x] 1.5 GREEN: `migrations/19.0.1.1.0/post-migrate.py` DROP COLUMN; bump `19.0.1.1.0`.
- [x] 1.6 Verify: `invoke install -m seedian_nebula`; `invoke test -m seedian_nebula`.

## Phase 2: document_id uniqueness (Unit 2)

- [x] 2.1 RED: Payment w/o `document_id` OK; duplicate non-null → IntegrityError.
- [x] 2.2 GREEN: Nullable Char `document_id` + unique `models.Constraint` on payment
      model.
- [x] 2.3 Verify: `invoke test -m seedian_nebula`.

## Phase 3: MCP tool create + ACL (Unit 3)

- [x] 3.1 RED: `tests/test_seedian_nebula_mcp_tool.py` — `_call` discover; all-new
      return; no `received_date` schema; require `document_id`.
- [x] 3.2 RED: Non-permitted user → AccessError, no writes.
- [x] 3.3 GREEN: Manifest `depends` += `muk_mcp`; `__init__.py` import `tools`.
- [x] 3.4 GREEN: `tools/__init__.py` + `tools/nebula_voucher.py` — mixin + `@mcp_tool`
      allowlist schema.
- [x] 3.5 GREEN: Validate → savepoint voucher+batch payments; return
      `{id,name,state,payments}`; no `sudo()`.
- [x] 3.6 Register in `tests/__init__.py`; `invoke test -m seedian_nebula`.

## Phase 4: Idempotency + race (Unit 4)

- [x] 4.1 RED: Exact-retry → same ids, no new rows.
- [x] 4.2 RED: In-call duplicate `document_id` → reject, no writes.
- [x] 4.3 RED: Partial-conflict → reject, no writes.
- [x] 4.4 RED: Cross-voucher-conflict → reject, no writes.
- [x] 4.5 RED: UniqueViolation → re-lookup; full match → replay; else UserError.
- [x] 4.6 GREEN: Lookup/create/reject + UniqueViolation → replay/reject.
- [x] 4.7 Verify: `invoke test -m seedian_nebula`.

## Phase 5: Quality gate

- [x] 5.1 `invoke install -m seedian_nebula`
- [x] 5.2 `pre-commit run --files odoo/custom/src/private/seedian_nebula/**`
- [x] 5.3 `invoke test -m seedian_nebula --mode=update`
