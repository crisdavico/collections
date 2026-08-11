# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from psycopg2 import IntegrityError

from odoo.tests import TransactionCase
from odoo.tools import mute_logger


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
