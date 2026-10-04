# Company-scoped collection management

Create kras and one user restricted to kras in the development database. Add a reusable
Collections Manager group entirely within collection, including scoped configuration,
seller import, connector credentials and snapshot refresh, and company bank accounts.
Existing collection company rules and MCP contracts remain in place. No system or user
administration rights are granted. Fixed-field configuration dialogs may elevate only
after validating manager membership and allowed company access; imports match only
company-local users and never expand another user's company access.

Rollback: remove the manager group from the user; keep all collection records and
existing internal-user access. Business-company/user creation is explicit setup rather
than installation data. Changes exceed 400 lines because they include configuration
dialogs, permission-boundary regression tests, and documentation.
