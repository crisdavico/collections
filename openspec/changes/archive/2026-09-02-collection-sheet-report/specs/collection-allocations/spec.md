# Delta for collection-allocations

## ADDED Requirements

### Requirement: Allocation line document_kind

Each `collection.allocation.line` MUST have required Selection
`document_kind` with values `invoice` and `quotation` only, default
`invoice`. Existing rows MUST backfill via `_init_column` (MUST NOT add a
`migrations/` folder). Operators MUST set `quotation` on a draft line.
The allocation form line list MUST inject `document_kind` immediately
before `invoice_number` via an inherited view (MUST NOT edit
`collection_allocation_views.xml`). That list MUST use `<list>` (MUST NOT
`<tree>`). MCP `create_collection_allocation` MUST stay unchanged: payload
and response MUST NOT gain `document_kind`; omitted kind MUST persist the
default `invoice`.

#### Scenario: Default invoice

- GIVEN a new allocation line with no `document_kind` in vals
- WHEN the line is created (ORM or MCP)
- THEN `document_kind` MUST be `invoice`

#### Scenario: Required selection

- GIVEN the line field
- WHEN selection and requiredness are inspected
- THEN values MUST be exactly `invoice` and `quotation`
- AND the field MUST be required

#### Scenario: Quotation round-trip on draft

- GIVEN a draft allocation line
- WHEN `document_kind` is written `quotation` and read back
- THEN stored `document_kind` MUST be `quotation`

#### Scenario: Inherited view before invoice_number

- GIVEN the allocation form line list arch after inherit
- WHEN field order is inspected
- THEN `document_kind` MUST appear immediately before `invoice_number`
- AND the line list tag MUST be `<list>`

#### Scenario: MCP create omits kind

- GIVEN a valid `create_collection_allocation` payload with invoices and no
  `document_kind` key
- WHEN the tool succeeds
- THEN each created line MUST have `document_kind` `invoice`
- AND request and response schemas MUST be unchanged
