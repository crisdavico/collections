# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase

from .test_collection_payment import (
    PNG_B64,
    create_internal_seller,
    dummy_customer_partner,
    ensure_enabled_seller,
    post_voucher_proof,
)


class TestCollectionMail(TransactionCase):
    """Mail thread / activities and state tracking on vouchers and sheets."""

    def _flush_tracking(self):
        """Force mail.thread precommit tracking finalize (MailCommon.flush_tracking)."""
        self.env.flush_all()
        self.cr.flush()

    def _create_voucher(self, customer=None, **extra):
        seller = extra.get("seller_id") or ensure_enabled_seller(self.env).id
        if extra.get("seller_id"):
            ensure_enabled_seller(
                self.env, self.env["res.users"].browse(extra["seller_id"])
            )
        partner = dummy_customer_partner(
            self.env, customer=customer, extra=extra, default="MAIL-CUST"
        )
        vals = {
            "partner_id": partner.id,
            "document_type": "bank_transfer",
            "seller_id": seller,
        }
        vals.update(extra)
        voucher = self.env["collection.voucher"].create(vals)
        # Clear create-time _track_discard residue before state writes
        self._flush_tracking()
        return voucher

    def _create_sheet(self, **extra):
        seller_id = extra.get("seller_id", ensure_enabled_seller(self.env).id)
        ensure_enabled_seller(self.env, self.env["res.users"].browse(seller_id))
        vals = {"seller_id": seller_id}
        vals.update(extra)
        sheet = self.env["collection.sheet"].create(vals)
        self._flush_tracking()
        return sheet

    def test_message_post_persists_on_voucher(self):
        voucher = self._create_voucher()
        message = voucher.message_post(
            body="Operator note on voucher",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        self.assertTrue(message.id)
        self.assertIn(message, voucher.message_ids)
        self.assertIn("Operator note on voucher", message.body)

    def test_activity_schedule_persists_on_voucher(self):
        voucher = self._create_voucher(customer_identification="MAIL-ACT")
        activity = voucher.activity_schedule(
            "mail.mail_activity_data_todo",
            summary="Review collection voucher",
        )
        self.assertTrue(activity.id)
        self.assertIn(activity, voucher.activity_ids)
        self.assertEqual(activity.summary, "Review collection voucher")

    def test_validate_seller_tracks_state_in_chatter(self):
        voucher = self._create_voucher(customer_identification="MAIL-VAL")
        voucher.action_validate_seller()
        self._flush_tracking()
        tracking = voucher.message_ids.sudo().mapped("tracking_value_ids")
        tracked_fields = tracking.mapped("field_id.name")
        self.assertIn("state", tracked_fields)
        state_tracking = tracking.filtered(lambda t: t.field_id.name == "state")
        self.assertTrue(state_tracking)
        self.assertEqual(state_tracking[-1].old_value_char, "Draft")
        self.assertEqual(state_tracking[-1].new_value_char, "Validated by Seller")

    def test_validate_seller_tracks_state_from_draft_triangulation(self):
        voucher = self._create_voucher(customer_identification="MAIL-REJ")
        self.assertEqual(voucher.state, "draft")
        voucher.action_validate_seller()
        self._flush_tracking()
        tracking = voucher.message_ids.sudo().mapped("tracking_value_ids")
        state_tracking = tracking.filtered(lambda t: t.field_id.name == "state")
        self.assertTrue(state_tracking)
        self.assertEqual(state_tracking[-1].old_value_char, "Draft")
        self.assertEqual(state_tracking[-1].new_value_char, "Validated by Seller")

    def test_voucher_tracks_seller_sheet_type_and_amount(self):
        """seller_id, sheet_id, document_type, and amount MUST set tracking=True."""
        Voucher = self.env["collection.voucher"]
        for name in ("state", "seller_id", "sheet_id", "document_type", "amount"):
            self.assertTrue(
                getattr(Voucher._fields[name], "tracking", False),
                f"{name} must set tracking=True",
            )

    def test_amount_write_tracks_in_chatter(self):
        voucher = self._create_voucher(customer_identification="MAIL-AMT")
        voucher.write({"amount": 123.45})
        self._flush_tracking()
        tracking = voucher.message_ids.sudo().mapped("tracking_value_ids")
        amount_tracking = tracking.filtered(lambda t: t.field_id.name == "amount")
        self.assertTrue(amount_tracking, "amount write must post a tracking value")
        self.assertAlmostEqual(amount_tracking[-1].new_value_float, 123.45)

    def test_seller_id_write_tracks_in_chatter(self):
        """Triangulation: relational seller_id changes MUST track in chatter."""
        self.env.company.write({"auto_create_sheet": False})
        voucher = self._create_voucher(customer_identification="MAIL-SELLER")
        self.assertFalse(voucher.sheet_id)
        other = ensure_enabled_seller(
            self.env, create_internal_seller(self.env, "mail_track_seller")
        )
        self.assertNotEqual(voucher.seller_id, other)
        voucher.write({"seller_id": other.id})
        self._flush_tracking()
        tracking = voucher.message_ids.sudo().mapped("tracking_value_ids")
        seller_tracking = tracking.filtered(lambda t: t.field_id.name == "seller_id")
        self.assertTrue(seller_tracking, "seller_id write must post a tracking value")
        self.assertEqual(seller_tracking[-1].new_value_char, other.display_name)

    def test_sheet_id_and_document_type_write_track_in_chatter(self):
        """sheet_id and document_type writes MUST each post tracking values."""
        self.env.company.write({"auto_create_sheet": False})
        voucher = self._create_voucher(
            customer_identification="MAIL-SHEET-TYPE",
            document_type="bank_transfer",
        )
        sheet = self._create_sheet(seller_id=voucher.seller_id.id)
        voucher.write({"sheet_id": sheet.id, "document_type": "check"})
        self._flush_tracking()
        tracking = voucher.message_ids.sudo().mapped("tracking_value_ids")
        tracked = set(tracking.mapped("field_id.name"))
        self.assertIn("sheet_id", tracked)
        self.assertIn("document_type", tracked)
        sheet_tracking = tracking.filtered(lambda t: t.field_id.name == "sheet_id")
        type_tracking = tracking.filtered(lambda t: t.field_id.name == "document_type")
        self.assertEqual(sheet_tracking[-1].new_value_char, sheet.display_name)
        self.assertEqual(type_tracking[-1].new_value_char, "Check")

    def test_message_post_image_becomes_designated_proof(self):
        """MCP/chatter nest of a valid image MUST become message_main_attachment_id."""
        voucher = self._create_voucher(customer_identification="MAIL-PROOF-PNG")
        proof = post_voucher_proof(voucher, "proof.png", PNG_B64)
        self.assertTrue(proof)
        self.assertEqual(voucher.message_main_attachment_id, proof)
        self.assertEqual(proof.name, "proof.png")
        self.assertFalse(proof.res_field)
        self.assertEqual(proof.res_model, "collection.voucher")
        self.assertEqual(proof.res_id, voucher.id)
        self.assertTrue(
            voucher.message_ids.filtered(
                lambda message: proof in message.attachment_ids
            )
        )

    def test_extra_chatter_file_does_not_steal_proof(self):
        """Extra chatter files with force=False MUST NOT steal designated proof."""
        voucher = self._create_voucher(customer_identification="MAIL-PROOF-KEEP")
        proof = post_voucher_proof(voucher, "proof.png", PNG_B64)
        extra = self.env["ir.attachment"].create(
            {
                "name": "notes.txt",
                "raw": b"hello world",
                "res_model": "collection.voucher",
                "res_id": voucher.id,
            }
        )
        extra._post_add_create()
        voucher.invalidate_recordset()
        self.assertEqual(voucher.message_main_attachment_id, proof)
        self.assertNotEqual(voucher.message_main_attachment_id, extra)

    def test_message_post_persists_on_sheet(self):
        sheet = self._create_sheet()
        message = sheet.message_post(
            body="Operator note on sheet",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        self.assertTrue(message.id)
        self.assertIn(message, sheet.message_ids)
        self.assertIn("Operator note on sheet", message.body)

    def test_activity_schedule_persists_on_sheet(self):
        sheet = self._create_sheet()
        activity = sheet.activity_schedule(
            "mail.mail_activity_data_todo",
            summary="Review collection sheet",
        )
        self.assertTrue(activity.id)
        self.assertIn(activity, sheet.activity_ids)
        self.assertEqual(activity.summary, "Review collection sheet")

    def test_close_tracks_state_in_chatter(self):
        sheet = self._create_sheet()
        sheet.action_seller_close()
        self._flush_tracking()
        sheet.action_confirm()
        self._flush_tracking()
        sheet.action_close()
        self._flush_tracking()
        tracking = sheet.message_ids.sudo().mapped("tracking_value_ids")
        tracked_fields = tracking.mapped("field_id.name")
        self.assertIn("state", tracked_fields)
        state_tracking = tracking.filtered(lambda t: t.field_id.name == "state")
        pairs = {(row.old_value_char, row.new_value_char) for row in state_tracking}
        self.assertIn(("Open", "Submitted by Seller"), pairs)
        self.assertIn(("Submitted by Seller", "Proposal"), pairs)
        self.assertIn(("Proposal", "Closed"), pairs)

    def test_confirm_tracks_state_in_chatter(self):
        sheet = self._create_sheet()
        sheet.action_seller_close()
        self._flush_tracking()
        sheet.action_confirm()
        self._flush_tracking()
        tracking = sheet.message_ids.sudo().mapped("tracking_value_ids")
        state_tracking = tracking.filtered(lambda t: t.field_id.name == "state")
        pairs = {(row.old_value_char, row.new_value_char) for row in state_tracking}
        self.assertIn(("Open", "Submitted by Seller"), pairs)
        self.assertIn(("Submitted by Seller", "Proposal"), pairs)

    def test_cancel_tracks_state_in_chatter(self):
        sheet = self._create_sheet()
        sheet.action_seller_close()
        self._flush_tracking()
        sheet.action_confirm()
        self._flush_tracking()
        sheet.action_cancel()
        self._flush_tracking()
        tracking = sheet.message_ids.sudo().mapped("tracking_value_ids")
        state_tracking = tracking.filtered(lambda t: t.field_id.name == "state")
        pairs = {(row.old_value_char, row.new_value_char) for row in state_tracking}
        self.assertIn(("Open", "Submitted by Seller"), pairs)
        self.assertIn(("Submitted by Seller", "Proposal"), pairs)
        self.assertIn(("Proposal", "Cancelled"), pairs)

    def test_open_tracks_state_in_chatter(self):
        sheet = self._create_sheet()
        sheet.action_seller_close()
        sheet.action_confirm()
        sheet.action_cancel()
        self._flush_tracking()
        sheet.action_reinstate()
        self._flush_tracking()
        tracking = sheet.message_ids.sudo().mapped("tracking_value_ids")
        state_tracking = tracking.filtered(lambda t: t.field_id.name == "state")
        pairs = {(row.old_value_char, row.new_value_char) for row in state_tracking}
        self.assertIn(("Cancelled", "Submitted by Seller"), pairs)

    def test_non_image_extra_cannot_become_proof(self):
        """A non-image/non-PDF chatter file MUST NOT become designated proof."""
        voucher = self._create_voucher(customer_identification="MAIL-PROOF-TXT")
        self.assertFalse(voucher.message_main_attachment_id)
        voucher.message_post(
            body="Extra notes",
            message_type="notification",
            attachments=[("notes.txt", b"hello world")],
        )
        voucher.invalidate_recordset()
        self.assertFalse(voucher.message_main_attachment_id)
        leftover = self.env["ir.attachment"].search(
            [
                ("res_model", "=", "collection.voucher"),
                ("res_id", "=", voucher.id),
                ("name", "=", "notes.txt"),
            ]
        )
        self.assertTrue(leftover, "extra file may exist; it must not be designated")
        self.assertNotIn(leftover, voucher.message_main_attachment_id)
