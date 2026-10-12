# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.fields import Command
from odoo.tests import TransactionCase

from .common_connector import install_bound_test_connector, install_test_connector_type
from .test_collection_payment import create_internal_seller, dummy_customer_partner

_IDENT = "20-11111111-1"


class TestCollectionCreditNotes(TransactionCase):
    """Decision D4: open credit notes net the customer total, not the invoices."""

    def setUp(self):
        super().setUp()
        install_test_connector_type(self)
        self.seller = create_internal_seller(self.env, "credit_notes_seller")
        self.connector = install_bound_test_connector(self, self.seller)

    def _debt(self, credit_total=None):
        connector = self.connector
        if credit_total is not None:
            connector = connector.with_context(
                collection_test_credit_total=credit_total
            )
        return connector.get_customer_debt(self.seller.id, _IDENT)

    def test_credit_notes_net_the_customer_total(self):
        """150 open invoices and a 50 credit note: the customer owes 100."""
        summary = self._debt(credit_total=50.0)["summary"]
        self.assertEqual(summary["gross_total"], 150.0)
        self.assertEqual(summary["credit_total"], 50.0)
        self.assertEqual(summary["net_total"], 100.0)
        self.assertEqual(summary["total_balance"], 100.0)

    def test_invoice_figures_are_untouched_by_credits(self):
        """Allocation still targets invoices: their balances stay gross."""
        debt = self._debt(credit_total=50.0)
        self.assertEqual(
            {row["external_invoice_id"]: row["balance"] for row in debt["invoices"]},
            {"inv-bound-overdue": 100.0, "inv-bound-open": 50.0},
        )
        self.assertEqual(debt["summary"]["open_balance"], 50.0)
        self.assertEqual(debt["summary"]["overdue_balance"], 100.0)
        self.assertEqual(debt["summary"]["invoice_count"], 2)

    def test_without_credits_net_equals_gross(self):
        summary = self._debt()["summary"]
        self.assertEqual(summary["credit_total"], 0.0)
        self.assertEqual(summary["gross_total"], 150.0)
        self.assertEqual(summary["net_total"], 150.0)
        self.assertEqual(summary["total_balance"], 150.0)

    def test_credit_is_reported_as_a_positive_amount(self):
        """Adapters may sign the credit either way; it is always subtracted."""
        summary = self._debt(credit_total=-30.0)["summary"]
        self.assertEqual(summary["credit_total"], 30.0)
        self.assertEqual(summary["net_total"], 120.0)

    def test_credits_above_the_invoices_leave_a_balance_in_favour(self):
        summary = self._debt(credit_total=200.0)["summary"]
        self.assertEqual(summary["net_total"], -50.0)
        self.assertEqual(summary["total_balance"], -50.0)

    def test_mcp_payload_carries_gross_credit_and_net(self):
        mixin = self.env["muk_mcp.mixin"].with_context(
            collection_test_credit_total=50.0
        )
        summary = mixin.customer_debt(self.seller.id, _IDENT)["summary"]
        self.assertEqual(
            (summary["gross_total"], summary["credit_total"], summary["net_total"]),
            (150.0, 50.0, 100.0),
        )
        self.assertEqual(summary["total_allocatable_balance"], 150.0)

    def test_picker_shows_gross_credit_and_net(self):
        partner = dummy_customer_partner(self.env, customer=_IDENT)
        self.env["collection.connector.customer.binding"].create(
            {
                "connector_id": self.connector.id,
                "external_customer_id": "cust-bound-active",
                "identification": _IDENT,
                "partner_id": partner.id,
            }
        )
        sheet = self.env["collection.sheet"].create({"seller_id": self.seller.id})
        allocation = self.env["collection.allocation"].create(
            {
                "sheet_id": sheet.id,
                "partner_id": partner.id,
                "line_ids": [
                    Command.create(
                        {
                            "external_invoice_id": "inv-bound-overdue",
                            "invoice_balance": 100.0,
                            "invoice_amount": 100.0,
                        }
                    )
                ],
            }
        )
        action = allocation.with_context(
            collection_test_credit_total=50.0
        ).action_open_debt_picker()
        picker = self.env["collection.allocation.debt.picker"].browse(action["res_id"])
        self.assertEqual(picker.debt_gross_total, 150.0)
        self.assertEqual(picker.debt_credit_total, 50.0)
        self.assertEqual(picker.debt_net_total, 100.0)
