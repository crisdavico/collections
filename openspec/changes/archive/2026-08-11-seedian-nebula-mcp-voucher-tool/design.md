# Design: Atomic idempotent `create_nebula_voucher` MCP tool

## Technical Approach

Extend `seedian_nebula` with a method-kind MuK MCP write tool (Approach 1 /
proposal). Inherit `muk_mcp.mixin`, decorate `@api.model` + `@mcp_tool` — no DB
`muk_mcp.tool` row. Tool validates input, resolves idempotency by payment
`document_id`, then savepoint-creates voucher + batched payment lines or returns
an existing voucher. Drop `received_date`; UI shows readonly `create_date`. Spec
delta: ADDED MCP + `document_id` uniqueness; MODIFIED header/UI requirements.

## Architecture Decisions

| Decision | Options | Choice | Rationale |
|----------|---------|--------|-----------|
| Registration | DB tool / `@mcp_tool` mixin | `_inherit='muk_mcp.mixin'` + `@mcp_tool(name='create_nebula_voucher', category='write', registry='mcp')` | Matches `muk_mcp/mcp/write.py`; method-indexed; no XML tool row |
| Depend | Soft / hard `muk_mcp` | Hard: `depends` += `muk_mcp` | Required for mixin; already aggregated |
| Schema | Full JSON Schema / allowlist | Nested `object`/`array`/`properties`/`required`/`enum`/`nullable`/`items` only | `to_strict_schema` silently strips `oneOf`/`$ref`/`additionalProperties` |
| Idempotency key | Customer+docs / docs only | Payment `document_id` set only | Spec: idempotency by `document_id`; replay ignores customer mismatch |
| Race on UniqueViolation | Reject / replay | **Replay**: catch `psycopg2.errors.UniqueViolation` outside savepoint → re-lookup → full same-voucher match returns existing; else `UserError` | Concurrent identical retries are the happy path for agents; reject alone forces a spurious failure then retry |
| Atomic create | Nested O2M / separate creates | Savepoint: `Voucher.create` then `Payment.create([{...}, ...])` | Same pattern as `_mcp_create_records`; batch avoids N inserts |
| ACL | sudo / caller env | No `sudo()`; `env` from MCP key user | `_execute` already calls without sudo; ORM enforces `base.group_user` ACL |
| `document_id` | Required field / nullable + MCP check | Nullable Char + `models.Constraint('unique(document_id)', …)`; MCP validates non-empty | PG unique allows many NULLs → UI lines OK |
| `received_date` | Keep / drop | Drop field + column; views → readonly `create_date` | Spec MODIFIED; registration time is ORM create time |

## Data Flow

```
MCP tools/call
    → muk_mcp.tool._call(env=key.user)
    → create_nebula_voucher(**args)   # no sudo
         │
         ├─ validate customer + payments + unique doc ids in call
         ├─ search payments by document_id ∈ submitted
         │     0 matches ──────────► savepoint create voucher+lines
         │     all + 1 voucher ────► return existing (replay)
         │     else ───────────────► UserError (no writes)
         └─ UniqueViolation on create ► rollback savepoint ► re-lookup
               full match → replay payload; else → UserError
```

## File Changes

Under `odoo/custom/src/private/seedian_nebula/`:

| File | Action | Description |
|------|--------|-------------|
| `__manifest__.py` | Modify | `depends` += `muk_mcp`; version `19.0.1.1.0` |
| `__init__.py` | Modify | `from . import tools` |
| `tools/__init__.py`, `tools/nebula_voucher.py` | Create | Mixin + `create_nebula_voucher` |
| `models/seedian_nebula_voucher.py` | Modify | Remove `received_date` |
| `models/seedian_nebula_payment.py` | Modify | Add `document_id` Char + `models.Constraint` unique |
| `views/seedian_nebula_views.xml` | Modify | Replace `received_date` with readonly `create_date` (list/search/kanban/form) |
| `migrations/19.0.1.1.0/post-migrate.py` | Create | `DROP COLUMN IF EXISTS received_date` on voucher table |
| `tests/test_seedian_nebula_mcp_tool.py` | Create | Tool + idempotency + ACL via `_call` |
| `tests/test_seedian_nebula_voucher.py`, `test_seedian_nebula_ui.py`, `tests/__init__.py` | Modify | Drop date asserts; UI → `create_date`; register MCP tests |

No ACL CSV / sequence / `repos.yaml` changes.

## Interfaces / Contracts

**Input** (`input_schema` — allowlist-safe):

- `customer_identification` (string, required)
- `payments` (array, `minItems: 1`, required); items: required
  `document_id`, `document_type` (`bank_transfer`\|`check`\|`cash_deposit`\|`unsupported`);
  optional nullable: `amount`, `from_account`, `to_account`, `voucher_number`,
  `voucher_date`, `check_number`, `check_bank`, `check_issue_date`,
  `check_payment_date`, `check_type` (`common`\|`deferred`)
- No `received_date`, `currency_id`, or `state` inputs

**Return** (JSON-serializable dict):

```python
{
  "id": int, "name": str, "state": str,
  "payments": [{"id": int, "document_id": str}, ...],
}
```

Create path: `state='new'`, currency = model default (`env.company.currency_id`).
Tool name `create_nebula_voucher` must stay globally unique across mixin MRO.

## Testing Strategy

Strict TDD (`invoke test -m seedian_nebula`). Pattern:
`self.env['muk_mcp.tool']._call(name, args, self.env(user=…))` like
`muk_mcp/tests/test_tools.py`.

| Layer | What | Approach |
|-------|------|----------|
| Unit/integration | All-new, exact-retry, in-call dup, partial, cross-voucher, ACL deny | `TransactionCase`; assert JSON + row counts; `AccessError` for non-internal |
| Unit | Nullable `document_id` UI create; unique constraint | Payment create w/o id OK; duplicate non-null → IntegrityError |
| Unit | Defaults / UI | Drop `received_date` tests; assert `create_date` in views; no `received_date` in arch |
| Race (optional RED) | UniqueViolation → replay | Force conflict in savepoint or dual create; expect replay payload |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file
classification, or process-integration boundary. Uses existing `muk_mcp`
dispatch; this change only adds a mixin method.

## Migration / Rollout

1. Bump to `19.0.1.1.0`; install/upgrade requires `muk_mcp`.
2. **Destructive**: `post-migrate.py` drops `received_date` — values unrecovered.
   Snapshot non-empty DBs (`prod.sql.gz` / BI extracts) before upgrade.
   **Archive-gate**: warn on destructive merge per `openspec/config.yaml`
   `rules.archive`.
3. Rollback: revert module version (tool unregisters). Dropped dates stay gone.

## Open Questions

- None blocking. Locked: race → replay-after-relookup; customer ignored on
  document_id match; hard `muk_mcp` depend accepted.
