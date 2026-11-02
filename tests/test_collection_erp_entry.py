# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo.exceptions import AccessError, UserError
from odoo.fields import Command
from odoo.tests import TransactionCase

from odoo.addons.collection.models.collection_common import privileged

from .common_connector import (
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
_APPLIED = 40.0


class TestCollectionErpEntry(TransactionCase):
    """The "Entered in the ERP" mark: back-office tracking only.

    Closing a sheet marks it; a manager may unmark it and mark it again. The
    real open amount of a document does not depend on it
    (test_collection_open_debt).
    """

    def setUp(self):
        super().setUp()
        install_test_connector_type(self)
        self.seller = create_internal_seller(self.env, "erp_entry_seller")
        self.connector = install_bound_test_connector(self, self.seller)
        self.manager = create_collection_user(self.env, "erp_entry_mgr", manager=True)
        self.operator = create_collection_user(self.env, "erp_entry_operator")
        self.plain = create_internal_seller(self.env, "erp_entry_plain")

    def _sheet(self, state="open"):
        """A sheet applying 40 to the open invoice, driven to ``state``."""
        partner = dummy_customer_partner(self.env, customer=f"ERP-ENTRY-{state}")
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
                            # An older, larger snapshot: several sheets in
                            # one test stay under the per-document cap (T18).
                            "invoice_amount": 1000.0,
                            "invoice_balance": 1000.0,
                            "invoice_state": "open",
                            "amount_applied": _APPLIED,
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
                "amount": _APPLIED,
                "document_id": f"erp-entry-{state}-{sheet.id}",
            }
        )
        with privileged("collection_audited_state"):
            voucher.write({"state": "validated_collections"})
        if state == "open":
            return sheet
        if state == "submitted":
            sheet.action_seller_close()
            return sheet
        confirm_sheet(sheet)
        if state == "proposal":
            return sheet
        sheet.action_close()
        if state == "cancelled":
            sheet.action_cancel()
        return sheet

    def _mark(self, sheet):
        """Mark a closed sheet again by hand; Close already marked it."""
        sheet.with_user(self.manager).action_unmark_erp_entered()
        sheet.with_user(self.manager).action_mark_erp_entered()
        return sheet.erp_entered_date

    def test_close_marks_the_sheet_as_entered_in_the_erp(self):
        sheet = self._sheet("proposal")
        self.assertFalse(sheet.erp_entered_date)
        before = len(sheet.message_ids)
        sheet.with_user(self.operator).action_close()
        self.assertEqual(sheet.state, "closed")
        self.assertTrue(sheet.erp_entered_date)
        self.assertEqual(sheet.erp_entered_uid, self.operator)
        self.assertEqual(len(sheet.message_ids), before + 1)
        self.assertIn("entered in the ERP", sheet.message_ids[0].body)

    def test_only_managers_mark_and_unmark(self):
        sheet = self._sheet("closed")
        for user in (self.plain, self.operator):
            with self.subTest(user=user.login, action="unmark"):
                with self.assertRaises(AccessError):
                    sheet.with_user(user).action_unmark_erp_entered()
        self.assertTrue(sheet.erp_entered_date)
        sheet.with_user(self.manager).action_unmark_erp_entered()
        for user in (self.plain, self.operator):
            with self.subTest(user=user.login):
                with self.assertRaises(AccessError):
                    sheet.with_user(user).action_mark_erp_entered()
        self.assertFalse(sheet.erp_entered_date)

    def test_only_closed_sheets_can_be_marked_once(self):
        sheet = self._sheet("closed")
        with self.assertRaises(UserError):
            sheet.with_user(self.manager).action_mark_erp_entered()
        self._mark(sheet)
        with self.assertRaises(UserError):
            sheet.with_user(self.manager).action_mark_erp_entered()
        unmarked = self._sheet("closed")
        unmarked.with_user(self.manager).action_unmark_erp_entered()
        with self.assertRaises(UserError):
            unmarked.with_user(self.manager).action_unmark_erp_entered()
        # One open sheet per seller: the open one comes last.
        for state in ("proposal", "cancelled", "open"):
            with self.subTest(state=state):
                other = self._sheet(state)
                with self.assertRaises(UserError):
                    other.with_user(self.manager).action_mark_erp_entered()
                self.assertFalse(other.erp_entered_date)

    def test_the_mark_cannot_be_written_directly(self):
        sheet = self._sheet("closed")
        sheet.with_user(self.manager).action_unmark_erp_entered()
        for user in (self.manager, self.env.user):
            for vals in (
                {"erp_entered_date": "2026-10-01 10:00:00"},
                {"erp_entered_uid": user.id},
            ):
                with self.subTest(user=user.login, vals=vals):
                    with self.assertRaises(UserError):
                        sheet.with_user(user).write(vals)
        self.assertFalse(sheet.erp_entered_date)

    def test_cancel_clears_the_mark_and_reinstate_keeps_it_cleared(self):
        sheet = self._sheet("closed")
        self.assertTrue(sheet.erp_entered_date)
        sheet.with_user(self.manager).action_cancel()
        self.assertFalse(sheet.erp_entered_date)
        self.assertFalse(sheet.erp_entered_uid)
        sheet.with_user(self.manager).action_reinstate()
        self.assertFalse(sheet.erp_entered_date)

    def test_operators_cancel_or_reset_a_marked_sheet(self):
        """Every closed sheet is marked, so Cancel and Reset stay with operators."""
        for name, call in (
            ("action_cancel", lambda sheet: sheet.action_cancel()),
            ("action_reset_to_open", lambda sheet: sheet.action_reset_to_open()),
            ("write cancelled", lambda sheet: sheet.write({"state": "cancelled"})),
            ("write open", lambda sheet: sheet.write({"state": "open"})),
        ):
            with self.subTest(call=name):
                sheet = self._sheet("closed")
                self.assertTrue(sheet.erp_entered_date)
                call(sheet.with_user(self.operator))
                self.assertIn(sheet.state, ("cancelled", "open"))
                self.assertFalse(sheet.erp_entered_date)
                self.assertFalse(sheet.erp_entered_uid)
                if sheet.state == "cancelled":
                    sheet.action_reset_to_open()
                sheet.unlink()

    def test_operators_see_cancel_and_reset_on_marked_sheets(self):
        raw = etree.fromstring(
            self.env.ref("collection.view_collection_sheet_form").arch
        )
        operator_form = etree.fromstring(
            self.env["collection.sheet"]
            .with_user(self.operator)
            .get_view(view_type="form")["arch"]
        )
        for name in ("action_cancel", "action_reset_to_open"):
            with self.subTest(button=name):
                buttons = operator_form.xpath(f"//button[@name='{name}']")
                self.assertEqual(len(buttons), 1)
                self.assertNotIn("erp_entered_date", buttons[0].get("invisible"))
                declared = raw.xpath(f"//button[@name='{name}']")
                self.assertEqual(
                    [node.get("groups") for node in declared],
                    ["collection.group_collection_user"],
                )

    def test_mark_and_unmark_leave_a_chatter_note(self):
        sheet = self._sheet("closed")
        before = len(sheet.message_ids)
        sheet.with_user(self.manager).action_unmark_erp_entered()
        sheet.with_user(self.manager).action_mark_erp_entered()
        self.assertEqual(len(sheet.message_ids), before + 2)

    def test_views_offer_the_mark_and_a_pending_filter(self):
        Sheet = self.env["collection.sheet"]
        raw = etree.fromstring(
            self.env.ref("collection.view_collection_sheet_form").arch
        )
        form = etree.fromstring(Sheet.get_view(view_type="form")["arch"])
        operator_form = etree.fromstring(
            Sheet.with_user(self.operator).get_view(view_type="form")["arch"]
        )
        for name in ("action_mark_erp_entered", "action_unmark_erp_entered"):
            buttons = raw.xpath(f"//button[@name='{name}']")
            self.assertTrue(buttons, name)
            self.assertIn(
                "collection.group_collection_manager", buttons[0].get("groups")
            )
            self.assertFalse(operator_form.xpath(f"//button[@name='{name}']"), name)
        self.assertTrue(form.xpath("//field[@name='erp_entered_date']"))
        self.assertTrue(form.xpath("//field[@name='erp_entered_uid']"))
        search = etree.fromstring(Sheet.get_view(view_type="search")["arch"])
        pending = search.xpath("//filter[@name='pending_erp_entry']")
        self.assertTrue(pending)
        self.assertIn("erp_entered_date", pending[0].get("domain"))
        closed = self._sheet("closed")
        closed.with_user(self.manager).action_unmark_erp_entered()
        marked = self._sheet("closed")
        domain = [("state", "=", "closed"), ("erp_entered_date", "=", False)]
        found = Sheet.search(domain)
        self.assertIn(closed, found)
        self.assertNotIn(marked, found)
