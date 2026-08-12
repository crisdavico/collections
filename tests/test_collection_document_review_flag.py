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
        voucher = self.env["collection.voucher"].create(
            {"customer_identification": customer}
        )
        line = self.env["collection.voucher.line"].create(
            {
                "voucher_id": voucher.id,
                "document_type": "bank_transfer",
                "document_id": document_id,
                "amount": 100.0,
                "attachment": PNG_B64,
                "attachment_filename": "pending.png",
            }
        )
        return voucher, line

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

    def test_action_validate_succeeds_with_pending_attached_when_review_off(self):
        """OFF: validate succeeds while attached payment lines are still pending."""
        self.assertFalse(
            self.env.company.document_review_enabled,
            "Document Review must stay OFF for this case",
        )
        voucher = self.env["collection.voucher"].create(
            {"customer_identification": "CUST-FLAG-VAL-OFF"}
        )
        line = self.env["collection.voucher.line"].create(
            {
                "voucher_id": voucher.id,
                "document_type": "bank_transfer",
                "document_id": "DOC-FLAG-VAL-OFF",
                "amount": 100.0,
                "attachment": PNG_B64,
                "attachment_filename": "pending.png",
            }
        )
        self.assertEqual(line.state, "pending")
        self.assertTrue(line.attachment)
        voucher.action_validate()
        self.assertEqual(voucher.state, "validated")

    def test_get_review_queue_raises_when_review_off(self):
        """When OFF, get_review_queue must refuse with UserError, not return []."""
        self.assertFalse(self.env.company.document_review_enabled)
        self._create_pending_attached("CUST-FLAG-Q-OFF", "DOC-FLAG-Q-OFF")
        with self.assertRaises(UserError) as error:
            self.env["collection.voucher.line"].get_review_queue()
        self.assertEqual(str(error.exception), _REVIEW_DISABLED_MSG)

    def test_action_review_approve_does_not_run_when_review_off(self):
        """When OFF, approve must raise and leave the line pending."""
        self.assertFalse(self.env.company.document_review_enabled)
        voucher, line = self._create_pending_attached(
            "CUST-FLAG-APPR-OFF", "DOC-FLAG-APPR-OFF"
        )
        with self.assertRaises(UserError) as error:
            line.action_review_approve()
        self.assertEqual(str(error.exception), _REVIEW_DISABLED_MSG)
        self.assertEqual(line.state, "pending")
        self.assertEqual(voucher.state, "new")

    def test_action_review_reject_does_not_run_when_review_off(self):
        """When OFF, reject must raise and leave the voucher new."""
        self.assertFalse(self.env.company.document_review_enabled)
        voucher, line = self._create_pending_attached(
            "CUST-FLAG-REJ-OFF", "DOC-FLAG-REJ-OFF"
        )
        with self.assertRaises(UserError) as error:
            line.action_review_reject()
        self.assertEqual(str(error.exception), _REVIEW_DISABLED_MSG)
        self.assertEqual(line.state, "pending")
        self.assertEqual(voucher.state, "new")

    def test_action_review_set_rotation_raises_when_review_off(self):
        """When OFF, set_rotation must raise and not persist rotation."""
        self.assertFalse(self.env.company.document_review_enabled)
        _voucher, line = self._create_pending_attached(
            "CUST-FLAG-ROT-OFF", "DOC-FLAG-ROT-OFF"
        )
        with self.assertRaises(UserError) as error:
            line.action_review_set_rotation(90)
        self.assertEqual(str(error.exception), _REVIEW_DISABLED_MSG)
        self.assertEqual(line.attachment_rotation, 0)

    def _assert_payment_line_views_keep_state_and_audit(self):
        list_root = etree.fromstring(
            self.env.ref("collection.view_collection_voucher_line_list").arch
        )
        search_root = etree.fromstring(
            self.env.ref("collection.view_collection_voucher_line_search").arch
        )
        self.assertTrue(
            list_root.xpath('./field[@name="state"]'),
            "Payment Lines list must show state regardless of Document Review flag",
        )
        self.assertTrue(
            search_root.xpath('.//field[@name="state"]'),
            "Payment Lines search must expose state regardless of Document Review flag",
        )
        for value in ("pending", "approved", "rejected"):
            matching = [
                node
                for node in search_root.xpath(f'//filter[contains(@domain, "{value}")]')
                if "state" in (node.get("domain") or "")
            ]
            self.assertTrue(
                matching,
                f"Payment Lines search must filter state={value}",
            )
        self.assertTrue(
            search_root.xpath('//filter[contains(@context, "state")]'),
            "Payment Lines search must offer group_by state",
        )
        for field_name in ("reviewed_by", "reviewed_at"):
            list_nodes = list_root.xpath(f'.//field[@name="{field_name}"]')
            search_nodes = search_root.xpath(f'.//field[@name="{field_name}"]')
            if list_nodes:
                self.assertEqual(list_nodes[0].get("name"), field_name)
            if search_nodes:
                self.assertEqual(search_nodes[0].get("name"), field_name)
        list_xml = etree.tostring(list_root, encoding="unicode")
        search_xml = etree.tostring(search_root, encoding="unicode")
        self.assertNotIn("document_review_enabled", list_xml)
        self.assertNotIn("document_review_enabled", search_xml)

    def test_payment_line_views_keep_state_when_review_off(self):
        """When OFF, Payment Lines list/search must still show state (and audit)."""
        self.assertFalse(self.env.company.document_review_enabled)
        self._assert_payment_line_views_keep_state_and_audit()

    def test_payment_line_views_keep_state_when_review_on(self):
        """Triangulation: Payment Lines state/audit stay visible when the flag is ON."""
        self.env.company.write({"document_review_enabled": True})
        self.assertTrue(self.env.company.document_review_enabled)
        self._assert_payment_line_views_keep_state_and_audit()
