# Exploration: align-allocation-contracts

Align Seedian `create_collection_allocation` so it accepts and strictly
validates Nebula’s `CollectionAllocationRequest.model_dump(mode="json")`
payload, including all seven payment document types. Keep MuK unchanged.
Exclude Odoo UI/report presentation. Coordinated consumer edit is limited to
the stale catalog note in Nebula `AGENTS.md`.

CodeGraph: queried collection at
`/home/crisd/projects/seedian/seedian/odoo/custom/src/private/collection`
(indexed). Nebula at `/home/crisd/projects/nebula/nebula-agent` has no
`.codegraph/`; Read/Grep used after that init check. Did not touch change
`2026-09-04-document-review-editable-ocr`.

## Current State

### Authoritative wire contract (Nebula)

`CollectionAllocationRequest` in `src/agent/schemas.py` is the payload
`submit_collection_allocations` sends via
`hydrated.model_dump(mode="json")`. Shape:

- Header: `seller_id` (int > 0), `customer_identification`, `request_id`,
  `payments` (min 1), `receipts` (min 1). `extra="forbid"`.
- Each payment: `document_id`, required `seller_confirmed` (`PaymentDocument`),
  optional `attachment` / `raw_ocr`. Seller-declared `cash` has no source; submit
  leaves `attachment` and `raw_ocr` unset (`null` on dump).
- Amounts serialize as decimal strings (`format(value, "f")`), dates as
  `YYYY-MM-DD`, unused typed fields as explicit `null`.
- Receipts: `document_kind` `invoice`|`quotation`; `values[]` min 1;
  `applications[]` may be empty (on account). Value/application amounts are
  also decimal strings. `number` is nullable text.
- `unsupported` cannot be allocated (Nebula `AllocationPayment` validator).
  OCR may still extract it.

Seven discriminated types and dump fields (only that variant’s fields; not a
flat superset):

| `document_type` | Writer | Fields on dump |
| --- | --- | --- |
| `bank_transfer` | OCR | `amount`, `from_account`, `to_account`, `voucher_number`, `voucher_date` |
| `check` | OCR | `amount`, `check_number`, `check_bank`, `check_issue_date`, `check_payment_date`, `check_type` |
| `echeck` | OCR | same as `check` |
| `cash_deposit` | OCR | `amount`, `to_account`, `voucher_number`, `voucher_date` |
| `retention_certificate` | OCR | `amount`, `voucher_number`, `voucher_date`, `retention_kind` (`iva`\|`ganancias`\|`iibb`\|`suss`\|`other` or null) |
| `cash` | `create_cash_payment` only | `amount`, `voucher_date`; no proof |
| `unsupported` | OCR | discriminator only; not submitted |

Attachment MIME: Nebula accepts `image/*` or `application/pdf`. Submit maps
source `image/jpg` through as `mimetype: "image/jpg"` (not normalized to
`image/jpeg`). `image/JPEG; charset=binary` is normalized to `image/jpeg`.

Unit proof: `tests/unit_tests/test_allocation_schemas.py`
(`amount` / `balance_seen` dump as `"150000"`) and
`test_schemas.py` (cash dump `{"document_type": "cash", "amount": "5000",
"voucher_date": "2026-05-01"}`).

Stale consumer note: Nebula `AGENTS.md` still claims Odoo catalog/Selection/MCP
must gain `echeck` / `cash` / `retention_certificate` before submit can
register them. That is the only Nebula file in scope.

### Seedian MCP schema vs runtime

Write tool: `tools/collection_allocation.py` `@mcp_tool`
`create_collection_allocation`. Advertised schema is a **flattened object**,
not a Pydantic `oneOf`. Payment items come from `_PAYMENT_SCHEMA` in
`tools/collection_voucher.py`.

**Advertised (discovery) today**

- Payment required: `document_id`, `seller_confirmed`. Optional `attachment`,
  `raw_ocr`.
- Provenance nest `document_type` enum:
  `bank_transfer`, `check`, `cash_deposit`, `unsupported` only.
  No `echeck`, `cash`, `retention_certificate`. No `retention_kind`.
- Amounts typed `"type": "number"` (receipt values, applications, nest
  `amount`). Strings are not advertised.
- No `additionalProperties: false` on payment or receipt objects.

**Runtime Python (authoritative today; schema is not trusted)**

`_collection_parse_allocation_form` → `_collection_parse_payment_vals` then
receipts. Identity/`request_id` replay ignores nests.

- `seller_confirmed` required; `unsupported` rejected; amount must parse with
  `float(...)` and be `> 0` (so **decimal strings already work** at Python).
- Provenance nests: unknown keys vs
  `collection.voucher._REVIEW_EDITABLE_FIELDS` → UserError. `document_type`
  must be in `_DOCUMENT_TYPES` (same four codes). Optional fields copied only
  when not `None`/`""`. `retention_kind` is an unknown key today.
- Payment-object extra keys (not nest keys) are ignored, not rejected.
- `attachment` `None`/`False`/`""` → no sidecar (cash-shaped omit already
  works). Declared `mimetype` must **equal** `guess_mimetype(decoded)` exactly.
  JPEG bytes typically detect as `image/jpeg`, so Nebula `image/jpg` would
  fail MIME mismatch. Tests cover PNG vs declared PDF, not `image/jpg`.
- Explicit null/empty optional nest fields already match omit
  (`test_optional_omit_null_empty_nests_are_equal`).
- Receipt `float(amount)` / `float(balance_seen)` already accept numeric
  strings. Application `number` kept only if non-empty `str`; JSON `null` is
  dropped.

Existing allocation behavior to preserve: one customer per request,
`request_id` replay, draft writes, ERP `balance_seen` revalidation, receipt
persist, response `{sheet_id, vouchers, allocation}`.

### Catalog, Selection, allow-list

| Surface | Today |
| --- | --- |
| `data/collection_document_type_data.xml` | Four XMLIDs: `document_type_bank_transfer`, `_check`, `_cash_deposit`, `_unsupported`. Then `_collection_seed_allowed_document_types` (empty allow-lists only). |
| `COLLECTION_TYPE_CODES` (`models/res_company.py`) | Same four codes. `res.company.create` unions them via `_collection_enable_all_document_types` (`Command.link`, keeps extras). |
| Voucher `document_type` | `Selection="_selection_document_type"` over `_DOCUMENT_TYPE_SELECTION` (four). Filtered by company allow-list ∪ current value. |
| `ocr_*` / `seller_*` Selection | Hard-coded same four (not `_DOCUMENT_TYPE_SELECTION`). |
| Snapshot `models/collection_voucher_review_snapshot.py` | `_DOCUMENT_TYPE_SELECTION` four codes; no `retention_kind`. |
| `_REVIEW_EDITABLE_FIELDS` | `document_type`, `amount`, accounts, voucher_*, check_*. No `retention_kind`. Stamps `seller_*` / `ocr_*` from nest keys. |
| `_assert_new_work(..., document_type)` | Type must be in `allowed_document_type_ids`. MCP create uses this after parse. |

Manifest version is **`19.0.1.39.0`**. There is no `migrations/19.0.1.39.0/`
(receipts-only MCP input had no stored fields). Tests pin four catalog rows,
`19.0.1.39.0`, and forbid leftover migrate folders including `19.0.1.39.0`.
`_collection_seed_allowed_document_types` will **not** add new types to
companies that already have an allow-list; additive upgrade needs
`_collection_enable_all_document_types` (or equivalent `Command.link`) on
**every** company.

Document Review OWL (`document_review_helpers.esm.js`) labels only the four
types. **Out of scope** (UI/report excluded). Persistence of new Selection
values is still required so MCP create can stamp vouchers.

### Tests today

- `tests/test_collection_mcp_allocation.py`: schema freeze (four-type payment
  items, receipts-only input, response keys), replay, draft persist, gates,
  UniqueViolation, `unsupported` reject, disallowed type via allow-list.
  Helpers default `document_type="bank_transfer"` and numeric amounts.
- `tests/test_collection_mcp_tool.py`: attachments, provenance nests, omit/null
  equality, MIME mismatch. No `echeck`/`cash`/`retention_certificate` /
  string-decimal / `image/jpg` goldens.
- `tests/test_collection_company_settings.py`: `CATALOG_XMLIDS` length 4;
  `test_catalog_has_exactly_four_seeded_types`.
- `tests/test_collection_company_migration.py`: `ALL_TYPE_CODES` four;
  `test_manifest_version_is_1_39_0`; AGENTS.md pin `19.0.1.39.0`.

### MuK

Collection already advertises a flattened nest (enum + optional properties),
not a discriminated `oneOf`. Product constraint: MuK discovery sanitizer
cannot preserve Pydantic `oneOf`/`anyOf`. Do **not** fork or edit MuK.
Exactness belongs in collection runtime validation plus golden tests.
`muk_mcp` source is git-aggregate-managed and was not edited or proposed for
edit; CodeGraph on the parent Doodba tree has no index.

## Affected Areas

- `tools/collection_voucher.py` — `_DOCUMENT_TYPES`, `_PAYMENT_OPTIONAL_FIELDS`,
  `_PROVENANCE_NEST_SCHEMA` / `_PAYMENT_SCHEMA`, payment/provenance/attachment
  parse (types, `retention_kind`, decimal strings, unknown keys, `image/jpg`).
- `tools/collection_allocation.py` — receipt amount schema/runtime; keep
  identity, replay, persist, response unchanged.
- `data/collection_document_type_data.xml` — add XMLIDs for `echeck`, `cash`,
  `retention_certificate`.
- `models/res_company.py` — `COLLECTION_TYPE_CODES`; create-time union already
  uses this tuple.
- `models/collection_voucher.py` — `_DOCUMENT_TYPE_SELECTION`; `ocr_*` /
  `seller_*` Selection; `_REVIEW_EDITABLE_*`; new `retention_kind` plus
  `ocr_retention_kind` / `seller_retention_kind`.
- `models/collection_voucher_review_snapshot.py` — Selection + `retention_kind`
  so snapshots can copy review fields (persistence, not UI).
- `migrations/19.0.1.40.0/post-migrate.py` — **new**; union catalog types onto
  every company allow-list.
- `__manifest__.py` — `19.0.1.40.0`.
- `tests/test_collection_mcp_allocation.py`,
  `tests/test_collection_mcp_tool.py` — golden Nebula dumps; new types; cash
  without proof; `image/jpg`; string decimals; `retention_kind`; unknown keys.
- `tests/test_collection_company_settings.py`,
  `tests/test_collection_company_migration.py` — seven XMLIDs; manifest 1.40.0;
  migrate folder required (unlike 1.39.0).
- `AGENTS.md` (collection) — catalog/version/migrate notes (apply phase).
- `/home/crisd/projects/nebula/nebula-agent/AGENTS.md` — remove stale catalog
  blocker for `echeck`/`cash`/`retention_certificate`.
- OpenSpec main specs `collection-vouchers` / `collection-allocations` (delta
  in later phases) — payment type set and wire validation.
- **Do not edit:** MuK; Document Review OWL/views/reports; change
  `2026-09-04-document-review-editable-ocr`; `odoo/custom/src/odoo/` / `OCA/`.

## Approaches

1. **Runtime-strict flattened contract (recommended)** — Keep a MuK-safe
   flattened JSON Schema (seven-value `document_type` enum; optional fields
   including `retention_kind`; amounts advertised as number-or-string). Enforce
   Nebula dump exactness in Python: seven types, type-owned fields,
   `extra=forbid`-equivalent unknown keys on nests, decimal strings, explicit
   nulls, cash without proof, `image/jpg` aliased to detected `image/jpeg`.
   Catalog + Selection + `_REVIEW_EDITABLE_FIELDS` + `19.0.1.40.0` post-migrate
   union. Golden tests from `model_dump(mode="json")` fixtures.
   - Pros: Matches product constraints; no MuK fork; preserves allocation
     semantics; TDD-friendly goldens; schema can mention string amounts so
     discovery is not a lie.
   - Cons: Flattened schema cannot express per-type `oneOf`; clients other
     than Nebula could send mixed-type fields unless runtime rejects them.
   - Effort: Medium

2. **Advertise Pydantic `oneOf` on MuK / patch sanitizer** — Generate MCP
   schema from the Nebula union.
   - Pros: Discovery would match the dump.
   - Cons: Forbidden (MuK sanitizer strips `oneOf`/`anyOf`; do not edit MuK).
     False security if advertised then stripped.
   - Effort: High (and out of scope)

3. **Catalog-only expansion, keep loose parser** — Add three XMLIDs and enum
   values; leave nest parse as a flat optional-field union; keep
   `"type": "number"`; no `image/jpg` alias; no unknown-key tightening.
   - Pros: Smaller diff; existing numeric tests unchanged.
   - Cons: `retention_kind` still rejected; `image/jpg` still fails; schema
     still lies about strings; not “strict”; cash/`echeck` may persist but
     mixed/extra keys remain silent.
   - Effort: Low

## Recommendation

Use **approach 1**.

Implementation sketch for later phases (not this explore write):

1. Expand `COLLECTION_TYPE_CODES`, catalog XMLIDs, voucher/snapshot/ocr/seller
   Selection, `_DOCUMENT_TYPES`, `_PAYMENT_OPTIONAL_FIELDS`, and
   `_REVIEW_EDITABLE_FIELDS` with `echeck`, `cash`, `retention_certificate`,
   and `retention_kind` (Selection matching Nebula’s five kinds).
2. Bump manifest to `19.0.1.40.0`. Add
   `migrations/19.0.1.40.0/post-migrate.py` that calls
   `_collection_enable_all_document_types()` on all companies (union, keep
   extras). Do not use seed-empty-only.
3. Runtime: accept `float`/`str` decimals; treat nest `null`/`""` as omit;
   reject unknown nest keys; reject `document_type` outside the seven codes;
   keep rejecting allocate of `unsupported` and non-positive amount; allow
   cash with `attachment`/`raw_ocr` null/omitted; alias `image/jpg` ↔
   `image/jpeg` (and case) when comparing declared vs detected MIME.
4. Prefer rejecting fields that do not belong to the discriminator (strict
   Nebula dump) rather than silently storing `check_number` on a
   `bank_transfer`. Flattened schema still lists the union of properties.
5. Do not change persist/replay/revalidation/response. Do not change OWL
   labels or reports in this change.
6. Tests first (`strict_tdd: true`): goldens for each of the seven types’
   dumps; cash without proof; `retention_kind`; string decimals on payments
   and receipts; `image/jpg`; unknown key; catalog count 7; migrate union on
   a company that already had four types.
7. Nebula: delete the AGENTS.md paragraph that says catalog blocks
   `echeck`/`cash`/`retention_certificate`. No agent code change.

## Risks

- **`image/jpg` vs `image/jpeg`:** exact MIME equality will reject Nebula
  JPEG proofs tagged `image/jpg` unless aliased.
- **Allow-list migrate:** seed-empty-only would leave existing companies
  unable to accept the three new types; union-all is required.
- **`retention_kind` persistence:** without a voucher/snapshot field, nest
  parse cannot stamp provenance (`_REVIEW_EDITABLE_FIELDS` drives both parse
  allow-list and `seller_*`/`ocr_*` columns).
- **Flattened schema vs strict runtime:** discovery will not encode
  per-type `oneOf`; golden tests must lock runtime. Other MCP clients could
  send mixed fields if runtime stays a flat union.
- **Document Review UI lag:** new types can appear as raw codes in OWL until
  a later UI change (accepted; UI excluded). Cash has no proof so it will not
  enter the review queue (queue requires designated attachment).
- **Test/doc pins:** settings, migration, and AGENTS.md still say four types
  and `19.0.1.39.0`; they must move with the bump.
- **400-line review budget:** catalog + fields + parse + goldens + migrate +
  two AGENTS.md files may exceed one PR; `sdd-tasks` should forecast chained
  PRs. `delivery_strategy` is `auto-chain`.
- **Sibling change:** `2026-09-04-document-review-editable-ocr` is still
  active; do not merge folders or edit its artifacts.
- **Float vs Decimal:** Seedian stores Monetary via `float(...)`. Nebula uses
  `Decimal` strings. Existing `currency.compare_amounts` path is unchanged;
  goldens should use amounts that survive float (avoid binary-rounding traps
  in equality tests).

## Ready for Proposal

Yes. Scope, authoritative dump, Seedian gaps, MuK constraint, migrate
strategy, and test surfaces are clear. Orchestrator should tell the user
proposal can proceed with approach 1, no product questions, UI/MuK out of
scope, and Nebula limited to the AGENTS.md catalog note.
