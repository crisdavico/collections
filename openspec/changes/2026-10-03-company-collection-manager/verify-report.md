# Verification

- Upgraded collection to 19.0.1.50.0 in local development DB `devel` on `seedian-odoo-1`
  and restarted the application.
- All 1,064 collection tests passed (zero failures/errors), including ten new
  Collections Manager permission and company-isolation tests.
- Scoped pre-commit passed for all changed source, XML, security, tests, and docs.
- Existing ACL assertions now include the explicitly requested manager group while
  preserving ordinary internal-user limits. The MCP commission rejection test now checks
  against its initial count so existing development data does not cause a false failure;
  MCP behavior is unchanged.
- Created company `kras` (ID 7637) and `kras.collections` (user ID 49381). Allowed
  companies and default company are exactly kras. The user has Collections Manager and
  internal-user access, with no Settings or user-administration group.
- Enabled the user as a kras seller and enabled Document Review. All nine document types
  and three independent company sequences are present. No other company's external
  connector or credentials were copied; kras can configure its own source.
- HTTP session authentication confirmed only kras is offered. RPC checks read all 15
  installed collection models with company filtering, saved collection settings, loaded
  company settings/connector/sheet form views, and rejected a forged
  `allowed_company_ids` selecting Seedian.
- Generated credentials were kept outside the repository in a mode-0600 temporary file
  and provided to the requesting user.
