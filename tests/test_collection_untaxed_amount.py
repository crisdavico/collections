# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tests import TransactionCase

from .common_connector import (
    TEST_INVOICES,
    install_bound_test_connector,
    install_test_connector_type,
)
from .test_collection_payment import dummy_customer_partner, ensure_enabled_seller

ERP_CUSTOMER_IDENT = "20-11111111-1"


class TestCollectionUntaxedAmount(TransactionCase):
    """The connector's `amount_untaxed` reaches every allocation line."""

    def setUp(self):
        super().setUp()
        self.seller = ensure_enabled_seller(self.env)
        self.partner = dummy_customer_partner(self.env, customer=ERP_CUSTOMER_IDENT)
        install_test_connector_type(self)
        self.connector = install_bound_test_connector(self, self.seller)
        self.env["collection.connector.customer.binding"].create(
            {
                "connector_id": self.connector.id,
                "external_customer_id": "cust-bound-active",
                "identification": ERP_CUSTOMER_IDENT,
                "partner_id": self.partner.id,
                "customer_code": "C-BOUND-1",
            }
        )
        invoices = [dict(row) for row in TEST_INVOICES]
        invoices[0]["amount_untaxed"] = 82.64
        self.env = self.env(
            context={**self.env.context, "collection_test_invoices": invoices}
        )
        self.sheet = self.env["collection.sheet"].create({"seller_id": self.seller.id})

    def test_customer_debt_gives_amount_untaxed_or_the_amount(self):
        """A connector without an untaxed amount gives the amount itself."""
        debt = self.connector.with_env(self.env).get_customer_debt(
            self.seller.id, ERP_CUSTOMER_IDENT
        )
        by_id = {row["external_invoice_id"]: row for row in debt["invoices"]}
        self.assertEqual(by_id["inv-bound-overdue"]["amount_untaxed"], 82.64)
        self.assertEqual(by_id["inv-bound-open"]["amount_untaxed"], 50.0)

    def test_mcp_customer_debt_does_not_expose_amount_untaxed(self):
        """The agent's `customer_debt` answer keeps its invoice keys."""
        result = self.env["muk_mcp.mixin"].customer_debt(
            self.seller.id, ERP_CUSTOMER_IDENT
        )
        self.assertTrue(result["invoices"])
        for row in result["invoices"]:
            self.assertNotIn("amount_untaxed", row)

    def test_debt_lines_and_picked_debt_keep_amount_untaxed(self):
        """Lines from the customer's debt and from the picker snapshot it."""
        Allocation = self.env["collection.allocation"]
        vals = {
            row["external_invoice_id"]: row["invoice_amount_untaxed"]
            for row in Allocation._prepare_customer_debt_lines(self.sheet, self.partner)
        }
        self.assertEqual(vals, {"inv-bound-overdue": 82.64, "inv-bound-open": 50.0})

        allocation = Allocation.create(
            {"sheet_id": self.sheet.id, "partner_id": self.partner.id, "line_ids": []}
        )
        self.assertFalse(allocation.line_ids)
        action = allocation.action_open_debt_picker()
        picker = self.env["collection.allocation.debt.picker"].browse(action["res_id"])
        picker.selected_ids = picker.candidate_ids
        picker.action_add_debts()
        lines = {
            line.external_invoice_id: line.invoice_amount_untaxed
            for line in allocation.line_ids
        }
        self.assertEqual(lines, {"inv-bound-overdue": 82.64, "inv-bound-open": 50.0})
