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
    """RED/GREEN: nullable unique document_id on payment lines."""

    def _create_voucher(self, customer_identification="CUST-DOC"):
        return self.env["collection.voucher"].create(
            {"customer_identification": customer_identification}
        )

    def _payment_vals(self, voucher, **extra):
        vals = {
            "voucher_id": voucher.id,
            "document_type": "bank_transfer",
            "amount": 100.0,
        }
        vals.update(extra)
        return vals

    def test_payment_without_document_id_ok(self):
        """UI payment lines must persist when document_id is omitted."""
        voucher = self._create_voucher()
        payment = self.env["collection.voucher.line"].create(
            self._payment_vals(voucher)
        )
        self.assertTrue(payment.id)
        self.assertFalse(
            payment.document_id,
            "document_id must remain empty when not provided",
        )

    def test_multiple_payments_without_document_id_ok(self):
        """Triangulation: several NULL document_id values must coexist (PG UNIQUE)."""
        voucher = self._create_voucher(customer_identification="CUST-DOC-NULL")
        Payment = self.env["collection.voucher.line"]
        first = Payment.create(self._payment_vals(voucher, amount=10.0))
        second = Payment.create(self._payment_vals(voucher, amount=20.0))
        self.assertTrue(first.id)
        self.assertTrue(second.id)
        self.assertFalse(first.document_id)
        self.assertFalse(second.document_id)
        self.assertNotEqual(first.id, second.id)

    def test_duplicate_non_null_document_id_raises_integrity_error(self):
        """Non-null document_id values must be unique across payment rows."""
        voucher = self._create_voucher(customer_identification="CUST-DOC-DUP")
        Payment = self.env["collection.voucher.line"]
        Payment.create(
            self._payment_vals(voucher, document_id="DOC-UNIQUE-1", amount=50.0)
        )
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                Payment.create(
                    self._payment_vals(voucher, document_id="DOC-UNIQUE-1", amount=75.0)
                )

    def test_distinct_document_ids_ok(self):
        """Triangulation: different non-null document_id values must both persist."""
        voucher = self._create_voucher(customer_identification="CUST-DOC-OK")
        Payment = self.env["collection.voucher.line"]
        first = Payment.create(
            self._payment_vals(voucher, document_id="DOC-A", amount=1.0)
        )
        second = Payment.create(
            self._payment_vals(voucher, document_id="DOC-B", amount=2.0)
        )
        self.assertEqual(first.document_id, "DOC-A")
        self.assertEqual(second.document_id, "DOC-B")


class TestCollectionPaymentAttachment(TransactionCase):
    """RED/GREEN: optional Binary+filename attachment on payment lines."""

    def _create_voucher(self, customer_identification="CUST-ATT"):
        return self.env["collection.voucher"].create(
            {"customer_identification": customer_identification}
        )

    def _payment_vals(self, voucher, **extra):
        vals = {
            "voucher_id": voucher.id,
            "document_type": "bank_transfer",
            "amount": 100.0,
        }
        vals.update(extra)
        return vals

    def _line_attachments(self, line):
        return self.env["ir.attachment"].search(
            [
                ("res_model", "=", "collection.voucher.line"),
                ("res_id", "=", line.id),
                ("res_field", "=", "attachment"),
            ]
        )

    def test_omit_attachment_persists(self):
        """Omit attachment remains valid and persists the line."""
        voucher = self._create_voucher()
        line = self.env["collection.voucher.line"].create(self._payment_vals(voucher))
        self.assertTrue(line.id)
        self.assertFalse(line.attachment)
        self.assertFalse(line.attachment_filename)
        self.assertFalse(self._line_attachments(line))

    def test_valid_png_persists_via_ir_attachment(self):
        """Valid PNG base64 + filename stores Binary via ir.attachment."""
        voucher = self._create_voucher(customer_identification="CUST-ATT-PNG")
        line = self.env["collection.voucher.line"].create(
            self._payment_vals(
                voucher,
                attachment=PNG_B64,
                attachment_filename="proof.png",
            )
        )
        self.assertTrue(line.attachment)
        self.assertEqual(line.attachment_filename, "proof.png")
        attachments = self._line_attachments(line)
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments.datas, PNG_B64.encode())

    def test_valid_pdf_persists_via_ir_attachment(self):
        """Triangulation: valid PDF also persists via ir.attachment."""
        voucher = self._create_voucher(customer_identification="CUST-ATT-PDF")
        line = self.env["collection.voucher.line"].create(
            self._payment_vals(
                voucher,
                attachment=PDF_B64,
                attachment_filename="receipt.pdf",
            )
        )
        self.assertTrue(line.attachment)
        self.assertEqual(line.attachment_filename, "receipt.pdf")
        self.assertEqual(len(self._line_attachments(line)), 1)

    def test_invalid_base64_raises_and_does_not_persist(self):
        """Invalid base64 must raise UserError and not create the line/file."""
        voucher = self._create_voucher(customer_identification="CUST-ATT-B64")
        Payment = self.env["collection.voucher.line"]
        before = Payment.search_count([])
        with self.assertRaises(UserError):
            with self.env.cr.savepoint():
                Payment.create(
                    self._payment_vals(
                        voucher,
                        attachment=INVALID_B64,
                        attachment_filename="bad.bin",
                    )
                )
        self.assertEqual(Payment.search_count([]), before)
        self.assertFalse(
            self.env["ir.attachment"].search(
                [
                    ("res_model", "=", "collection.voucher.line"),
                    ("res_field", "=", "attachment"),
                    ("name", "=", "bad.bin"),
                ]
            )
        )

    def test_non_image_non_pdf_mime_raises_and_does_not_persist(self):
        """Non-image/non-PDF detected MIME must raise UserError and not persist."""
        voucher = self._create_voucher(customer_identification="CUST-ATT-MIME")
        Payment = self.env["collection.voucher.line"]
        before = Payment.search_count([])
        with self.assertRaises(UserError):
            with self.env.cr.savepoint():
                Payment.create(
                    self._payment_vals(
                        voucher,
                        attachment=TXT_B64,
                        attachment_filename="notes.txt",
                    )
                )
        self.assertEqual(Payment.search_count([]), before)
        self.assertFalse(
            self.env["ir.attachment"].search(
                [
                    ("res_model", "=", "collection.voucher.line"),
                    ("res_field", "=", "attachment"),
                    ("name", "=", "notes.txt"),
                ]
            )
        )

    def test_write_replace_updates_attachment(self):
        """Writing a new valid file replaces the stored attachment content."""
        voucher = self._create_voucher(customer_identification="CUST-ATT-REP")
        line = self.env["collection.voucher.line"].create(
            self._payment_vals(
                voucher,
                attachment=PNG_B64,
                attachment_filename="old.png",
            )
        )
        line.write(
            {
                "attachment": PDF_B64,
                "attachment_filename": "new.pdf",
            }
        )
        self.assertEqual(line.attachment_filename, "new.pdf")
        self.assertEqual(line.attachment, PDF_B64.encode())
        attachments = self._line_attachments(line)
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments.datas, PDF_B64.encode())

    def test_clear_attachment_empties_binary_and_filename(self):
        """Clearing attachment empties Binary and filename."""
        voucher = self._create_voucher(customer_identification="CUST-ATT-CLR")
        line = self.env["collection.voucher.line"].create(
            self._payment_vals(
                voucher,
                attachment=PNG_B64,
                attachment_filename="clear-me.png",
            )
        )
        line.write({"attachment": False, "attachment_filename": False})
        self.assertFalse(line.attachment)
        self.assertFalse(line.attachment_filename)
        self.assertFalse(self._line_attachments(line))

    def test_unlink_line_cascades_attachment_cleanup(self):
        """Unlinking a line must remove its stored attachment row."""
        voucher = self._create_voucher(customer_identification="CUST-ATT-UNL")
        line = self.env["collection.voucher.line"].create(
            self._payment_vals(
                voucher,
                attachment=PNG_B64,
                attachment_filename="gone.png",
            )
        )
        att_ids = self._line_attachments(line).ids
        self.assertTrue(att_ids)
        line.unlink()
        self.assertFalse(self.env["ir.attachment"].browse(att_ids).exists())

    def test_copy_does_not_copy_attachment(self):
        """copy=False: duplicated line must not inherit Binary/filename."""
        voucher = self._create_voucher(customer_identification="CUST-ATT-CPY")
        line = self.env["collection.voucher.line"].create(
            self._payment_vals(
                voucher,
                document_id="DOC-ATT-SRC",
                attachment=PNG_B64,
                attachment_filename="source.png",
            )
        )
        clone = line.copy({"document_id": "DOC-ATT-CLONE"})
        self.assertTrue(clone.id)
        self.assertNotEqual(clone.id, line.id)
        self.assertFalse(clone.attachment)
        self.assertFalse(clone.attachment_filename)
        self.assertFalse(self._line_attachments(clone))
        self.assertTrue(line.attachment)
        self.assertEqual(len(self._line_attachments(line)), 1)
