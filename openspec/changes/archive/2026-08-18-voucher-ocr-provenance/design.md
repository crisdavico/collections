# Design: Voucher OCR Provenance

Stamp typed `ocr_*`/`seller_*` copies of `_REVIEW_EDITABLE_FIELDS` on all-new MCP
create; keep current payment columns editable; append
`collection.voucher.review.snapshot` only from `_write_review_decision`. Exact replay
and form Approve/Reject never write provenance or history. CodeGraph init failed (exit
127); design from Read/Grep of the paths below.

## Architecture Decisions

| Decision | Options | Tradeoff | Choice |
|---|---|---|---|
| Raw/seller | Typed columns vs JSON | JSON untyped; new here | `ocr_*`/`seller_*` same types; `copy=False`; view `readonly` |
| Mutate | UI readonly vs `write()` | `readonly` is UI-only | `write()` rejects keys; `create()` may stamp |
| History | Snapshot vs chatter vs JSON | Chatter is not full-field | Snapshot model; append from `_write_review_decision` only |
| Snapshot path | DR helper vs form buttons | Form has no lock/vals | `action_approve`/`action_reject` do **not** append |
| MCP shape | Nested vs flattened keys | Flatten collides | `raw_ocr` + `seller_confirmed`; `document_id`/`attachment` top-level |
| Nest parse | `_collection_parse_payment_vals` vs create-only | Early parse breaks replay | Same as attachment: after existing-check, before savepoint |
| Equality | Ad-hoc vs `_PAYMENT_OPTIONAL_FIELDS` | omit/`null`/`""` traps | Reuse optional parse; nest `document_type` required |
| Snapshot ACL | sudo vs context | Addon forbids sudo | `read=1,create=1,write=0,unlink=0`; flag `collection_review_snapshot`; no groups/`ir.rule` |
| UI | Form and/or OWL | OWL is the review tool | Form notebook three-way + history; OWL via queue payload |

## Data Flow

```
MCP: parse current → existing? replay (ignore nests) : parse attachment+provenance
     → savepoint create (stamp ocr_*/seller_*) → list payload
DR:  FOR UPDATE → _write_review_decision (approve incl. empty vals | reject)
     → write current/state → append snapshot of current typed fields
Form: action_approve|action_reject → state/audit only → no snapshot
```

All-new: parsed `seller_confirmed` MUST equal top-level payment minus `document_id`.
Current stays top-level. Raw may differ. Both nests omitted → null provenance.
One-sided/malformed/mismatch → `UserError` before write. UniqueViolation replay ignores
nests.

## File Changes

| File | Action | Description |
|---|---|---|
| `models/collection_voucher.py` | Modify | `ocr_*`/`seller_*`; `write()` reject; One2many; snapshot from `_write_review_decision`; queue keys |
| `models/collection_voucher_review_snapshot.py` | Create | Gated `create`; refuse `write`/`unlink` |
| `models/__init__.py` | Modify | Import snapshot |
| `tools/collection_voucher.py` | Modify | Schema + create-path stamp; replay unchanged |
| `views/collection_views.xml` | Modify | Notebook Current/Raw/Seller/history; type `invisible=`; hide `document_id` on provenance pages |
| `static/src/document_review/document_review_action.xml` | Modify | Readonly raw/seller beside current; keep `isBankTransfer`/`isCheck`; no `document_id` |
| `static/src/document_review/document_review_helpers.esm.js` | Modify | `buildApproveVals` current-only |
| `security/ir.model.access.csv` | Modify | Snapshot ACL for `base.group_user` |
| `__manifest__.py` | Modify | `19.0.1.14.0` |
| `tests/test_collection_*.py` | Modify | MCP/snapshot/ACL/UI/queue; allow history `<list>`, still forbid `payment_ids` |
| `migrations/19.0.1.13.0/` | Unchanged | Leave chatter scripts |

Store cash-deposit `voucher_number`/`voucher_date` in all three layers even when UI
hides them.

## Interfaces / Contracts

**Columns** (`copy=False`; not identity/attachment): for each `_REVIEW_EDITABLE_FIELDS`
name, `ocr_<name>` and `seller_<name>` with the same type/selection.

**Snapshot** `_name = "collection.voucher.review.snapshot"`: `voucher_id` (cascade),
`revision` (max+1), `reviewer_id`, `reviewed_at`, `decision` (`approved`/`rejected`),
full current typed set. `models.Constraint UNIQUE(voucher_id, revision)`. Monetary via
related `currency_id`. `@api.private` append **after** the decision `write`.

**MCP nests** (create path only): `_REVIEW_EDITABLE_FIELDS` keys; no base64. Snapshot
`create` requires context `collection_review_snapshot`.

**Queue**: `ocr_*`/`seller_*` (no `datas`). OWL approve sends current keys only.

```python
# snapshot.create — no sudo
if not self.env.context.get("collection_review_snapshot"):
    raise UserError(...)
# voucher.write
blocked = {f"{p}_{n}" for p in ("ocr", "seller") for n in self._REVIEW_EDITABLE_FIELDS}
if blocked & set(vals):
    raise UserError(...)
```

## Testing Strategy

| Layer | What | Where |
|---|---|---|
| MCP | omit→null; seller==top-level; raw may differ; one-sided/mismatch fail before write; exact + UniqueViolation ignore nests | `tests/test_collection_mcp_tool.py` |
| Review | empty approve + reject snapshot; reopen appends; form path does not; queue provenance, no base64 | `tests/test_collection_document_review.py` |
| ACL | gated create; write/unlink denied; portal denied; voucher `write` rejects keys; no sudo | `tests/test_collection_acl.py` |
| UI | notebook; type `invisible=`; history list; OWL hides `document_id` | `tests/test_collection_ui.py` + OWL source asserts |
| E2E | N/A | `openspec/config.yaml` |

`strict_tdd: true`. Chain PRs: model/MCP/ACL → form → OWL (400-line budget).

## Threat Matrix

N/A — Odoo model/MCP mixin/OWL. No routing, shell, subprocess, VCS/PR, executable-file,
or process-integration boundary.

## Migration / Rollout

`__manifest__.py` → `19.0.1.14.0`. ORM additive null columns + table on `-u collection`.
No backfill; no `migrations/19.0.1.14.0/`; do not edit `migrations/19.0.1.13.0/`.
Existing rows: current kept; raw/seller null; zero snapshots. Revert does not drop
columns/rows.

## Open Questions

- [ ] Non-blocking (locked): form Approve/Reject never snapshot — Document Review is
  the history path.
