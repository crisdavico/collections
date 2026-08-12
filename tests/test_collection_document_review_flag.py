# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo.exceptions import UserError
from odoo.tests import TransactionCase

from .test_collection_payment import PNG_B64

_REVIEW_DISABLED_MSG = "Document Review is not enabled."


class TestCollectionDocumentReviewFlag(TransactionCase):
    """Company Document Review flag defaults off and Settings persist it."""

    def _create_pending_attached(self, customer, document_id):
        return self.env["collection.voucher"].create(
            {
                "customer_identification": customer,
                "document_type": "bank_transfer",
                "document_id": document_id,
                "amount": 100.0,
                "attachment": PNG_B64,
                "attachment_filename": "pending.png",
            }
        )

    def test_document_review_enabled_defaults_false_on_env_company(self):
        self.assertFalse(
            self.env.company.document_review_enabled,
            "Document Review must be OFF on the current company by default",
        )

    def test_document_review_enabled_defaults_false_on_browsed_company(self):
        companies = self.env["res.company"].search([])
        self.assertTrue(companies, "at least one company must exist")
        for company in companies:
            self.assertFalse(
                company.document_review_enabled,
                "Document Review must be OFF on browsed company records",
            )
        fresh = self.env["res.company"].new({"name": "Flag Default Off Co"})
        self.assertFalse(
            fresh.document_review_enabled,
            "Document Review must default OFF on a new company record",
        )

    def test_settings_toggle_persists_true_on_company(self):
        self.assertFalse(self.env.company.document_review_enabled)
        settings = self.env["res.config.settings"].create(
            {"document_review_enabled": True}
        )
        settings.execute()
        self.assertTrue(
            self.env.company.document_review_enabled,
            "Settings must persist Document Review ON onto the current company",
        )

    def test_settings_toggle_persists_false_on_company(self):
        self.env.company.write({"document_review_enabled": True})
        self.assertTrue(self.env.company.document_review_enabled)
        settings = self.env["res.config.settings"].create(
            {"document_review_enabled": False}
        )
        settings.execute()
        self.assertFalse(
            self.env.company.document_review_enabled,
            "Settings must persist Document Review OFF onto the current company",
        )

    def test_document_review_helper_defaults_false(self):
        self.assertFalse(
            self.env["res.company"]._document_review_enabled(),
            "Helper must report Document Review OFF by default",
        )

    def test_document_review_helper_follows_company_write(self):
        self.env.company.write({"document_review_enabled": True})
        self.assertTrue(
            self.env["res.company"]._document_review_enabled(),
            "Helper must report Document Review ON after company write",
        )
        self.env.company.write({"document_review_enabled": False})
        self.assertFalse(
            self.env["res.company"]._document_review_enabled(),
            "Helper must report Document Review OFF after writing False",
        )
        self.assertFalse(self.env.company.document_review_enabled)

    def test_get_review_queue_raises_when_review_off(self):
        """When OFF, get_review_queue must refuse with UserError, not return []."""
        self.assertFalse(self.env.company.document_review_enabled)
        self._create_pending_attached("CUST-FLAG-Q-OFF", "DOC-FLAG-Q-OFF")
        with self.assertRaises(UserError) as error:
            self.env["collection.voucher"].get_review_queue()
        self.assertEqual(str(error.exception), _REVIEW_DISABLED_MSG)

    def test_action_review_approve_does_not_run_when_review_off(self):
        """When OFF, review approve must raise and leave the voucher pending."""
        self.assertFalse(self.env.company.document_review_enabled)
        voucher = self._create_pending_attached(
            "CUST-FLAG-APPR-OFF", "DOC-FLAG-APPR-OFF"
        )
        with self.assertRaises(UserError) as error:
            voucher.action_review_approve({"amount": 1.0})
        self.assertEqual(str(error.exception), _REVIEW_DISABLED_MSG)
        self.assertEqual(voucher.state, "pending")
        self.assertAlmostEqual(voucher.amount, 100.0, places=2)
        self.assertFalse(voucher.reviewed_by)
        self.assertFalse(voucher.reviewed_at)

    def test_action_review_reject_does_not_run_when_review_off(self):
        """When OFF, review reject must raise and leave the voucher pending."""
        self.assertFalse(self.env.company.document_review_enabled)
        voucher = self._create_pending_attached("CUST-FLAG-REJ-OFF", "DOC-FLAG-REJ-OFF")
        with self.assertRaises(UserError) as error:
            voucher.action_review_reject()
        self.assertEqual(str(error.exception), _REVIEW_DISABLED_MSG)
        self.assertEqual(voucher.state, "pending")
        self.assertFalse(voucher.reviewed_by)
        self.assertFalse(voucher.reviewed_at)

    def test_action_review_set_rotation_raises_when_review_off(self):
        """When OFF, set_rotation must raise and not persist rotation."""
        self.assertFalse(self.env.company.document_review_enabled)
        voucher = self._create_pending_attached("CUST-FLAG-ROT-OFF", "DOC-FLAG-ROT-OFF")
        with self.assertRaises(UserError) as error:
            voucher.action_review_set_rotation(90)
        self.assertEqual(str(error.exception), _REVIEW_DISABLED_MSG)
        self.assertEqual(voucher.attachment_rotation, 0)

    def test_form_approve_works_when_review_off(self):
        """Payment Vouchers Approve must work even when Document Review is OFF."""
        self.assertFalse(self.env.company.document_review_enabled)
        voucher = self.env["collection.voucher"].create(
            {
                "customer_identification": "CUST-FLAG-FORM-APPR",
                "document_type": "bank_transfer",
                "amount": 10.0,
            }
        )
        with self.assertRaises(UserError):
            self.env["collection.voucher"].get_review_queue()
        voucher.action_approve()
        self.assertEqual(voucher.state, "approved")
        self.assertEqual(voucher.reviewed_by, self.env.user)
        self.assertTrue(voucher.reviewed_at)

    def test_form_reject_works_when_review_off(self):
        """Triangulation: Payment Vouchers Reject must work when the flag is OFF."""
        self.assertFalse(self.env.company.document_review_enabled)
        voucher = self.env["collection.voucher"].create(
            {
                "customer_identification": "CUST-FLAG-FORM-REJ",
                "document_type": "check",
                "amount": 20.0,
            }
        )
        with self.assertRaises(UserError):
            voucher.action_review_reject()
        voucher.action_reject()
        self.assertEqual(voucher.state, "rejected")
        self.assertEqual(voucher.reviewed_by, self.env.user)
        self.assertTrue(voucher.reviewed_at)

    def test_document_review_xmlids_kept(self):
        action = self.env.ref("collection.action_collection_document_review")
        menu = self.env.ref("collection.menu_collection_document_review")
        self.assertEqual(action.tag, "collection.document_review")
        self.assertEqual(menu.action, action)

    def _assert_payment_voucher_views_keep_state_and_audit(self):
        list_root = etree.fromstring(
            self.env.ref("collection.view_collection_voucher_list").arch
        )
        search_root = etree.fromstring(
            self.env.ref("collection.view_collection_voucher_search").arch
        )
        form_root = etree.fromstring(
            self.env.ref("collection.view_collection_voucher_form").arch
        )
        self.assertTrue(
            list_root.xpath('./field[@name="state"]'),
            "Payment Vouchers list must show state regardless of Document Review flag",
        )
        self.assertTrue(
            search_root.xpath('.//field[@name="state"]'),
            "Payment Vouchers search must expose state regardless of the flag",
        )
        for value in ("pending", "approved", "rejected"):
            matching = [
                node
                for node in search_root.xpath(f'//filter[contains(@domain, "{value}")]')
                if "state" in (node.get("domain") or "")
            ]
            self.assertTrue(
                matching,
                f"Payment Vouchers search must filter state={value}",
            )
        self.assertTrue(
            search_root.xpath('//filter[contains(@context, "state")]'),
            "Payment Vouchers search must offer group_by state",
        )
        for field_name in ("reviewed_by", "reviewed_at"):
            self.assertTrue(
                list_root.xpath(f'.//field[@name="{field_name}"]'),
                f"Payment Vouchers list must show audit column {field_name}",
            )
            self.assertTrue(
                form_root.xpath(f'.//field[@name="{field_name}"]'),
                f"Payment Vouchers form must show audit field {field_name}",
            )
        list_xml = etree.tostring(list_root, encoding="unicode")
        search_xml = etree.tostring(search_root, encoding="unicode")
        form_xml = etree.tostring(form_root, encoding="unicode")
        self.assertNotIn("document_review_enabled", list_xml)
        self.assertNotIn("document_review_enabled", search_xml)
        self.assertNotIn("document_review_enabled", form_xml)
        self.assertFalse(
            self.env.ref(
                "collection.view_collection_voucher_line_list",
                raise_if_not_found=False,
            ),
            "Payment Lines views must stay removed",
        )

    def test_payment_voucher_views_keep_state_when_review_off(self):
        """When OFF, Payment Vouchers list/form must still show state (and audit)."""
        self.assertFalse(self.env.company.document_review_enabled)
        self._assert_payment_voucher_views_keep_state_and_audit()

    def test_payment_voucher_views_keep_state_when_review_on(self):
        """Triangulation: Payment Vouchers state/audit stay visible when ON."""
        self.env.company.write({"document_review_enabled": True})
        self.assertTrue(self.env.company.document_review_enabled)
        self._assert_payment_voucher_views_keep_state_and_audit()
