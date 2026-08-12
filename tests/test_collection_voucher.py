# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date

from psycopg2 import IntegrityError

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase
from odoo.tools import mute_logger

from .test_collection_payment import PDF_B64, PNG_B64


class TestCollectionVoucher(TransactionCase):
    """RED/GREEN tests for standalone collection.voucher lifecycle."""

    def _create_voucher(self, **extra):
        vals = {
            "customer_identification": "CUST-001",
            "document_type": "bank_transfer",
        }
        vals.update(extra)
        return self.env["collection.voucher"].create(vals)

    # --- Sequence naming ---

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

    # --- 1.1 Defaults and required fields ---

    def test_defaults_on_create(self):
        voucher = self._create_voucher()
        fields_map = self.env["collection.voucher"]._fields
        self.assertNotIn(
            "received_date",
            fields_map,
            "received_date must be removed from the voucher model",
        )
        self.assertNotIn(
            "payment_ids",
            fields_map,
            "payment_ids must be dropped; one voucher is one payment",
        )
        self.assertTrue(
            voucher.create_date,
            "create_date must be set automatically by the ORM",
        )
        self.assertEqual(voucher.state, "pending")
        state_keys = {key for key, _label in fields_map["state"].selection}
        self.assertEqual(state_keys, {"pending", "approved", "rejected"})
        self.assertEqual(
            voucher.currency_id,
            self.env.company.currency_id,
            "Currency must default to company currency",
        )

    def test_customer_identification_required(self):
        # Odoo 19 enforces required Char via DB NOT NULL on create({})
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            self.env["collection.voucher"].create({"document_type": "unsupported"})

    def test_received_date_field_absent(self):
        """Triangulation: field must not exist on the model registry."""
        self.assertNotIn("received_date", self.env["collection.voucher"]._fields)

    def test_create_rejects_received_date_vals(self):
        """Create vals must not accept received_date after the field is dropped."""
        with self.assertRaises(ValueError):
            self.env["collection.voucher"].create(
                {
                    "customer_identification": "CUST-NO-RECV",
                    "document_type": "unsupported",
                    "received_date": fields.Date.today(),
                }
            )

    def test_create_date_not_overridable(self):
        """Caller-supplied create_date must not stick; ORM owns registration time."""
        forged = fields.Datetime.to_datetime("2020-01-15 12:00:00")
        voucher = self.env["collection.voucher"].create(
            {
                "customer_identification": "CUST-CREATE-DATE",
                "document_type": "unsupported",
                "create_date": forged,
            }
        )
        self.assertNotEqual(
            fields.Datetime.to_datetime(voucher.create_date),
            forged,
            "create_date must not be caller-overridable",
        )
        self.assertTrue(voucher.create_date)

    # --- 1.3 Payment field contract on the voucher ---

    def test_persist_type_specific_collection_fields(self):
        transfer = self._create_voucher(
            customer_identification="CUST-TRF",
            document_type="bank_transfer",
            amount=1500.50,
            from_account="ACC-FROM-1",
            to_account="ACC-TO-1",
            voucher_number="TRF-100",
            voucher_date=date(2026, 3, 15),
        )
        check = self._create_voucher(
            customer_identification="CUST-CHK",
            document_type="check",
            amount=200.00,
            check_number="CHK-9",
            check_bank="Banco Nación",
            check_issue_date=date(2026, 1, 10),
            check_payment_date=date(2026, 2, 10),
            check_type="deferred",
        )
        deposit = self._create_voucher(
            customer_identification="CUST-CASH",
            document_type="cash_deposit",
            amount=50.25,
            voucher_number="CASH-1",
            voucher_date=date(2026, 4, 1),
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

    def test_unsupported_and_partial_payment_fields(self):
        unsupported = self._create_voucher(
            customer_identification="CUST-UNSUP",
            document_type="unsupported",
        )
        partial = self._create_voucher(
            customer_identification="CUST-PARTIAL",
            document_type="bank_transfer",
            from_account="ONLY-FROM",
        )

        self.assertEqual(unsupported.document_type, "unsupported")
        self.assertFalse(unsupported.amount)
        self.assertFalse(unsupported.from_account)
        self.assertFalse(unsupported.check_number)

        self.assertEqual(partial.document_type, "bank_transfer")
        self.assertEqual(partial.from_account, "ONLY-FROM")
        self.assertFalse(partial.to_account)
        self.assertFalse(partial.amount)

    def test_check_type_common_persists(self):
        """Triangulation: check_type common is a distinct selection path."""
        check = self._create_voucher(
            customer_identification="CUST-CHK-COMMON",
            document_type="check",
            check_type="common",
            check_number="CHK-COMMON",
        )
        self.assertEqual(check.check_type, "common")
        self.assertEqual(check.check_number, "CHK-COMMON")

    # --- 1.4 / 1.5 Approve, reject, unlink ---

    def test_action_approve_from_pending_records_reviewer(self):
        voucher = self._create_voucher()
        self.assertEqual(voucher.state, "pending")
        self.assertFalse(voucher.reviewed_by)
        self.assertFalse(voucher.reviewed_at)
        voucher.action_approve()
        self.assertEqual(voucher.state, "approved")
        self.assertEqual(voucher.reviewed_by, self.env.user)
        self.assertTrue(voucher.reviewed_at)

    def test_action_reject_from_pending_records_reviewer(self):
        voucher = self._create_voucher(customer_identification="CUST-REJ")
        voucher.action_reject()
        self.assertEqual(voucher.state, "rejected")
        self.assertEqual(voucher.reviewed_by, self.env.user)
        self.assertTrue(voucher.reviewed_at)

    def test_terminal_states_block_approve_and_reject(self):
        approved = self._create_voucher(customer_identification="V1")
        approved.action_approve()
        with self.assertRaises(UserError):
            approved.action_approve()
        with self.assertRaises(UserError):
            approved.action_reject()
        self.assertEqual(approved.state, "approved")

        rejected = self._create_voucher(customer_identification="R1")
        rejected.action_reject()
        with self.assertRaises(UserError):
            rejected.action_approve()
        with self.assertRaises(UserError):
            rejected.action_reject()
        self.assertEqual(rejected.state, "rejected")

    def test_unlink_allowed_when_pending(self):
        voucher = self._create_voucher()
        voucher_id = voucher.id
        voucher.unlink()
        self.assertFalse(self.env["collection.voucher"].browse(voucher_id).exists())

    def test_unlink_blocked_when_not_pending(self):
        voucher = self._create_voucher()
        voucher.action_approve()
        with self.assertRaises(UserError):
            voucher.unlink()
        self.assertTrue(voucher.exists())

        rejected = self._create_voucher(customer_identification="CUST-UNL-REJ")
        rejected.action_reject()
        with self.assertRaises(UserError):
            rejected.unlink()
        self.assertTrue(rejected.exists())

    def test_action_validate_removed(self):
        """Aggregate header validate must not exist on the standalone voucher."""
        voucher = self._create_voucher()
        self.assertFalse(hasattr(voucher, "action_validate"))

    # --- 1.6 / 1.7 Audited write() / kanban drag ---

    def test_kanban_drag_writes_state(self):
        """write({state}) without collection_audited_state must run approve/reject."""
        voucher = self._create_voucher()
        voucher.write({"state": "approved"})
        self.assertEqual(voucher.state, "approved")
        self.assertEqual(voucher.reviewed_by, self.env.user)
        self.assertTrue(voucher.reviewed_at)

        other = self._create_voucher(customer_identification="CUST-DRAG-REJ")
        other.write({"state": "rejected"})
        self.assertEqual(other.state, "rejected")
        self.assertEqual(other.reviewed_by, self.env.user)
        self.assertTrue(other.reviewed_at)

    def test_kanban_reopen_without_attachment_refused(self):
        """state=pending without attachment in vals must refuse reopen."""
        voucher = self._create_voucher()
        voucher.action_approve()
        with self.assertRaises(UserError):
            voucher.write({"state": "pending"})
        self.assertEqual(voucher.state, "approved")
        self.assertEqual(voucher.reviewed_by, self.env.user)

    def test_attachment_replace_resets_pending_and_clears_audit(self):
        """Replacing Binary content must reopen review and clear audit."""
        voucher = self._create_voucher(
            customer_identification="CUST-ATT-RST",
            document_id="DOC-ATT-RST",
            attachment=PNG_B64,
            attachment_filename="old.png",
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
