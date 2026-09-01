# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo.exceptions import UserError
from odoo.tests import TransactionCase

from .test_collection_payment import (
    PNG_B64,
    dummy_customer_partner,
    ensure_enabled_seller,
    post_voucher_proof,
)

_REVIEW_DISABLED_MSG = "Document Review is not enabled."


class TestCollectionDocumentReviewFlag(TransactionCase):
    """Company Document Review flag defaults off and Settings persist it."""

    def _force_document_review_enabled(self, enabled):
        self.env.company.write({"document_review_enabled": enabled})

    def _create_sheet(self, **extra):
        seller_id = extra.get("seller_id", ensure_enabled_seller(self.env).id)
        ensure_enabled_seller(self.env, self.env["res.users"].browse(seller_id))
        vals = {"seller_id": seller_id, **extra}
        return self.env["collection.sheet"].create(vals)

    def _create_pending_attached(self, customer, document_id, sheet_id=None):
        seller = ensure_enabled_seller(self.env)
        partner = dummy_customer_partner(self.env, customer=customer)
        vals = {
            "partner_id": partner.id,
            "document_type": "bank_transfer",
            "document_id": document_id,
            "amount": 100.0,
            "seller_id": seller.id,
        }
        if sheet_id:
            vals["sheet_id"] = sheet_id
        voucher = self.env["collection.voucher"].create(vals)
        post_voucher_proof(voucher, "pending.png", PNG_B64)
        return voucher

    def test_document_review_enabled_defaults_false_on_env_company(self):
        field = self.env["res.company"]._fields["document_review_enabled"]
        self.assertFalse(
            field.default(self.env["res.company"]),
            "Document Review must default OFF on res.company",
        )

    def test_document_review_enabled_defaults_false_on_browsed_company(self):
        fresh = self.env["res.company"].new({"name": "Flag Default Off Co"})
        self.assertFalse(
            fresh.document_review_enabled,
            "Document Review must default OFF on a new company record",
        )

    def test_settings_toggle_persists_true_on_company(self):
        self._force_document_review_enabled(False)
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
        self._force_document_review_enabled(False)
        self.assertFalse(
            self.env["res.company"]._document_review_enabled(),
            "Helper must report Document Review OFF when the company flag is off",
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
        self._force_document_review_enabled(False)
        self.assertFalse(self.env.company.document_review_enabled)
        self._create_pending_attached("CUST-FLAG-Q-OFF", "DOC-FLAG-Q-OFF")
        with self.assertRaises(UserError) as error:
            self.env["collection.voucher"].get_review_queue()
        self.assertEqual(str(error.exception), _REVIEW_DISABLED_MSG)

    def test_action_review_approve_does_not_run_when_review_off(self):
        """When OFF, review approve must raise and leave the voucher pending."""
        self._force_document_review_enabled(False)
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
        self._force_document_review_enabled(False)
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
        self._force_document_review_enabled(False)
        self.assertFalse(self.env.company.document_review_enabled)
        voucher = self._create_pending_attached("CUST-FLAG-ROT-OFF", "DOC-FLAG-ROT-OFF")
        with self.assertRaises(UserError) as error:
            voucher.action_review_set_rotation(90)
        self.assertEqual(str(error.exception), _REVIEW_DISABLED_MSG)
        self.assertEqual(voucher.attachment_rotation, 0)

    def test_review_rpcs_refuse_when_off_with_or_without_sheet_id(self):
        """When OFF, all four RPCs refuse whether a sheet id is passed or omitted."""
        self._force_document_review_enabled(False)
        sheet = self._create_sheet()
        voucher = self._create_pending_attached(
            "CUST-FLAG-OFF-BOTH", "DOC-FLAG-OFF-BOTH", sheet_id=sheet.id
        )
        Voucher = self.env["collection.voucher"]
        with self.assertRaises(UserError) as error:
            Voucher.get_review_queue()
        self.assertEqual(str(error.exception), _REVIEW_DISABLED_MSG)
        with self.assertRaises(UserError) as error:
            Voucher.get_review_queue(sheet.id)
        self.assertEqual(str(error.exception), _REVIEW_DISABLED_MSG)
        for call in (
            lambda: voucher.action_review_approve({"amount": 1.0}),
            lambda: voucher.action_review_approve(sheet.id, {"amount": 1.0}),
            lambda: voucher.action_review_reject(),
            lambda: voucher.action_review_reject(sheet.id),
            lambda: voucher.action_review_set_rotation(90),
            lambda: voucher.action_review_set_rotation(sheet.id, 90),
        ):
            with self.assertRaises(UserError) as error:
                call()
            self.assertEqual(str(error.exception), _REVIEW_DISABLED_MSG)
        self.assertEqual(voucher.state, "pending")
        self.assertEqual(voucher.attachment_rotation, 0)
        self.assertAlmostEqual(voucher.amount, 100.0, places=2)

    def test_review_rpcs_refuse_invalid_sheet_id_when_review_on(self):
        """When ON, missing/0/False/bad sheet ids must UserError, not empty queue."""
        self._force_document_review_enabled(True)
        sheet = self._create_sheet()
        voucher = self._create_pending_attached(
            "CUST-FLAG-BAD-SHEET", "DOC-FLAG-BAD-SHEET", sheet_id=sheet.id
        )
        Voucher = self.env["collection.voucher"]
        with self.assertRaises(UserError):
            Voucher.get_review_queue()
        for invalid_id in (None, 0, False, sheet.id + 10**6):
            with self.subTest(sheet_id=invalid_id):
                with self.assertRaises(UserError):
                    Voucher.get_review_queue(invalid_id)
                with self.assertRaises(UserError):
                    voucher.action_review_approve(invalid_id, {"amount": 1.0})
                with self.assertRaises(UserError):
                    voucher.action_review_reject(invalid_id)
                with self.assertRaises(UserError):
                    voucher.action_review_set_rotation(invalid_id, 90)
        self.assertEqual(voucher.state, "pending")
        self.assertEqual(voucher.attachment_rotation, 0)
        self.assertAlmostEqual(voucher.amount, 100.0, places=2)

    def test_form_approve_works_when_review_off(self):
        """Payment Vouchers Approve must work even when Document Review is OFF."""
        self._force_document_review_enabled(False)
        self.assertFalse(self.env.company.document_review_enabled)
        voucher = self.env["collection.voucher"].create(
            {
                "partner_id": dummy_customer_partner(
                    self.env, customer="CUST-FLAG-FORM-APPR"
                ).id,
                "document_type": "bank_transfer",
                "amount": 10.0,
                "seller_id": ensure_enabled_seller(self.env).id,
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
        self._force_document_review_enabled(False)
        self.assertFalse(self.env.company.document_review_enabled)
        voucher = self.env["collection.voucher"].create(
            {
                "partner_id": dummy_customer_partner(
                    self.env, customer="CUST-FLAG-FORM-REJ"
                ).id,
                "document_type": "check",
                "amount": 20.0,
                "seller_id": ensure_enabled_seller(self.env).id,
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
        self.assertEqual(action.tag, "collection.document_review")
        self.assertFalse(
            self.env.ref(
                "collection.menu_collection_document_review",
                raise_if_not_found=False,
            ),
            "Document Review menu xmlid must be gone",
        )

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
        self._force_document_review_enabled(False)
        self.assertFalse(self.env.company.document_review_enabled)
        self._assert_payment_voucher_views_keep_state_and_audit()

    def test_payment_voucher_views_keep_state_when_review_on(self):
        """Triangulation: Payment Vouchers state/audit stay visible when ON."""
        self.env.company.write({"document_review_enabled": True})
        self.assertTrue(self.env.company.document_review_enabled)
        self._assert_payment_voucher_views_keep_state_and_audit()

    def test_saving_other_collection_settings_preserves_document_review_on(self):
        """Saving other Collection Settings MUST NOT clear Document Review ON."""
        self.env.company.write({"document_review_enabled": True})
        self.assertTrue(self.env.company.document_review_enabled)
        settings = self.env["res.config.settings"].create({"auto_create_sheet": False})
        settings.execute()
        self.assertTrue(
            self.env.company.document_review_enabled,
            "document_review_enabled must remain ON when other settings are saved",
        )
        self.assertFalse(
            self.env.company.auto_create_sheet,
            "auto_create_sheet must persist False from Collection Settings",
        )

    def test_saving_other_collection_settings_preserves_document_review_off(self):
        """Triangulation: Document Review OFF stays OFF when other settings save."""
        self._force_document_review_enabled(False)
        self.assertFalse(self.env.company.document_review_enabled)
        settings = self.env["res.config.settings"].create({"auto_create_sheet": False})
        settings.execute()
        self.assertFalse(
            self.env.company.document_review_enabled,
            "document_review_enabled must remain OFF when other settings are saved",
        )
        self.assertFalse(self.env.company.auto_create_sheet)
