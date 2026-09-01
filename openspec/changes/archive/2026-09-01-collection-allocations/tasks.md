# Tasks: Collection Allocations

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 1600–2200 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 models/ACL/seq/migrate → PR 2 MCP → PR 3 views |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Models, ACL, `CA/` seq, migrate 1.25.0, guards | PR 1 (base `main`) | `invoke test -m collection --mode=update` | `-u collection`; N/A CRUD — tests cover models | Revert models/seq/migration/manifest/voucher+sheet guards |
| 2 | MCP `create_collection_allocation` | PR 2 (on PR 1) | `invoke test -m collection --mode=update` | N/A — MCP tests cover create/replay/gates | Remove tool + MCP tests |
| 3 | Views, menu 30, sheet notebook | PR 3 (on PR 2) | `invoke test -m collection --mode=update` | `-u collection`; open sheet notebook + Allocations menu | Revert views + UI assertions |

Skip OpenSpec, 1.17.0, `_DISPATCH_OPS`, partner-create resolve, Nebula, sqlite.

## Phase 1: Models, security, sequence, migration (PR 1)

- [x] 1.1 RED `tests/test_collection_allocation.py`: UNIQUE(sheet,partner); freeze not-confirmed; O2M DELETE sanitizer; residual ≥0 only while confirmed; validate/reject; revision immutable UNIQUE(`request_id`); unlink-with-revisions refused; `allocation_id` write iff both confirmed/unset; allocated unlink refused.
- [x] 1.2 RED `tests/test_collection_allocation_acl.py`: allocation/line `1,1,1,1`; revision `1,0,1,0`; three company `ir.rule`s; `inspect.getsource` no `.sudo(`.
- [x] 1.3 RED `tests/test_collection_company_migration.py`: version `19.0.1.25.0`; SPECS/XMLID includes `CA/` `seq_collection_allocation`.
- [x] 1.4 RED `tests/test_collection_sheet.py`: unlink unassigns when empty of allocations; restrict when allocated (members stay).
- [x] 1.5 GREEN `models/collection_allocation.py`, `collection_allocation_line.py`, `collection_allocation_revision.py`; import in `models/__init__.py`.
- [x] 1.6 GREEN `models/collection_voucher.py` `allocation_id` (`ondelete="set null"`, `check_company`, write/ondelete); `models/collection_sheet.py` `allocation_ids`; empty unlink OK; `ondelete="restrict"` when allocated.
- [x] 1.7 GREEN `security/ir.model.access.csv` + three `ir.rule`s in `security/collection_security.xml`.
- [x] 1.8 GREEN `data/ir_sequence_data.xml` `seq_collection_allocation`; `COLLECTION_SEQUENCE_SPECS` `CA/%(year)s/` padding 4 in `models/res_company.py`; `migrations/19.0.1.25.0/post-migrate.py` `_collection_copy_sequences()`; `__manifest__.py` `19.0.1.25.0`; register tests in `tests/__init__.py`.
- [x] 1.9 REFACTOR + `AGENTS.md` models/seq/version; `-u collection`; `invoke test -m collection --mode=update`; `pre-commit run --files` on Phase 1 paths.

## Phase 2: MCP tool (PR 2)

- [x] 2.1 RED `tests/test_collection_mcp_allocation.py`: create; `request_id`/`content_hash` replay; SUPERSET amend; overlap reject; UniqueViolation replay/generic (no ids); amount/rejected/company/sheet gates; binding-only resolve; prior-allocation subtract; residual; freeze; `inspect.getsource` no `.sudo(`.
- [x] 2.2 GREEN `tools/collection_allocation.py` `@mcp_tool` write; import in `tools/__init__.py`; register MCP tests in `tests/__init__.py`.
- [x] 2.3 REFACTOR + `AGENTS.md` MCP row; `invoke test -m collection --mode=update`; `pre-commit run --files` on tool + MCP tests.

## Phase 3: Views / menu / sheet notebook (PR 3)

- [x] 3.1 RED `tests/test_collection_ui.py`: allocation `<list>`/form/search; menu sequence 30; sheet form notebook vouchers + allocations.
- [x] 3.2 GREEN `views/collection_allocation_views.xml` (`<list>`; `path`; menu 30); sheet notebook in `views/collection_views.xml`; add views to `__manifest__.py` `data`.
- [x] 3.3 REFACTOR + `AGENTS.md` UI/tests; `-u collection`; `invoke test -m collection --mode=update`; `pre-commit run --files` on views + UI tests.
