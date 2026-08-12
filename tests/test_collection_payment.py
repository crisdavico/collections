# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from psycopg2 import IntegrityError

from odoo.exceptions import UserError
from odoo.tests import TransactionCase
from odoo.tools import mute_logger

# Minimal valid payloads (base64) for MIME triangulation.
PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4z8AAAAMBAQ"
    "DJ/pLvAAAAAElFTkSuQmCC"
)
PDF_B64 = "JVBERi0xLjEKMSAwIG9iajw8Pj5lbmRvYmoKdHJhaWxlcjw8Pj4KJSVFT0YK"
TXT_B64 = "aGVsbG8gd29ybGQ="
INVALID_B64 = "!!!not-base64!!!"


class TestCollectionPaymentDocumentId(TransactionCase):
    """RED/GREEN: nullable unique document_id on standalone vouchers."""

    def _voucher_vals(self, **extra):
        vals = {
            "customer_identification": "CUST-DOC",
            "document_type": "bank_transfer",
            "amount": 100.0,
        }
        vals.update(extra)
        return vals

    def test_payment_without_document_id_ok(self):
        """UI vouchers must persist when document_id is omitted."""
        voucher = self.env["collection.voucher"].create(self._voucher_vals())
        self.assertTrue(voucher.id)
        self.assertFalse(
            voucher.document_id,
            "document_id must remain empty when not provided",
        )

    def test_multiple_payments_without_document_id_ok(self):
        """Triangulation: several NULL document_id values must coexist (PG UNIQUE)."""
        Voucher = self.env["collection.voucher"]
        first = Voucher.create(
            self._voucher_vals(customer_identification="CUST-DOC-NULL-1", amount=10.0)
        )
        second = Voucher.create(
            self._voucher_vals(customer_identification="CUST-DOC-NULL-2", amount=20.0)
        )
        self.assertTrue(first.id)
        self.assertTrue(second.id)
        self.assertFalse(first.document_id)
        self.assertFalse(second.document_id)
        self.assertNotEqual(first.id, second.id)

    def test_duplicate_non_null_document_id_raises_integrity_error(self):
        """Non-null document_id values must be unique across vouchers."""
        Voucher = self.env["collection.voucher"]
        Voucher.create(
            self._voucher_vals(
                customer_identification="CUST-DOC-DUP-1",
                document_id="DOC-UNIQUE-1",
                amount=50.0,
            )
        )
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                Voucher.create(
                    self._voucher_vals(
                        customer_identification="CUST-DOC-DUP-2",
                        document_id="DOC-UNIQUE-1",
                        amount=75.0,
                    )
                )

    def test_distinct_document_ids_ok(self):
        """Triangulation: different non-null document_id values must both persist."""
        Voucher = self.env["collection.voucher"]
        first = Voucher.create(
            self._voucher_vals(
                customer_identification="CUST-DOC-OK-A",
                document_id="DOC-A",
                amount=1.0,
            )
        )
        second = Voucher.create(
            self._voucher_vals(
                customer_identification="CUST-DOC-OK-B",
                document_id="DOC-B",
                amount=2.0,
            )
        )
        self.assertEqual(first.document_id, "DOC-A")
        self.assertEqual(second.document_id, "DOC-B")


class TestCollectionPaymentAttachment(TransactionCase):
    """RED/GREEN: optional Binary+filename attachment on standalone vouchers."""

    def _voucher_vals(self, **extra):
        vals = {
            "customer_identification": "CUST-ATT",
            "document_type": "bank_transfer",
            "amount": 100.0,
        }
        vals.update(extra)
        return vals

    def _voucher_attachments(self, voucher):
        return self.env["ir.attachment"].search(
            [
                ("res_model", "=", "collection.voucher"),
                ("res_id", "=", voucher.id),
                ("res_field", "=", "attachment"),
            ]
        )

    def test_omit_attachment_persists(self):
        """Omit attachment remains valid and persists the voucher."""
        voucher = self.env["collection.voucher"].create(self._voucher_vals())
        self.assertTrue(voucher.id)
        self.assertFalse(voucher.attachment)
        self.assertFalse(voucher.attachment_filename)
        self.assertFalse(self._voucher_attachments(voucher))

    def test_valid_png_persists_via_ir_attachment(self):
        """Valid PNG base64 + filename stores Binary via ir.attachment."""
        voucher = self.env["collection.voucher"].create(
            self._voucher_vals(
                customer_identification="CUST-ATT-PNG",
                attachment=PNG_B64,
                attachment_filename="proof.png",
            )
        )
        self.assertTrue(voucher.attachment)
        self.assertEqual(voucher.attachment_filename, "proof.png")
        attachments = self._voucher_attachments(voucher)
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments.res_model, "collection.voucher")
        self.assertEqual(attachments.datas, PNG_B64.encode())

    def test_valid_pdf_persists_via_ir_attachment(self):
        """Triangulation: valid PDF also persists via ir.attachment."""
        voucher = self.env["collection.voucher"].create(
            self._voucher_vals(
                customer_identification="CUST-ATT-PDF",
                attachment=PDF_B64,
                attachment_filename="receipt.pdf",
            )
        )
        self.assertTrue(voucher.attachment)
        self.assertEqual(voucher.attachment_filename, "receipt.pdf")
        attachments = self._voucher_attachments(voucher)
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments.res_model, "collection.voucher")

    def test_invalid_base64_raises_and_does_not_persist(self):
        """Invalid base64 must raise UserError and not create the voucher/file."""
        Voucher = self.env["collection.voucher"]
        before = Voucher.search_count([])
        with self.assertRaises(UserError):
            with self.env.cr.savepoint():
                Voucher.create(
                    self._voucher_vals(
                        customer_identification="CUST-ATT-B64",
                        attachment=INVALID_B64,
                        attachment_filename="bad.bin",
                    )
                )
        self.assertEqual(Voucher.search_count([]), before)
        self.assertFalse(
            self.env["ir.attachment"].search(
                [
                    ("res_model", "=", "collection.voucher"),
                    ("res_field", "=", "attachment"),
                    ("name", "=", "bad.bin"),
                ]
            )
        )

    def test_non_image_non_pdf_mime_raises_and_does_not_persist(self):
        """Non-image/non-PDF detected MIME must raise UserError and not persist."""
        Voucher = self.env["collection.voucher"]
        before = Voucher.search_count([])
        with self.assertRaises(UserError):
            with self.env.cr.savepoint():
                Voucher.create(
                    self._voucher_vals(
                        customer_identification="CUST-ATT-MIME",
                        attachment=TXT_B64,
                        attachment_filename="notes.txt",
                    )
                )
        self.assertEqual(Voucher.search_count([]), before)
        self.assertFalse(
            self.env["ir.attachment"].search(
                [
                    ("res_model", "=", "collection.voucher"),
                    ("res_field", "=", "attachment"),
                    ("name", "=", "notes.txt"),
                ]
            )
        )

    def test_write_replace_updates_attachment(self):
        """Writing a new valid file replaces the stored attachment content."""
        voucher = self.env["collection.voucher"].create(
            self._voucher_vals(
                customer_identification="CUST-ATT-REP",
                attachment=PNG_B64,
                attachment_filename="old.png",
            )
        )
        voucher.write(
            {
                "attachment": PDF_B64,
                "attachment_filename": "new.pdf",
            }
        )
        self.assertEqual(voucher.attachment_filename, "new.pdf")
        self.assertEqual(voucher.attachment, PDF_B64.encode())
        attachments = self._voucher_attachments(voucher)
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments.datas, PDF_B64.encode())

    def test_write_replace_resets_approved_review_to_pending(self):
        """Replacing Binary content must reopen review and clear audit."""
        voucher = self.env["collection.voucher"].create(
            self._voucher_vals(
                customer_identification="CUST-ATT-RST",
                document_id="DOC-ATT-RST",
                attachment=PNG_B64,
                attachment_filename="old.png",
            )
        )
        voucher.action_approve()
        self.assertEqual(voucher.state, "approved")
        voucher.write(
            {
                "attachment": PDF_B64,
                "attachment_filename": "new.pdf",
            }
        )
        self.assertEqual(voucher.state, "pending")
        self.assertFalse(voucher.reviewed_by)
        self.assertFalse(voucher.reviewed_at)
        self.assertEqual(voucher.attachment_filename, "new.pdf")

    def test_write_replace_resets_rejected_review_to_pending(self):
        """Triangulation: replacing a rejected voucher's file also reopens review."""
        voucher = self.env["collection.voucher"].create(
            self._voucher_vals(
                customer_identification="CUST-ATT-RST-REJ",
                document_id="DOC-ATT-RST-REJ",
                attachment=PNG_B64,
                attachment_filename="rej.png",
            )
        )
        voucher.action_reject()
        voucher.write(
            {
                "attachment": PNG_B64,
                "attachment_filename": "again.png",
            }
        )
        self.assertEqual(voucher.state, "pending")
        self.assertFalse(voucher.reviewed_by)
        self.assertFalse(voucher.reviewed_at)

    def test_clear_attachment_empties_binary_and_filename(self):
        """Clearing attachment empties Binary and filename."""
        voucher = self.env["collection.voucher"].create(
            self._voucher_vals(
                customer_identification="CUST-ATT-CLR",
                attachment=PNG_B64,
                attachment_filename="clear-me.png",
            )
        )
        voucher.write({"attachment": False, "attachment_filename": False})
        self.assertFalse(voucher.attachment)
        self.assertFalse(voucher.attachment_filename)
        self.assertFalse(self._voucher_attachments(voucher))

    def test_unlink_voucher_cascades_attachment_cleanup(self):
        """Unlinking a voucher must remove its stored attachment row."""
        voucher = self.env["collection.voucher"].create(
            self._voucher_vals(
                customer_identification="CUST-ATT-UNL",
                attachment=PNG_B64,
                attachment_filename="gone.png",
            )
        )
        att_ids = self._voucher_attachments(voucher).ids
        self.assertTrue(att_ids)
        voucher.unlink()
        self.assertFalse(self.env["ir.attachment"].browse(att_ids).exists())

    def test_copy_does_not_copy_attachment(self):
        """copy=False: duplicated voucher must not inherit Binary/filename."""
        voucher = self.env["collection.voucher"].create(
            self._voucher_vals(
                customer_identification="CUST-ATT-CPY",
                document_id="DOC-ATT-SRC",
                attachment=PNG_B64,
                attachment_filename="source.png",
            )
        )
        clone = voucher.copy({"document_id": "DOC-ATT-CLONE"})
        self.assertTrue(clone.id)
        self.assertNotEqual(clone.id, voucher.id)
        self.assertFalse(clone.attachment)
        self.assertFalse(clone.attachment_filename)
        self.assertFalse(self._voucher_attachments(clone))
        self.assertTrue(voucher.attachment)
        self.assertEqual(len(self._voucher_attachments(voucher)), 1)
