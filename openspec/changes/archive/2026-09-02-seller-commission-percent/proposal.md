# Proposal: Seller Commission Percent

## Intent

Sellers have no commission rate. After Import, back-office must see a stored 0–100
**Commission %** (read-only) on Settings and connector Seller Bindings. Store/display
only.

**Assumptions (settled):** `commission_percent` / `Commission %`; 0–100 (`5.0` = 5%);
on `collection.connector.seller.binding` not `res.users`; connector → Import is
source of truth; re-Import overwrites; missing list key → `0.0`; invalid → generic
`UserError` before any write.

## Scope

### In Scope

- SQLite `commission_percent REAL NOT NULL DEFAULT 0` + CHECK 0–100; fixtures Ana
  5.0, Bruno 7.5, Carla 10.0, Diego 0.0, Elena 3.0, Facundo 5.0 (inactive); sqlite
  `19.0.1.5.0` → `19.0.1.6.0` + post-migrate rematerialize sample
- `list_sellers()` copies the key (missing → `0.0`); Import validate-then-write;
  upsert `write`s existing bindings
- Binding `Float(digits=(16, 2), required=True, default=0.0)` + `models.Constraint`;
  readonly Settings One2many + connector Seller Bindings notebook
- collection `19.0.1.27.0` → `19.0.1.28.0` (no collection `migrations/`); modify
  `collection-connectors`: drop four-tuple and `` `database.sql` MUST NOT change ``

### Out of Scope

- MCP `get_seller_id`; nebula-agent (overrides `config.yaml` Nebula-in-scope rule);
  applying rate on allocations/vouchers; `res.users`; `_DISPATCH_OPS`
- Collision paths: allocation models/tests, `draft-until-close`, `inline-collection-allocation`

## Capabilities

### New Capabilities

None

### Modified Capabilities

- `collection-connectors`: sellers schema includes `commission_percent`;
  `list_sellers` + Import persist/overwrite; drop stale
  `` `database.sql` MUST NOT change ``

## Approach

SQLite column → `list_sellers()` → Import validate → binding create/`write` →
readonly views. Invalid (`<0`, `>100`, non-numeric) fails in
`_collection_validate_connector_seller_rows` before writes. Rematerialize sample via
`ensure_sample_sqlite_source` in sqlite `migrations/19.0.1.6.0/`. Strict TDD; Odoo 19
`models.Constraint`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `collection_connector_sqlite/` | Modified | Schema, SELECT, fixtures, `19.0.1.6.0`, post-migrate, tests |
| collection models/views/tests | Modified | Float+Constraint; format; validate; upsert write; readonly UI |
| `openspec/specs/collection-connectors/spec.md` | Modified | Schema + Import overwrite |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Custom sqlite files lack column | Med | Required-column fail-close; operators ALTER |
| Create-only upsert leaves `0.0` | High | Import must `write` existing bindings |
| Formatter drop / test DDL miss | Med | Copy+coerce `0.0`; grow every `_write_*` CREATE |
| Two-repo size / spec freeze | Med | Split work units; drop `` MUST NOT change `` |

## Rollback Plan

Revert sqlite schema/migrate and collection field/Import/UI. Uninstall sqlite leaves
vouchers/MCP unchanged. Custom sqlite may keep the extra column (`DEFAULT 0`).

## Dependencies

- Sibling `collection_connector_sqlite` (not nebula-agent)
- Odoo 19 Float + `models.Constraint`; existing Import/upsert

## Success Criteria

- [ ] SQLite + `list_sellers` + Import persist fixture rates; missing key → `0.0`;
      invalid fail-closed with zero writes; re-Import overwrites
- [ ] Views show readonly `Commission %`; MCP `get_seller_id`, nebula-agent,
      allocations/vouchers unchanged
- [ ] `collection-connectors` spec no longer freezes four-tuple / `database.sql`
