# Delta for collection-vouchers

## ADDED Requirements

### Requirement: Internal collection payment helpers

Internal `_collection_*` helpers on `muk_mcp.mixin` MUST remain (parse payment
vals, attachment nest, provenance nests, create vouchers, submit-order
payload, classify/replay/conflict, require internal seller). They MUST NOT be
registered as MCP tools. `create_collection_allocation` MUST reuse them.
Payment items MUST omit `customer_identification`; helpers MUST take
top-level identification and replicate it per payment. Exact same-company
`document_id` set MUST be reusable by allocation (continue; MUST NOT
voucher-only early-return). Partial overlap and other-company hits MUST stay
generic conflict with no writes. Optional nested `attachment` and
`raw_ocr`/`seller_confirmed` parse rules MUST still apply on the fused write.

#### Scenario: Helpers not discovered as MCP tools

- GIVEN the MCP registry for `registry=mcp`
- WHEN tools are discovered
- THEN `create_collection_vouchers` MUST NOT appear
- AND `_collection_*` helpers MUST NOT have `@mcp_tool` or a `muk_mcp.tool` row

#### Scenario: Allocation reuses helpers

- GIVEN inline payments with top-level identification
- WHEN `create_collection_allocation` runs
- THEN helpers MUST parse payments, nests, and payload order
- AND MUST NOT require per-payment `customer_identification`

## MODIFIED Requirements

### Requirement: MCP optional payment attachment on create

`create_collection_allocation` MAY accept one optional nested attachment per
payment with required `name`, `mimetype`, and base64 `datas` when present.
Declared `mimetype` MUST match content detection (`image/*` or PDF only);
mismatch or bad base64 MUST raise `UserError` with no writes. Create with
attachments MUST persist all vouchers and files atomically under a savepoint
by posting each nest onto the new voucher chatter via `message_post` (MUST
NOT write Binary `attachment`). Exact same-company `document_id` reuse MUST
NOT add, replace, or compare attachments (even when a voucher has none) and
MUST continue to allocation. All-new and conflict rules MUST remain unchanged
except as this change specifies for company, seller, and type gates.
(Previously: Nested attachments were accepted by MCP `create_collection_vouchers`.)

#### Scenario: MCP create with nested attachment

- GIVEN unused `document_id`s and a payment with valid nested attachment
- WHEN `create_collection_allocation` runs
- THEN vouchers and the nested file MUST persist atomically under a savepoint
- AND the file MUST appear on that voucher's chatter as designated proof

#### Scenario: MCP attachment MIME mismatch rejected

- GIVEN nested attachment with mismatched or non-image/non-PDF `mimetype`
- WHEN `create_collection_allocation` runs
- THEN MUST raise `UserError` with no writes

#### Scenario: Exact-retry skips attachment writes

- GIVEN every submitted `document_id` already exists in the same company
- WHEN retried with or without nested attachments
- THEN matching vouchers MUST be unchanged; attachments MUST NOT be
  written/replaced/compared
- AND the write MUST continue to allocation

### Requirement: MCP nested provenance on all-new create

`create_collection_allocation` MAY accept nested `raw_ocr` and
`seller_confirmed` with the same typed keys as current fields. When both
nests are present, seller-confirmed MUST equal top-level fields; current MUST
initialize from seller-confirmed; raw MUST persist as submitted. Omitting
both nests MUST leave empty provenance; UI/ORM create MUST remain allowed.
Malformed, one-sided, or mismatched nests MUST fail the batch with no writes.
Exact same-company `document_id` reuse MUST ignore those nests with no
provenance mutation and MUST continue to allocation.
(Previously: Nested provenance was accepted by MCP `create_collection_vouchers`.)

#### Scenario: Unchanged seller confirmation

- GIVEN unused `document_id`s and both nests equal to top-level payment fields
- WHEN all-new create runs
- THEN raw, seller-confirmed, and current MUST be equal

#### Scenario: Seller correction

- GIVEN raw nest differs from seller-confirmed, and seller-confirmed equals
  top-level
- WHEN all-new create runs
- THEN raw MUST persist unchanged
- AND seller-confirmed and current MUST contain the correction

#### Scenario: Both nests omitted leave empty provenance

- GIVEN UI or MCP create with neither `raw_ocr` nor `seller_confirmed`
- WHEN create completes
- THEN raw and seller-confirmed MUST be empty
- AND current payment fields MUST persist as submitted

#### Scenario: Bad provenance fails the batch

- GIVEN a payment with one-sided, malformed, or mismatched nests
- WHEN `create_collection_allocation` runs
- THEN the call MUST fail with no writes

#### Scenario: Exact replay ignores provenance nests

- GIVEN every submitted `document_id` already exists in the same company, with
  or without stored provenance
- WHEN retried with different or omitted nests
- THEN matching vouchers MUST return unchanged
- AND provenance and snapshots MUST NOT be written, backfilled, or mutated

### Requirement: Cross-company document_id reject not replay

`document_id` uniqueness MUST remain global among non-null values. When a new
write collides with another company's `document_id`, the system MUST reject
it (MUST NOT replay) and MUST NOT disclose that voucher's id or name. A user
who can read both companies MUST NOT receive the other company's voucher as
an MCP replay via `create_collection_allocation`.
(Previously: Multi-company MCP replay named `create_collection_vouchers`.)

#### Scenario: Global uniqueness still holds

- GIVEN a non-null `document_id` already stored
- WHEN another voucher is saved with the same `document_id` in any company
- THEN the save MUST be rejected

#### Scenario: Other-company collision undisclosed

- GIVEN `document_id` D exists only on a company B voucher
- WHEN company A creates via UI, ORM, import, or MCP with D
- THEN the operation MUST fail with a generic error
- AND the response MUST NOT include company B's voucher id or name

#### Scenario: Multi-company reader must not replay the other company

- GIVEN a user allowed to read companies A and B, and D exists only on B
- WHEN they call `create_collection_allocation` in company A with D
- THEN the call MUST be rejected with no writes
- AND MUST NOT return B's voucher as replay

## REMOVED Requirements

### Requirement: MCP tool create_collection_vouchers

(Reason: Fused confirm is `create_collection_allocation` with inline
`payments[]`; a second write tool would drift from the Nebula contract and
split partner/sheet/idempotency paths.)
(Migration: Retire the `@mcp_tool` in work unit 3 (after/with Nebula deploy).
Keep `_collection_*` helpers internal and reuse them from allocation.
Re-point attachment, provenance, partner-resolve, and remaining MCP tests to
`create_collection_allocation`. Delete create/replay/ACL tests that only
covered the retired tool. Do not add a `muk_mcp.tool` row.)
