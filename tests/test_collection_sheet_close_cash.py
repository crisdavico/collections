# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests import TransactionCase

from .test_collection_mcp_cash_declare import TestCollectionMcpCashDeclare
from .test_collection_payment import create_internal_seller, ensure_enabled_seller


class TestCollectionSheetCloseCash(TransactionCase):
    """Seller Close declares the cash: a sheet with cash cannot close without it."""

    def setUp(self):
        super().setUp()
        self.seller = create_internal_seller(self.env, "collection_close_cash_ana")
        ensure_enabled_seller(self.env, self.seller)

    def _create_sheet(self, *, seller=None, cash=0.0):
        return TestCollectionMcpCashDeclare._create_sheet(
            self, seller=seller, cash=cash
        )

    def _add_commission(self, sheet, applied=100.0, percent=10.0):
        return TestCollectionMcpCashDeclare._add_commission(
            self, sheet, applied=applied, percent=percent
        )

    def _assert_still_open(self, sheet):
        self.assertEqual(sheet.state, "open")
        self.assertFalse(sheet.cash_declared_at)
        self.assertFalse(sheet.commission_withheld)

    def test_close_with_cash_and_no_declaration_is_refused(self):
        """A sheet with collected cash MUST NOT close before the cash is declared."""
        sheet = self._create_sheet(cash=40.0)
        with self.assertRaises(UserError) as ctx:
            sheet.action_seller_close()
        self.assertIn("commission_withheld", str(ctx.exception))
        self._assert_still_open(sheet)

    def test_state_write_with_cash_and_no_declaration_is_refused(self):
        """Writing state submitted goes through Seller Close and obeys the rule."""
        sheet = self._create_sheet(cash=40.0)
        with self.assertRaises(UserError):
            sheet.write({"state": "submitted"})
        self._assert_still_open(sheet)

    def test_close_declares_the_cash_in_the_same_step(self):
        """Seller Close with commission_withheld MUST submit and declare at once."""
        sheet = self._create_sheet(cash=40.0)
        self._add_commission(sheet, applied=50.0, percent=10.0)
        sheet.action_seller_close(commission_withheld=2.25)
        self.assertEqual(sheet.state, "submitted")
        self.assertEqual(sheet.commission_withheld, 2.25)
        self.assertEqual(sheet.commission_owed, 2.75)
        self.assertEqual(sheet.cash_on_hand, 37.75)
        self.assertTrue(sheet.cash_declared_at)
        self.assertEqual(sheet.cash_declared_by, self.env.user)

    def test_close_declares_zero_kept(self):
        """Keeping nothing is a declaration: zero closes and stamps the sheet."""
        sheet = self._create_sheet(cash=40.0)
        self._add_commission(sheet, applied=50.0, percent=10.0)
        sheet.action_seller_close(commission_withheld=0.0)
        self.assertEqual(sheet.state, "submitted")
        self.assertEqual(sheet.commission_withheld, 0.0)
        self.assertEqual(sheet.cash_on_hand, 40.0)
        self.assertTrue(sheet.cash_declared_at)

    def test_close_keeping_more_than_the_commission_is_refused(self):
        """The cash kept MUST NOT exceed the commission the sheet computes."""
        sheet = self._create_sheet(cash=100.0)
        self._add_commission(sheet, applied=50.0, percent=10.0)
        with self.assertRaises(UserError) as ctx:
            sheet.action_seller_close(commission_withheld=5.01)
        self.assertIn("seller commission", str(ctx.exception))
        self._assert_still_open(sheet)

    def test_close_keeping_more_than_the_cash_is_refused(self):
        """The cash kept MUST NOT exceed the cash collected minus deposits."""
        sheet = self._create_sheet(cash=3.0)
        self._add_commission(sheet, applied=100.0, percent=10.0)
        with self.assertRaises(UserError) as ctx:
            sheet.action_seller_close(commission_withheld=4.0)
        self.assertIn("cash collected", str(ctx.exception))
        self._assert_still_open(sheet)

    def test_close_keeping_a_negative_amount_is_refused(self):
        """A negative amount kept MUST refuse the close."""
        sheet = self._create_sheet(cash=40.0)
        self._add_commission(sheet, applied=50.0, percent=10.0)
        with self.assertRaises(UserError):
            sheet.action_seller_close(commission_withheld=-1.0)
        self._assert_still_open(sheet)

    def test_close_without_cash_needs_no_declaration(self):
        """With no cash collected, Seller Close MUST NOT ask for a declaration."""
        sheet = self._create_sheet()
        sheet.action_seller_close()
        self.assertEqual(sheet.state, "submitted")
        self.assertFalse(sheet.cash_declared_at)

    def test_submitted_sheet_can_still_correct_the_declaration(self):
        """Declare Cash on a submitted sheet MUST still correct the amount kept."""
        sheet = self._create_sheet(cash=40.0)
        self._add_commission(sheet, applied=50.0, percent=10.0)
        sheet.action_seller_close(commission_withheld=2.25)
        sheet.action_declare_cash(commission_withheld=5.0)
        self.assertEqual(sheet.commission_withheld, 5.0)
        self.assertEqual(sheet.cash_on_hand, 35.0)

    def test_form_button_without_cash_closes_at_once(self):
        """The Seller Close button MUST close a sheet without cash directly."""
        sheet = self._create_sheet()
        action = sheet.action_open_seller_close()
        self.assertNotIsInstance(action, dict)
        self.assertEqual(sheet.state, "submitted")

    def test_form_button_with_cash_asks_the_cash_kept(self):
        """With cash, the button MUST open a wizard that declares while closing."""
        sheet = self._create_sheet(cash=40.0)
        self._add_commission(sheet, applied=50.0, percent=10.0)
        action = sheet.action_open_seller_close()
        self.assertEqual(action["res_model"], "collection.sheet.close.wizard")
        self.assertEqual(action["target"], "new")
        self._assert_still_open(sheet)
        wizard = self.env["collection.sheet.close.wizard"].browse(action["res_id"])
        self.assertEqual(wizard.sheet_id, sheet)
        self.assertEqual(wizard.cash_collected, 40.0)
        self.assertEqual(wizard.commission_amount, 5.0)
        wizard.commission_withheld = 2.25
        wizard.action_seller_close()
        self.assertEqual(sheet.state, "submitted")
        self.assertEqual(sheet.commission_withheld, 2.25)
        self.assertTrue(sheet.cash_declared_at)

    def test_wizard_keeping_more_than_the_commission_is_refused(self):
        """The wizard MUST apply the same caps and leave the sheet open."""
        sheet = self._create_sheet(cash=40.0)
        self._add_commission(sheet, applied=50.0, percent=10.0)
        action = sheet.action_open_seller_close()
        wizard = self.env["collection.sheet.close.wizard"].browse(action["res_id"])
        wizard.commission_withheld = 6.0
        with self.assertRaises(UserError):
            wizard.action_seller_close()
        self._assert_still_open(sheet)
