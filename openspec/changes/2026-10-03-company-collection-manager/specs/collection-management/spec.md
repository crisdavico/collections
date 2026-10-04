# Collection management

Collections Managers MUST manage all collection workflows in their allowed companies
without Settings or user-administration groups. The collection addon MUST own the group,
ACLs, record rules, and configuration dialogs. MCP contracts MUST remain unchanged.

Given a manager allowed only kras, when they access another company's collections,
settings, connector credentials, bindings, or company bank accounts, access MUST be
denied. A forged allowed_company_ids context MUST NOT grant company access.

Given a kras manager importing sellers, when another company's user has the same phone,
the import MUST create or reuse a kras-local seller and MUST NOT add kras access to the
other-company user. Imported users MUST receive only internal-user permissions.

Given a manager saving settings or connector credentials, only fixed collection fields
on a checked allowed company/connector MAY be written with elevated rights. The manager
MUST NOT change company identity, user groups, or their own allowed companies.
