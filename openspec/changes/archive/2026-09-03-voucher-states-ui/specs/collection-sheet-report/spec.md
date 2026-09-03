# Delta for collection-sheet-report

## MODIFIED Requirements

### Requirement: Shared report payload

`_collection_report_data()` MUST return one payload: primitives (`str` / `float` / `int` / `bool` / `date` / `list` / `dict`) plus `sheet` and `currency` for QWeb. Nested customer, document-row, and voucher-row dict values MUST be primitives (XLSX MUST NOT touch the ORM). MUST include `company`, `printed_on`, `reference`, `state_label`, `seller_name`, `date_from`, `date_to`, `customer_count`, `voucher_count`, `commission_percent`, `customers`, `customer_totals`, `document_blocks`, `applied_total`, `voucher_blocks`, `collected_total`, `tendered`, `recon`, `mismatch`. Print MUST include every `allocation_ids` and `voucher_ids` row (draft/confirmed; draft/validated_seller/validated_collections). Open-sheet prints MUST include drafts. Customer totals MUST equal allocation sums. PDF HTML and XLSX cached totals MUST match.
(Previously: Print-includes voucher keys were pending/approved/rejected.)

#### Scenario: Primitive nested values

- GIVEN a saved sheet with allocations and vouchers
- WHEN `_collection_report_data()` runs
- THEN listed keys MUST be present
- AND nested row dict values MUST be primitives

#### Scenario: Open sheet prints drafts

- GIVEN an open sheet with draft allocations and mixed-state vouchers
- WHEN the payload is built
- THEN every allocation and voucher MUST appear
- AND drafts MUST NOT be omitted
