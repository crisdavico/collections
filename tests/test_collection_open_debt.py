# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import TransactionCase

from odoo.addons.collection.models.collection_common import privileged

from .common_connector import (
    TEST_INVOICES,
    confirm_sheet,
    install_bound_test_connector,
    install_test_connector_type,
)
from .test_collection_payment import (
    create_collection_user,
    create_internal_seller,
    dummy_customer_partner,
)

_INVOICE = "inv-bound-open"
_CUSTOMER = "20-11111111-1"


class TestCollectionOpenDebt(TransactionCase):
    """A document applied on a sheet shows its real open amount.

    open = max(0, min(ERP balance now, base - applied on non-cancelled
    sheets)), base being the ERP balance when a sheet first applied it. The
    "Entered in the ERP" mark and the snapshot refresh time do not change it.
    """

    def setUp(self):
        super().setUp()
        install_test_connector_type(self)
        self.seller = create_internal_seller(self.env, "open_debt_seller")
        self.connector = install_bound_test_connector(self, self.seller)
        self.mixin = self.env["muk_mcp.mixin"]
        self.currency = self.env.company.currency_id

    def _sheet(self, applied, base, state="open"):
        """A sheet applying ``applied`` to the open invoice seen at ``base``."""
        tag = f"{state}-{applied}-{base}"
        partner = dummy_customer_partner(self.env, customer=f"OPEN-DEBT-{tag}")
        sheet = self.env["collection.sheet"].create({"seller_id": self.seller.id})
        allocation = self.env["collection.allocation"].create(
            {
                "sheet_id": sheet.id,
                "partner_id": partner.id,
                "line_ids": [
                    Command.create(
                        {
                            "external_invoice_id": _INVOICE,
                            "invoice_number": "A-0002",
                            "invoice_amount": base,
                            "invoice_balance": base,
                            "invoice_state": "open",
                            "amount_applied": applied,
                        }
                    )
                ],
            }
        )
        voucher = self.env["collection.voucher"].create(
            {
                "document_type": "bank_transfer",
                "partner_id": partner.id,
                "seller_id": self.seller.id,
                "sheet_id": sheet.id,
                "allocation_id": allocation.id,
                "company_id": sheet.company_id.id,
                "amount": applied,
                "document_id": f"open-debt-{tag}-{sheet.id}",
            }
        )
        with privileged("collection_audited_state"):
            voucher.write({"state": "validated_collections"})
        if state == "open":
            return sheet
        confirm_sheet(sheet)
        sheet.action_close()
        if state == "cancelled":
            sheet.action_cancel()
        return sheet

    def _invoices(self, balance):
        """The connector's invoices with the open invoice at ``balance``."""
        return tuple(
            dict(row, balance=balance) if row["id"] == _INVOICE else row
            for row in TEST_INVOICES
        )

    def _debt(self, balance):
        return self.mixin.with_context(
            collection_test_invoices=self._invoices(balance)
        ).customer_debt(self.seller.id, _CUSTOMER)

    def _row(self, payload):
        by_id = {row["external_invoice_id"]: row for row in payload["invoices"]}
        return by_id[_INVOICE]

    def _revalidate(self, applied, balance, destination=None):
        context = {"collection_test_invoices": self._invoices(balance)}
        rows = [
            {
                "external_invoice_id": _INVOICE,
                "amount_applied": applied,
                "document_kind": "invoice",
            }
        ]
        return self.mixin.with_context(**context)._collection_allocation_revalidate(
            self.connector.with_context(**context),
            self.seller,
            _CUSTOMER,
            rows,
            destination or self.env["collection.allocation"],
            self.currency,
        )

    def test_closed_sheet_not_yet_in_the_erp_stays_subtracted(self):
        """Close marks the sheet; the debt does not come back while unchanged."""
        sheet = self._sheet(40.0, 50.0, state="closed")
        self.assertTrue(sheet.erp_entered_date)
        row = self._row(self._debt(50.0))
        self.assertEqual(row["balance"], 50.0)
        self.assertEqual(row["allocatable_balance"], 10.0)
        self.assertEqual(row["in_collection"], 40.0)

    def test_receipt_already_in_the_erp_is_not_subtracted_twice(self):
        """Typed in, the ERP shows base - applied: that is the open amount."""
        for state in ("closed", "open"):
            with self.subTest(state=state):
                sheet = self._sheet(40.0, 50.0, state=state)
                row = self._row(self._debt(10.0))
                self.assertEqual(row["allocatable_balance"], 10.0)
                self.assertEqual(row["in_collection"], 0.0)
                if state == "closed":
                    sheet.action_cancel()

    def test_several_sheets_on_one_document(self):
        """Closed sheet 30 and open sheet 20 on a document seen at 100."""
        self._sheet(30.0, 100.0, state="closed")
        self._sheet(20.0, 100.0)
        for balance in (100.0, 70.0, 50.0):
            with self.subTest(balance=balance):
                row = self._row(self._debt(balance))
                self.assertEqual(row["allocatable_balance"], 50.0)
                self.assertEqual(row["in_collection"], balance - 50.0)

    def test_cancelled_sheet_counts_nothing(self):
        self._sheet(40.0, 50.0, state="cancelled")
        row = self._row(self._debt(50.0))
        self.assertEqual(row["allocatable_balance"], 50.0)
        self.assertEqual(row["in_collection"], 0.0)

    def test_payment_typed_outside_the_sheets_is_the_known_limit(self):
        """100 owed, 30 on a sheet not typed yet, 20 typed outside: 70, not 50."""
        self._sheet(30.0, 100.0, state="closed")
        row = self._row(self._debt(80.0))
        self.assertEqual(row["allocatable_balance"], 70.0)
        self.assertEqual(row["in_collection"], 10.0)

    def test_summary_says_what_is_in_collection_and_still_pending(self):
        self._sheet(40.0, 50.0, state="closed")
        summary = self._debt(50.0)["summary"]
        self.assertEqual(summary["total_balance"], 150.0)
        self.assertEqual(summary["net_total"], 150.0)
        self.assertEqual(summary["in_collection_total"], 40.0)
        self.assertEqual(summary["pending_total"], 110.0)
        self.assertEqual(summary["total_allocatable_balance"], 110.0)

    def test_summary_without_sheets_has_nothing_in_collection(self):
        summary = self._debt(50.0)["summary"]
        self.assertEqual(summary["in_collection_total"], 0.0)
        self.assertEqual(summary["pending_total"], summary["net_total"])

    def test_tool_description_names_the_pending_total(self):
        by_name = {
            entry["name"]: entry
            for entry in self.env["muk_mcp.tool"].get_tools(registry="mcp")
        }
        description = by_name["customer_debt"]["description"]
        self.assertIn("pending_total", description)
        self.assertIn("in_collection", description)

    def test_write_is_capped_at_the_open_amount_of_a_marked_sheet(self):
        sheet = self._sheet(40.0, 50.0, state="closed")
        self.assertTrue(sheet.erp_entered_date)
        with self.assertRaisesRegex(UserError, "exceeds available invoice balance"):
            self._revalidate(11.0, 50.0)
        line_vals = self._revalidate(10.0, 50.0)
        by_id = {vals["external_invoice_id"]: vals for vals in line_vals}
        self.assertEqual(by_id[_INVOICE]["amount_applied"], 10.0)

    def test_write_accepts_the_open_amount_once_the_erp_shows_the_receipt(self):
        self._sheet(40.0, 50.0, state="closed")
        line_vals = self._revalidate(10.0, 10.0)
        by_id = {vals["external_invoice_id"]: vals for vals in line_vals}
        self.assertEqual(by_id[_INVOICE]["amount_applied"], 10.0)

    def test_amendment_keeps_the_base_of_an_applied_document(self):
        sheet = self._sheet(40.0, 50.0)
        allocation = sheet.allocation_ids
        # The ERP balance moved to 45: the amendment must keep base 50.
        line_vals = self._revalidate(40.0, 45.0, destination=allocation)
        by_id = {vals["external_invoice_id"]: vals for vals in line_vals}
        self.assertEqual(by_id[_INVOICE]["erp_balance_base"], 50.0)
        self.assertEqual(by_id[_INVOICE]["invoice_balance"], 45.0)
        # A document the allocation did not apply takes the ERP balance now.
        self.assertEqual(by_id["inv-bound-overdue"]["erp_balance_base"], 100.0)

    def test_new_line_base_is_its_balance_unless_given(self):
        sheet = self._sheet(5.0, 50.0)
        line = sheet.allocation_ids.line_ids
        self.assertEqual(line.erp_balance_base, 50.0)
        line.invoice_balance = 30.0
        self.assertEqual(line.erp_balance_base, 50.0)
        given = self.env["collection.allocation.line"].create(
            {
                "allocation_id": sheet.allocation_ids.id,
                "external_invoice_id": "inv-given-base",
                "invoice_balance": 20.0,
                "erp_balance_base": 80.0,
            }
        )
        self.assertEqual(given.erp_balance_base, 80.0)

    def test_planilla_balance_is_what_earlier_sheets_left_open(self):
        """The Saldo column: the ERP balance net of earlier sheets only."""
        closed = self._sheet(30.0, 100.0, state="closed")
        current = self._sheet(20.0, 100.0)
        rows = [
            row
            for block in current._collection_report_document_blocks({})
            for row in block["rows"]
            if row["invoice_number"] == "A-0002"
        ]
        self.assertEqual([row["invoice_balance"] for row in rows], [70.0])
        self.assertEqual([row["amount_applied"] for row in rows], [20.0])
        earlier = [
            row
            for block in closed._collection_report_document_blocks({})
            for row in block["rows"]
            if row["invoice_number"] == "A-0002"
        ]
        self.assertEqual([row["invoice_balance"] for row in earlier], [100.0])

    def test_the_mark_never_changes_the_open_amount(self):
        manager = create_collection_user(self.env, "open_debt_mgr", manager=True)
        sheet = self._sheet(40.0, 50.0, state="closed")
        for action in ("action_unmark_erp_entered", "action_mark_erp_entered"):
            with self.subTest(action=action):
                getattr(sheet.with_user(manager), action)()
                row = self._row(self._debt(50.0))
                self.assertEqual(row["allocatable_balance"], 10.0)
