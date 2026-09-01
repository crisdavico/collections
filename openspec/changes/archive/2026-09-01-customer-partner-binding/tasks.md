# Tasks: Customer Partner Binding

## Review Workload Forecast

| Field                   | Value                                                        |
| ----------------------- | ------------------------------------------------------------ |
| Estimated changed lines | 900–1300                                                     |
| 400-line budget risk    | High                                                         |
| Chained PRs recommended | Yes                                                          |
| Suggested split         | PR1 binding → PR2 resolve → PR3 voucher → PR4 MCP → PR5 docs |
| Delivery strategy       | auto-chain                                                   |
| Chain strategy          | stacked-to-main                                              |

Decision needed before apply: No Chained PRs recommended: Yes Chain strategy:
stacked-to-main 400-line budget risk: High

Skip sqlite/nebula/Q4.

### Suggested Work Units

| Unit | Goal                      | Likely PR   | Focused test command                      | Runtime harness                | Rollback boundary                 |
| ---- | ------------------------- | ----------- | ----------------------------------------- | ------------------------------ | --------------------------------- |
| 1    | Binding + ACL + notebook  | PR 1 → main | `invoke test -m collection --mode=update` | `invoke install -m collection` | binding model/security/view/tests |
| 2    | Resolve + P5 + race       | PR 2 → PR1  | same                                      | same                           | resolve + P5 + tests              |
| 3    | Voucher `partner_id` + P4 | PR 3 → PR2  | same                                      | same                           | voucher field/views/helpers       |
| 4    | MCP + fixtures            | PR 4 → PR3  | same                                      | same                           | MCP tool + tests                  |
| 5    | Docs + `19.0.1.24.0`      | PR 5 → PR4  | same                                      | same                           | manifest/docs/version-test        |

## Phase 1: Binding + security + view

- [x] 1.1 RED `tests/test_collection_customer_binding.py`: UNIQUE
      `(connector_id, external_customer_id|identification|partner_id)`; company-guard;
      user ACL `1,0,1,0`; other-company `ir.rule`. Wire `tests/__init__.py`.
- [x] 1.2 GREEN `models/collection_connector_customer_binding.py` (seller-binding
      mirror; three `models.Constraint`; `create()` company-guard). Import after
      connector in `models/__init__.py`.
- [x] 1.3 GREEN ACL csv `1,0,1,0` / system `1,1,1,1`; company `ir.rule` in
      `security/collection_security.xml`. No `sudo()`.
- [x] 1.4 GREEN `customer_binding_ids` on `models/collection_connector.py`; bindings
      notebook on `views/collection_connector_views.xml`.

## Phase 2: Resolve + P5 + race

- [x] 2.1 RED `tests/test_collection_customer_resolution.py`: gate before lookup;
      fast-path skip adapter; vat 1 bind / 0 create (`vat`, `company_id`,
      `customer_rank=1`) / `>1` generic; nested UniqueViolation not `document_id`
      conflict.
- [x] 2.2 GREEN `resolve_customer_partner` on connector: ident → seller gate → binding →
      `list_customers` → D3 vat → nested savepoint on partner+binding insert.
- [x] 2.3 GREEN `models/res_company.py`: rename `_collection_create_seller_partners` →
      `_collection_create_partners`; extend raw-SQL INSERT with `vat`, `company_id`,
      `customer_rank` (P5+Q3).

## Phase 3: Voucher field + P4

- [x] 3.1 RED required `partner_id` (Customer, tracking, index, restrict); Char gone;
      six `views/collection_views.xml` nodes (22/47/107/116/164/490) `partner_id` **no
      domain**; UI tests.
- [x] 3.2 GREEN `models/collection_voucher.py` drop Char / add `partner_id` (P3).
- [x] 3.3 RED→GREEN P4 `customer=` on `_create_voucher` / `_voucher_vals` /
      `_create_voucher_in_company` (~12 defs). Dummy partner OK.

## Phase 4: MCP path + fixtures

- [x] 4.1 RED `tests/test_collection_mcp_tool.py` fixtures:
      `install_test_connector_type`, company connector, bound seller, listable
      `TEST_CUSTOMERS`.
- [x] 4.2 RED all-new resolve after classify inside savepoint; mixed stamps; invalid
      batch rolls back; replay skips resolve, keeps first-call `partner_id`.
- [x] 4.3 GREEN `tools/collection_voucher.py`: parallel ident list; resolve in
      savepoint; nested UniqueViolation for bindings; provenance exclusion
      `("document_id",)`.

## Phase 5: Docs + version

- [x] 5.1 RED→GREEN `__manifest__.py` `19.0.1.24.0`; bump
      `test_manifest_version_is_1_23_0`.
- [x] 5.2 GREEN `AGENTS.md` + `readme/DESCRIPTION.md` (partner in-scope; MCP string I/O
      unchanged).
- [x] 5.3 Scoped pre-commit; module test; install.
