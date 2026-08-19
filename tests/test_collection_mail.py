# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase

from .test_collection_payment import PNG_B64, ensure_enabled_seller, post_voucher_proof


class TestCollectionMail(TransactionCase):
    """Mail thread / activities and state tracking on vouchers and sheets."""

    def _flush_tracking(self):
        """Force mail.thread precommit tracking finalize (MailCommon.flush_tracking)."""
        self.env.flush_all()
        self.cr.flush()

    def _create_voucher(self, **extra):
        seller = extra.get("seller_id") or ensure_enabled_seller(self.env).id
        if extra.get("seller_id"):
            ensure_enabled_seller(
                self.env, self.env["res.users"].browse(extra["seller_id"])
            )
        vals = {
            "customer_identification": "MAIL-CUST",
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

    def test_approve_tracks_state_in_chatter(self):
        voucher = self._create_voucher(customer_identification="MAIL-VAL")
        voucher.action_approve()
        self._flush_tracking()
        tracking = voucher.message_ids.sudo().mapped("tracking_value_ids")
        tracked_fields = tracking.mapped("field_id.name")
        self.assertIn("state", tracked_fields)
        state_tracking = tracking.filtered(lambda t: t.field_id.name == "state")
        self.assertTrue(state_tracking)
        self.assertEqual(state_tracking[-1].old_value_char, "Pending")
        self.assertEqual(state_tracking[-1].new_value_char, "Approved")

    def test_reject_tracks_state_in_chatter(self):
        voucher = self._create_voucher(customer_identification="MAIL-REJ")
        voucher.action_reject()
        self._flush_tracking()
        tracking = voucher.message_ids.sudo().mapped("tracking_value_ids")
        tracked_fields = tracking.mapped("field_id.name")
        self.assertIn("state", tracked_fields)
        state_tracking = tracking.filtered(lambda t: t.field_id.name == "state")
        self.assertTrue(state_tracking)
        self.assertEqual(state_tracking[-1].old_value_char, "Pending")
        self.assertEqual(state_tracking[-1].new_value_char, "Rejected")

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
        sheet.action_close()
        self._flush_tracking()
        tracking = sheet.message_ids.sudo().mapped("tracking_value_ids")
        tracked_fields = tracking.mapped("field_id.name")
        self.assertIn("state", tracked_fields)
        state_tracking = tracking.filtered(lambda t: t.field_id.name == "state")
        self.assertTrue(state_tracking)
        self.assertEqual(state_tracking[-1].old_value_char, "Open")
        self.assertEqual(state_tracking[-1].new_value_char, "Closed")

    def test_reopen_tracks_state_in_chatter(self):
        sheet = self._create_sheet()
        sheet.action_close()
        self._flush_tracking()
        sheet.action_reopen()
        self._flush_tracking()
        tracking = sheet.message_ids.sudo().mapped("tracking_value_ids")
        state_tracking = tracking.filtered(lambda t: t.field_id.name == "state")
        pairs = {(row.old_value_char, row.new_value_char) for row in state_tracking}
        self.assertIn(("Open", "Closed"), pairs)
        self.assertIn(("Closed", "Open"), pairs)

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
