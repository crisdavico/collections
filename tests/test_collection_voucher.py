# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date

from psycopg2 import IntegrityError

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase
from odoo.tools import mute_logger

from .test_collection_payment import PNG_B64


class TestCollectionVoucher(TransactionCase):
    """RED/GREEN tests for collection.voucher and payment lines."""

    def _create_voucher(self, **extra):
        vals = {
            "customer_identification": "CUST-001",
        }
        vals.update(extra)
        return self.env["collection.voucher"].create(vals)

    # --- 1.1 Sequence naming ---

    def test_sequence_assigned_on_create(self):
        year = date.today().year
        voucher = self._create_voucher()
        self.assertRegex(
            voucher.name,
            rf"^COL/{year}/\d{{4}}$",
            "Voucher name must match COL/<year>/<padded number>",
        )

    def test_sequence_names_are_unique(self):
        first = self._create_voucher(customer_identification="A")
        second = self._create_voucher(customer_identification="B")
        self.assertNotEqual(first.name, second.name)
        self.assertTrue(first.name)
        self.assertTrue(second.name)

    # --- 1.2 Defaults and required fields ---

    def test_defaults_on_create(self):
        voucher = self._create_voucher()
        self.assertNotIn(
            "received_date",
            self.env["collection.voucher"]._fields,
            "received_date must be removed from the voucher model",
        )
        self.assertTrue(
            voucher.create_date,
            "create_date must be set automatically by the ORM",
        )
        self.assertEqual(voucher.state, "new")
        self.assertEqual(
            voucher.currency_id,
            self.env.company.currency_id,
            "Currency must default to company currency",
        )

    def test_customer_identification_required(self):
        # Odoo 19 enforces required Char via DB NOT NULL on create({})
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            self.env["collection.voucher"].create({})

    def test_received_date_field_absent(self):
        """Triangulation: field must not exist on the model registry."""
        self.assertNotIn("received_date", self.env["collection.voucher"]._fields)

    def test_create_rejects_received_date_vals(self):
        """Create vals must not accept received_date after the field is dropped."""
        with self.assertRaises(ValueError):
            self.env["collection.voucher"].create(
                {
                    "customer_identification": "CUST-NO-RECV",
                    "received_date": fields.Date.today(),
                }
            )

    def test_create_date_not_overridable(self):
        """Caller-supplied create_date must not stick; ORM owns registration time."""
        forged = fields.Datetime.to_datetime("2020-01-15 12:00:00")
        voucher = self.env["collection.voucher"].create(
            {
                "customer_identification": "CUST-CREATE-DATE",
                "create_date": forged,
            }
        )
        self.assertNotEqual(
            fields.Datetime.to_datetime(voucher.create_date),
            forged,
            "create_date must not be caller-overridable",
        )
        self.assertTrue(voucher.create_date)

    # --- 1.3 State transitions and unlink ---

    def test_action_validate_from_new(self):
        voucher = self._create_voucher()
        voucher.action_validate()
        self.assertEqual(voucher.state, "validated")

    def test_action_validate_blocked_when_attached_line_pending(self):
        """Validate must refuse while an attached line is still pending review."""
        self.env.company.write({"document_review_enabled": True})
        voucher = self._create_voucher(customer_identification="CUST-VAL-PEND")
        self.env["collection.voucher.line"].create(
            {
                "voucher_id": voucher.id,
                "document_type": "bank_transfer",
                "document_id": "DOC-VAL-PEND",
                "attachment": PNG_B64,
                "attachment_filename": "pending.png",
            }
        )
        with self.assertRaises(UserError):
            voucher.action_validate()
        self.assertEqual(voucher.state, "new")

    def test_action_validate_allows_unattached_pending_line(self):
        """Triangulation: unattached pending lines must not block validate."""
        voucher = self._create_voucher(customer_identification="CUST-VAL-UNATT")
        line = self.env["collection.voucher.line"].create(
            {
                "voucher_id": voucher.id,
                "document_type": "cash_deposit",
                "document_id": "DOC-VAL-UNATT",
                "amount": 10.0,
            }
        )
        self.assertEqual(line.state, "pending")
        self.assertFalse(line.attachment)
        voucher.action_validate()
        self.assertEqual(voucher.state, "validated")

    def test_action_reject_from_new(self):
        voucher = self._create_voucher()
        voucher.action_reject()
        self.assertEqual(voucher.state, "rejected")

    def test_kanban_drag_writes_state(self):
        """Moving a card between columns must persist the target state."""
        voucher = self._create_voucher()
        voucher.write({"state": "validated"})
        self.assertEqual(voucher.state, "validated")
        voucher.write({"state": "rejected"})
        self.assertEqual(voucher.state, "rejected")
        voucher.write({"state": "new"})
        self.assertEqual(voucher.state, "new")

    def test_terminal_states_block_validate_and_reject(self):
        validated = self._create_voucher(customer_identification="V1")
        validated.action_validate()
        with self.assertRaises(UserError):
            validated.action_validate()
        with self.assertRaises(UserError):
            validated.action_reject()
        self.assertEqual(validated.state, "validated")

        rejected = self._create_voucher(customer_identification="R1")
        rejected.action_reject()
        with self.assertRaises(UserError):
            rejected.action_validate()
        with self.assertRaises(UserError):
            rejected.action_reject()
        self.assertEqual(rejected.state, "rejected")

    def test_unlink_allowed_when_new(self):
        voucher = self._create_voucher()
        voucher_id = voucher.id
        voucher.unlink()
        self.assertFalse(self.env["collection.voucher"].browse(voucher_id).exists())

    def test_unlink_blocked_when_not_new(self):
        voucher = self._create_voucher()
        voucher.action_validate()
        with self.assertRaises(UserError):
            voucher.unlink()
        self.assertTrue(voucher.exists())

    # --- 1.4 Payment lines / payment field contract ---

    def test_persist_type_specific_collection_fields(self):
        voucher = self._create_voucher()
        Payment = self.env["collection.voucher.line"]
        transfer = Payment.create(
            {
                "voucher_id": voucher.id,
                "document_type": "bank_transfer",
                "amount": 1500.50,
                "from_account": "ACC-FROM-1",
                "to_account": "ACC-TO-1",
                "voucher_number": "TRF-100",
                "voucher_date": date(2026, 3, 15),
            }
        )
        check = Payment.create(
            {
                "voucher_id": voucher.id,
                "document_type": "check",
                "amount": 200.00,
                "check_number": "CHK-9",
                "check_bank": "Banco Nación",
                "check_issue_date": date(2026, 1, 10),
                "check_payment_date": date(2026, 2, 10),
                "check_type": "deferred",
            }
        )
        deposit = Payment.create(
            {
                "voucher_id": voucher.id,
                "document_type": "cash_deposit",
                "amount": 50.25,
                "voucher_number": "CASH-1",
                "voucher_date": date(2026, 4, 1),
            }
        )

        self.assertEqual(transfer.document_type, "bank_transfer")
        self.assertAlmostEqual(transfer.amount, 1500.50, places=2)
        self.assertEqual(transfer.from_account, "ACC-FROM-1")
        self.assertEqual(transfer.to_account, "ACC-TO-1")
        self.assertEqual(transfer.voucher_number, "TRF-100")
        self.assertEqual(transfer.voucher_date, date(2026, 3, 15))

        self.assertEqual(check.document_type, "check")
        self.assertAlmostEqual(check.amount, 200.00, places=2)
        self.assertEqual(check.check_number, "CHK-9")
        self.assertEqual(check.check_bank, "Banco Nación")
        self.assertEqual(check.check_issue_date, date(2026, 1, 10))
        self.assertEqual(check.check_payment_date, date(2026, 2, 10))
        self.assertEqual(check.check_type, "deferred")

        self.assertEqual(deposit.document_type, "cash_deposit")
        self.assertAlmostEqual(deposit.amount, 50.25, places=2)
        self.assertEqual(deposit.voucher_number, "CASH-1")
        self.assertEqual(deposit.voucher_date, date(2026, 4, 1))

        self.assertEqual(len(voucher.payment_ids), 3)

    def test_unsupported_and_partial_payment_lines(self):
        voucher = self._create_voucher()
        Payment = self.env["collection.voucher.line"]
        unsupported = Payment.create(
            {
                "voucher_id": voucher.id,
                "document_type": "unsupported",
            }
        )
        partial = Payment.create(
            {
                "voucher_id": voucher.id,
                "document_type": "bank_transfer",
                "from_account": "ONLY-FROM",
            }
        )

        self.assertEqual(unsupported.document_type, "unsupported")
        self.assertFalse(unsupported.amount)
        self.assertFalse(unsupported.from_account)
        self.assertFalse(unsupported.check_number)

        self.assertEqual(partial.document_type, "bank_transfer")
        self.assertEqual(partial.from_account, "ONLY-FROM")
        self.assertFalse(partial.to_account)
        self.assertFalse(partial.amount)
        self.assertEqual(len(voucher.payment_ids), 2)

    def test_check_type_common_persists(self):
        """Triangulation: check_type common is a distinct selection path."""
        voucher = self._create_voucher()
        check = self.env["collection.voucher.line"].create(
            {
                "voucher_id": voucher.id,
                "document_type": "check",
                "check_type": "common",
                "check_number": "CHK-COMMON",
            }
        )
        self.assertEqual(check.check_type, "common")
        self.assertEqual(check.check_number, "CHK-COMMON")
