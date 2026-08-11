# Design: Optional image/PDF attachment per voucher line

## Technical Approach

Add one optional Binary + filename on `collection.voucher.line`, validate MIME/base64
server-side, expose binary widgets on typed One2many lists and Payment Lines list, and
extend MCP so creates store files inside the existing savepoint while exact-retry never
writes attachments. Delta specs cover model/UI/MCP. `AGENTS.md` attachment rules are
already updated (prerequisite — do not re-edit).

## Architecture Decisions

| Decision         | Options                                                         | Choice                                         | Rationale                                      |
| ---------------- | --------------------------------------------------------------- | ---------------------------------------------- | ---------------------------------------------- |
| Storage          | Binary `attachment=True` + Char vs M2O `ir.attachment`          | **Binary + Char**                              | Spec/`AGENTS.md`; one file via ORM attachments |
| Names            | `attachment`/`attachment_filename` vs `datas`/`datas_fname`     | **Former**                                     | Clear; avoids `ir.attachment.datas` clash      |
| Validation       | `guess_mimetype` + `b64decode(validate=True)` vs extension-only | **Odoo guess + decode/`binascii`**             | Content-based; reject bad base64               |
| Allow-list       | Strict set vs `image/*` + PDF                                   | **`image/*` or `application/pdf`**             | Spec; detected MIME wins                       |
| Hook             | `@api.constrains` vs create/write override                      | **`@api.constrains('attachment')`**            | UI + MCP; empty skips                          |
| MCP parse timing | Always validate nest vs create-only                             | **Create-only after all-new**                  | Exact-retry must not compare/write             |
| Nest shape       | Flat keys vs nested object                                      | **`{name,mimetype,datas}`**                    | Proposal; all required when present            |
| UI accept        | Ext-only vs MIME                                                | **`accepted_file_extensions`: `image/*,.pdf`** | Odoo 19 binary widget                          |
| Payment Lines    | List-only vs add form                                           | **List-only**                                  | Matches typed-views design                     |
| Version          | Patch vs minor                                                  | **`19.0.1.2.0` → `19.0.1.3.0`**                | New fields + behavior                          |

## Data Flow

```
UI / MCP payment
  ├─ omit ──────────────────────────► line save (no file)
  ├─ UI binary ──► ORM Binary+filename ──► constrain (decode + guess_mimetype)
  └─ MCP nest ──► (all-new only) map name→filename, datas→Binary
                      existing savepoint: Voucher.create + Line.create → ir.attachment
Exact-retry (full same-voucher document_ids)
  → replay return; ignore attachment keys; no write
```

## File Changes

| File                                | Action    | Description                                                  |
| ----------------------------------- | --------- | ------------------------------------------------------------ |
| `models/collection_voucher_line.py` | Modify    | Binary+filename (`copy=False`); MIME/base64 → `UserError`    |
| `tools/collection_voucher.py`       | Modify    | Nested schema; create-path validate/map; replay unchanged    |
| `views/collection_views.xml`        | Modify    | Widgets on 3 typed lists + Payment Lines list; accept filter |
| `tests/test_collection_payment.py`  | Modify    | Omit / valid / bad b64 / wrong MIME / `copy=False`           |
| `tests/test_collection_ui.py`       | Modify    | Arch: widgets + accept on typed + lines list                 |
| `tests/test_collection_mcp_tool.py` | Modify    | Atomic create; MIME fail no writes; retry no attach write    |
| `__manifest__.py`                   | Modify    | Version `19.0.1.3.0`                                         |
| `AGENTS.md`                         | Unchanged | Prerequisite already done                                    |

## Interfaces / Contracts

```python
attachment = fields.Binary(attachment=True, copy=False)
attachment_filename = fields.Char(copy=False)
# if attachment: raw = b64decode(..., validate=True); mime = guess_mimetype(raw)
# allow mime.startswith("image/") or mime == "application/pdf" else UserError
```

```xml
<field name="attachment" widget="binary" filename="attachment_filename"
       options="{'accepted_file_extensions': 'image/*,.pdf'}"/>
<field name="attachment_filename" optional="hide"/>
```

MCP nest (optional per payment): required `name`, `mimetype`, `datas` when present;
declared `mimetype` MUST equal detected allow-listed MIME; map into line vals inside
existing `cr.savepoint()`. Never `sudo()`.

## Testing Strategy

Strict TDD: RED → GREEN → `invoke test -m collection`.

| Layer   | What                                                                            | Approach                       |
| ------- | ------------------------------------------------------------------------------- | ------------------------------ |
| Model   | Omit; valid PNG/PDF + `ir.attachment`; bad b64/MIME → `UserError`; `copy=False` | `test_collection_payment.py`   |
| UI arch | Typed lists + Payment Lines list: binary, filename, accept                      | `test_collection_ui.py`        |
| MCP     | Atomic attach create; mismatch/bad b64 no writes; exact-retry unchanged binary  | `test_collection_mcp_tool.py`  |
| Upgrade | Fields/views load                                                               | `invoke install -m collection` |
| E2E     | N/A                                                                             | Not available                  |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification,
or process-integration boundary.

## Migration / Rollout

No data migration; upgrade adds optional columns. Manifest `19.0.1.3.0`. Rollback:
revert + upgrade; drop columns/orphaned attachments only if reverse migration required.

## Open Questions

- None.
