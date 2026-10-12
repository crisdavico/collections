# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.orm.model_classes import add_to_registry

from odoo.addons.collection.models.collection_common import privileged

TEST_CONNECTOR_TYPE = "test"
TEST_STALE_MESSAGE = "The customer debt is out of date."

TEST_SELLERS = (
    {
        "id": "ext-bound",
        "name": "Bound Seller",
        "mobile": "5491111111111",
        "active": 1,
        "commission_percent": 5.0,
    },
    {
        "id": "ext-unbound",
        "name": "Unbound Seller",
        "mobile": "5491122222222",
        "active": 1,
        "commission_percent": 7.5,
    },
    {
        "id": "ext-inactive",
        "name": "Inactive Seller",
        "mobile": "5491133333333",
        "active": 0,
        "commission_percent": 10.0,
    },
)

TEST_CUSTOMERS = (
    {
        "id": "cust-bound-active",
        "seller_id": "ext-bound",
        "name": "Bound Active Customer",
        "identification": "20-11111111-1",
        "customer_code": "C-BOUND-1",
        "active": 1,
    },
    {
        "id": "cust-bound-inactive",
        "seller_id": "ext-bound",
        "name": "Bound Inactive Customer",
        "identification": "20-22222222-2",
        "customer_code": "C-BOUND-0",
        "active": 0,
    },
    {
        "id": "cust-unbound-active",
        "seller_id": "ext-unbound",
        "name": "Unbound Active Customer",
        "identification": "20-33333333-3",
        "customer_code": "C-UNBOUND-1",
        "active": 1,
    },
)

TEST_INVOICES = (
    {
        "id": "inv-bound-overdue",
        "customer_id": "cust-bound-active",
        "number": "A-0001",
        "issue_date": "2026-01-10",
        "due_date": "2026-03-10",
        "amount": 100.0,
        "balance": 100.0,
        "state": "overdue",
    },
    {
        "id": "inv-bound-open",
        "customer_id": "cust-bound-active",
        "number": "A-0002",
        "issue_date": "2026-04-01",
        "due_date": "2026-09-01",
        "amount": 50.0,
        "balance": 50.0,
        "state": "open",
    },
    {
        "id": "inv-bound-paid",
        "customer_id": "cust-bound-active",
        "number": "A-0003",
        "issue_date": "2026-02-01",
        "due_date": "2026-03-01",
        "amount": 20.0,
        "balance": 0.0,
        "state": "paid",
    },
    {
        "id": "inv-bound-zero-open",
        "customer_id": "cust-bound-active",
        "number": "A-0004",
        "issue_date": "2026-05-01",
        "due_date": "2026-10-01",
        "amount": 30.0,
        "balance": 0.0,
        "state": "open",
    },
    {
        "id": "inv-bound-inactive-debt",
        "customer_id": "cust-bound-inactive",
        "number": "A-0005",
        "issue_date": "2026-01-01",
        "due_date": "2026-02-01",
        "amount": 80.0,
        "balance": 80.0,
        "state": "overdue",
    },
    {
        "id": "inv-unbound-open",
        "customer_id": "cust-unbound-active",
        "number": "A-0006",
        "issue_date": "2026-06-01",
        "due_date": "2026-08-01",
        "amount": 40.0,
        "balance": 40.0,
        "state": "open",
    },
)


class CollectionConnectorTestProvider(models.Model):
    """Test-only provider; not shipped as a production Selection value."""

    _module = None
    _name = "collection.connector"
    _inherit = ["collection.connector"]

    type = fields.Selection(
        selection_add=[(TEST_CONNECTOR_TYPE, "Test")],
        ondelete={TEST_CONNECTOR_TYPE: "cascade"},
    )

    @api.private
    def _test_list_sellers(self):
        self.ensure_one()
        rows = self.env.context.get("collection_test_sellers")
        if rows is None:
            rows = TEST_SELLERS
        return [dict(row) for row in rows]

    @api.private
    def _test_list_customers(self, external_seller_id):
        self.ensure_one()
        rows = self.env.context.get("collection_test_customers")
        if rows is None:
            rows = TEST_CUSTOMERS
        needle = str(external_seller_id or "")
        return [dict(row) for row in rows if str(row.get("seller_id") or "") == needle]

    @api.private
    def _test_get_customer_debt(self, external_seller_id, customer_identification):
        self.ensure_one()
        if self.env.context.get("collection_test_stale"):
            # Imported here so an older core still loads the rest of the fixtures.
            from odoo.addons.collection.models.collection_common import (
                ConnectorDataStaleError,
            )

            raise ConnectorDataStaleError(TEST_STALE_MESSAGE)
        customers = self.env.context.get("collection_test_customers")
        if customers is None:
            customers = TEST_CUSTOMERS
        invoices = self.env.context.get("collection_test_invoices")
        if invoices is None:
            invoices = TEST_INVOICES
        seller_needle = str(external_seller_id or "")
        ident_needle = str(customer_identification or "").strip()
        matches = [
            dict(row)
            for row in customers
            if str(row.get("seller_id") or "") == seller_needle
            and str(row.get("identification") or "").strip() == ident_needle
        ]
        if len(matches) != 1:
            return {"customer": None, "invoices": []}
        customer = matches[0]
        customer_id = str(customer.get("id") or "")
        payload = {
            "customer": customer,
            "invoices": [
                dict(row)
                for row in invoices
                if str(row.get("customer_id") or "") == customer_id
            ],
        }
        as_of = self.env.context.get("collection_test_as_of")
        if as_of:
            payload["as_of"] = as_of
        credit_total = self.env.context.get("collection_test_credit_total")
        if credit_total is not None:
            payload["credit_total"] = credit_total
        return payload

    @api.private
    def _collection_erp_reflected_since(self):
        """Test type: the time a test says its data took ERP entries in."""
        if self.type == TEST_CONNECTOR_TYPE:
            return self.env.context.get("collection_test_reflected_since") or False
        return super()._collection_erp_reflected_since()

    @api.private
    def _test_test_connection(self):
        self.ensure_one()
        return {"ok": True}

    @api.private
    def _test_create_receipt(self, receipt):
        self.ensure_one()
        return {"external_receipt_id": f"stub-{receipt.id}"}


def install_test_connector_type(case):
    """Register the test provider on this case's registry (idempotent)."""
    field = case.env["collection.connector"]._fields["type"]
    selection = field._description_selection(case.env) or []
    if any(value == TEST_CONNECTOR_TYPE for value, _label in selection):
        return
    add_to_registry(case.registry, CollectionConnectorTestProvider)
    case.registry._setup_models__(case.env.cr, ["collection.connector"])
    case.addClassCleanup(case.registry.reset_changes)
    case.addClassCleanup(case.registry.clear_all_caches)


def install_bound_test_connector(case, seller):
    """Smallest connector fixture so all-new MCP resolve can succeed."""
    from .test_collection_payment import ensure_enabled_seller

    install_test_connector_type(case)
    connector = case.env["collection.connector"].create(
        {
            "name": "MCP Test Connector",
            "type": TEST_CONNECTOR_TYPE,
        }
    )
    case.env.company.write({"collection_connector_id": connector.id})
    ensure_enabled_seller(case.env, seller)
    Binding = case.env["collection.connector.seller.binding"]
    if not Binding.search(
        [("connector_id", "=", connector.id), ("user_id", "=", seller.id)],
        limit=1,
    ):
        Binding.create(
            {
                "connector_id": connector.id,
                "external_seller_id": "ext-bound",
                "user_id": seller.id,
            }
        )
    return connector


def mcp_env_with_listable_customers(env, arguments, user, default_user):
    """Env for MCP create: echo payment idents as listable test customers."""
    known = {str(row.get("identification") or "").strip() for row in TEST_CUSTOMERS}
    extra = []
    seen = set()
    for payment in arguments.get("payments") or []:
        if not isinstance(payment, dict):
            continue
        ident = str(payment.get("customer_identification") or "").strip()
        if not ident or ident in known or ident in seen:
            continue
        seen.add(ident)
        extra.append(
            {
                "id": f"echo-{ident}",
                "seller_id": "ext-bound",
                "name": ident,
                "identification": ident,
                "customer_code": ident,
                "active": 1,
            }
        )
    customers = [dict(row) for row in TEST_CUSTOMERS] + extra
    uid = user if user else default_user
    ctx = dict(env.context)
    ctx["collection_test_customers"] = customers
    return env(user=uid, context=ctx)


def force_sheet_state(sheet, state):
    """Write sheet ``state`` inside the audited privileged scope."""
    with privileged("collection_sheet_audited_state"):
        sheet.write({"state": state})
    return sheet


def confirm_sheet(sheet):
    """Confirm from submitted. Seller Close first when the sheet is still open."""
    opens = sheet.filtered(lambda rec: rec.state == "open")
    if opens:
        opens.action_seller_close()
    return sheet.action_confirm()


def advance_sheet_to(sheet, target):
    """Drive an open sheet through legal Seller Close/Confirm/Close/Cancel.

    Marks members ``validated_collections`` so Seller Close and Confirm can run.
    Use :func:`force_sheet_state` when a test must skip those gates.
    """
    if target == "open":
        return sheet
    vouchers = sheet.voucher_ids
    if vouchers:
        with privileged("collection_audited_state"):
            vouchers.write({"state": "validated_collections"})
    if sheet.state == "open":
        sheet.action_seller_close()
    if target == "submitted":
        return sheet
    sheet.action_confirm()
    if target == "proposal":
        return sheet
    if target == "closed":
        sheet.action_close()
        return sheet
    if target == "cancelled":
        sheet.action_cancel()
        return sheet
    raise AssertionError(f"Unsupported sheet target {target!r}")
