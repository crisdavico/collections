## Production setup

1. **API user.** Give the user behind the agent's MCP API key **Collections User** only.
   The agent's tools never need Collections Manager (Close, Cancel, Reinstate,
   connectors, settings) and never need administrator rights.
2. **Tools.** The agent needs only the collection tools: `get_seller_id`,
   `list_collection_customers`, `customer_debt`, `get_collection_allocation`,
   `create_collection_allocation`, `get_collection_sheet_pdf`, `close_collection_sheet`,
   `declare_collection_cash` and `create_seller_deposit`. The generic muk_mcp write
   tools (`create_records`, `update_records`, `delete_records`, `call_method`) accept a
   caller-supplied `context` and arbitrary writes on any model the API user can reach,
   which skips every check the collection tools make. At the pinned muk_mcp version an
   API key has no per-tool switch, only a `read` or `write` scope, and the collection
   write tools need `write`. So expose only the collection tools to the model in the
   gateway's MCP client, and keep the API user's rights to Collections User.
3. **Seller identity.** Set the trusted seller header (below) and deploy the matching
   Nebula change, so the gateway, not the model, names the seller.
4. **Upgrades.** Upgrading a database that already had `collection` installed cuts plain
   internal users off collection data (menus, vouchers, sheets, snapshots, board events)
   until they are added to Collections User or Collections Manager. Assign the groups as
   part of the upgrade.

## Collection configuration

Open **Collections → Configuration** for the current company's full settings page:

- **General:** automatic sheet creation, document review and allowed document types.
- **Sellers:** enabled sellers, imported commission rates and **Import Sellers**.
- **Bank Accounts:** company accounts and **Manage Bank Accounts**.
- **Integration:** active connector, **Configure Connection**, **Test Connection** and
  **Manage Connectors and Mappings** for seller/customer mappings.

Use the normal **Save** and **Discard** controls. Collection Managers can configure
their company without system administration rights. Administrators also see the advanced
trusted seller header; connector credentials remain administrator-only. The header
applies to all companies. The old configuration submenu entries are inactive after
upgrade; their actions remain available for existing links.

## Trusted seller header (MCP agent)

By default every collection MCP tool acts for the `seller_id` the agent sends (for
`get_seller_id`, the `mobile`). The agent is a language model, so that value is only as
trustworthy as the conversation that produced it. The MCP API key's user must be a
Collections User; any other caller is refused.

To bind the tools to the verified WhatsApp sender instead, an administrator sets
**Collections → Configuration → Integration → Advanced → Trusted seller header**
(`ir.config_parameter` key `collection.mcp_trusted_seller_header`) to the name of an
HTTP header, for example `X-Sender-Phone`. Empty, the default, keeps the behavior above.

Contract for the gateway (Nebula) once a header name is set:

- **Source.** The gateway adds the header to every MCP HTTP request it forwards, with
  the phone of the verified WhatsApp sender taken from the channel metadata. The value
  comes from gateway code, never from model output or tool arguments, and the gateway
  drops any incoming header of the same name. Anyone holding the MCP API key can send
  any header, so the key must live only in the gateway.
- **Value.** The sender's phone in any Argentine format. It is normalized like
  `get_seller_id`: non-digits are stripped, then one leading `54`, then one leading `9`.
  `+54 9 11 5555-0199`, `5491155550199` and `1155550199` name the same seller.
- **Match.** The number must belong to exactly one internal user who is on the current
  company's Enabled Sellers list. The tools then act for that seller.
- **Arguments.** `seller_id` and `mobile` may be omitted. When the agent still sends
  one, it must name the header's seller.
- **Fail closed.** A missing or empty header, an unknown, ambiguous or not-enabled
  phone, or a `seller_id`/`mobile` naming another seller is refused with one generic
  error, `The seller identity could not be verified.`, that never tells which sellers
  exist. A disabled seller can no longer close a sheet or declare cash through the
  agent.
