# Design: Add Pluggable Collection Connectors

## Technical Approach

`collection.connector` holds provider config. Company M2O `collection_connector_id`
(related writable on Collection Settings) selects it. Public `test_connection` /
`list_sellers` dispatch to addon `_<type>_*` (`selection_add`). Dispatch uses
allowlisted `getattr` (see Dispatch decision). MCP `list_collection_sellers` lives only
in `collection` (`tools/collection_connector.py`):
`env.company.collection_connector_id`, no caller `company_id`, no `sudo()`, no DB
`muk_mcp.tool` row. SQLite is a sibling addon. List skips `_assert_new_work`. Spec:
`specs/collection-connectors/spec.md`.

## Architecture Decisions

| Decision             | Choice                                                                                                                                                                   | Alternatives considered                      | Rationale                                                                 |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------- | ------------------------------------------------------------------------- |
| Dispatch             | `_dispatch(op)` allowlists `op ∈ {test_connection, list_sellers}` and type in Selection keys, then `getattr(self, f'_{type}_{op}')`; miss → generic `UserError`          | if/elif; unrestricted getattr                | plugins without editing collection; allowlist blocks getattr gadgets      |
| SQLite path          | `sqlite_path` Char on connector via sqlite `_inherit`; hidden unless type is sqlite                                                                                      | company field; Binary; related               | provider-record settled; Binary snapshots; company junk-drawer rejected   |
| Binding `company_id` | related stored `connector_id.company_id` (`required=True`, `precompute=True`, `index=True`)                                                                              | independent stored; related non-stored       | `ir.rule` needs stored company; related cannot drift (snapshot pattern)   |
| ACL                  | `group_user` read; `group_system` write; company `ir.rule`; portal/public denied; never `sudo()`                                                                         | full CRUD for `group_user`; extra groups     | MCP needs internal read; Settings already `group_system`; no extra groups |
| SQLite extend        | `_inherit = 'collection.connector'`; `selection_add=[('sqlite','SQLite')], ondelete={'sqlite':'cascade'}`; `@api.private` `_sqlite_*`; company M2O `ondelete='set null'` | mixin MCP override; `ondelete='set default'` | no duplicate MuK names; cascade+set-null clears leftover sqlite values    |

## Data Flow

```
MCP caller ──list_collection_sellers──► muk_mcp.mixin
                    env.company.collection_connector_id
                    missing/inactive → UserError
                              ▼
                    connector.list_sellers()
                    _dispatch → _sqlite_list_sellers
                    sqlite3 file:<abs>?mode=ro
                              ▼
         drop inactive; merge bindings → {sellers, source}
                                         (no path/SQL)
```

## File Changes

### Unit 1 — collection

| File                                                                                            | Action | Description                                 |
| ----------------------------------------------------------------------------------------------- | ------ | ------------------------------------------- |
| `models/collection_connector.py`                                                                | Create | Provider + dispatcher                       |
| `models/collection_connector_seller_binding.py`                                                 | Create | 1:1 bindings + UNIQUE Constraints           |
| `tools/collection_connector.py`                                                                 | Create | MCP `list_collection_sellers`               |
| `models/__init__.py`, `tools/__init__.py`                                                       | Modify | Import models/tool                          |
| `models/res_company.py`, `models/res_config_settings.py`, `views/res_config_settings_views.xml` | Modify | M2O + related Settings selector             |
| `views/collection_connector_views.xml`                                                          | Create | UI + `group_system` menus                   |
| `security/collection_security.xml`, `security/ir.model.access.csv`                              | Modify | company `ir.rule`; user read / system write |
| `__manifest__.py`                                                                               | Modify | `19.0.1.18.0` + data                        |
| `tests/test_collection_connector.py`                                                            | Create | dispatch, bindings, list≠collect            |
| `tests/test_collection_mcp_list_sellers.py`                                                     | Create | kind=method, portal deny                    |
| `tests/test_collection_{acl,company_settings,ui}.py`                                            | Modify | ACL, persist, XMLID                         |
| `tests/__init__.py`                                                                             | Modify | import tests                                |
| `AGENTS.md`                                                                                     | Modify | connector, MCP, sibling                     |

Unchanged: `tools/seller_lookup.py`, `tools/collection_voucher.py`.

### Unit 2 — sqlite addon + apply.roots

| File                                                                          | Action | Description                                 |
| ----------------------------------------------------------------------------- | ------ | ------------------------------------------- |
| `openspec/config.yaml`                                                        | Modify | `apply.roots` += sibling path before apply  |
| `../collection_connector_sqlite/__manifest__.py`                              | Create | `depends: ['collection']`; parent git       |
| `../collection_connector_sqlite/{__init__,models/__init__,tests/__init__}.py` | Create | package inits                               |
| `../collection_connector_sqlite/models/collection_connector.py`               | Create | `selection_add`, `sqlite_path`, `_sqlite_*` |
| `../collection_connector_sqlite/views/collection_connector_views.xml`         | Create | path + test-connection                      |
| `../collection_connector_sqlite/tests/test_sqlite_connector.py`               | Create | ro, schema, leak, path RED                  |

## Interfaces / Contracts

MCP `list_collection_sellers` (`category=read`, `registry=mcp`, method): no args.
`{sellers:[{external_seller_id,name,mobile,active,odoo_seller_id}], source:{connector_id,connector_type,connector_name,company_id}}`.
Drop inactive externals. `odoo_seller_id` int or null. UNIQUE
`(connector_id, external_seller_id)` and `(connector_id, user_id)`. SQLite
`sellers(id TEXT PK, name TEXT NOT NULL, mobile TEXT, active INTEGER NOT NULL DEFAULT 1)`.
Connect `sqlite3.connect('file:%s?mode=ro' % path, uri=True)` only if path is absolute
and has no `?`, `#`, or NUL.

## Testing Strategy

| Layer         | What to Test                                                                | Approach                                                   |
| ------------- | --------------------------------------------------------------------------- | ---------------------------------------------------------- |
| Unit          | dispatch miss, UNIQUE, ACL, settings, MCP method, portal deny, list≠collect | `invoke test -m collection --mode=update`                  |
| Integration   | sqlite `mode=ro`, schema, bindings, uninstall cascade                       | `invoke test -m collection_connector_sqlite --mode=update` |
| E2E           | N/A                                                                         | unavailable                                                |
| No-regression | `get_seller_id`, voucher MCP                                                | existing collection tests                                  |

## Threat Matrix

| Boundary                 | Minimum adversarial cases                                                  | Applicability                             | Design response                                                                                 | Planned RED tests                                                                                          |
| ------------------------ | -------------------------------------------------------------------------- | ----------------------------------------- | ----------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Documentation-like paths | `requirements.txt`, `CMakeLists.txt`, executable Markdown/MDX, `README.sh` | Applicable — admin path opened by process | Absolute path; URI `mode=ro`; never exec; generic `UserError` (no path/SQL); reject `?` `#` NUL | Per class: list+test on fixture → `UserError`, not executed, no path/SQL. Also relative and `path?mode=rw` |
| Git repository selection | `git -C`, relative, absolute                                               | N/A: no git                               | —                                                                                               | —                                                                                                          |
| Commit state             | staged, `commit -a`, empty index                                           | N/A: no git                               | —                                                                                               | —                                                                                                          |
| Push state               | tracking, first push, refspec                                              | N/A: no git                               | —                                                                                               | —                                                                                                          |
| PR commands              | `--head`, env prefix, composed                                             | N/A: no PR automation                     | —                                                                                               | —                                                                                                          |

Safe: valid `sellers` schema → list. Failure: missing, directory, non-db, injection,
relative → generic `UserError`, no leak.

## Migration / Rollout

Additive ORM models. Bump collection `19.0.1.18.0`. No voucher/sheet data migration. Two
units; extend `apply.roots` before unit 2. Rollback: clear `collection_connector_id`,
uninstall sqlite.

## Open Questions

None.
