# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from base64 import b64decode
from datetime import date
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from psycopg2 import IntegrityError

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase
from odoo.tools import mute_logger

from .test_collection_payment import PDF_B64, PNG_B64, post_voucher_proof


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

    # --- Voucher seller_id (nullable, no backfill) ---

    def test_orm_create_without_seller_stays_null(self):
        """ORM create without seller_id MUST persist a null seller (no backfill)."""
        fields_map = self.env["collection.voucher"]._fields
        self.assertIn("seller_id", fields_map)
        seller_field = fields_map["seller_id"]
        self.assertEqual(seller_field.comodel_name, "res.users")
        self.assertFalse(
            seller_field.required,
            "ORM seller_id must stay nullable (no NOT NULL / no backfill)",
        )
        self.assertEqual(seller_field.domain, [("share", "=", False)])

        voucher = self._create_voucher(customer_identification="CUST-NO-SELLER")
        self.assertFalse(
            voucher.seller_id,
            "ORM create without seller_id must leave seller null",
        )

    def test_orm_write_does_not_backfill_null_seller(self):
        """Triangulation: explicit seller persists; write does not backfill null."""
        seller = self.env.user
        with_seller = self._create_voucher(
            customer_identification="CUST-WITH-SELLER",
            seller_id=seller.id,
        )
        self.assertEqual(with_seller.seller_id, seller)

        legacy = self._create_voucher(customer_identification="CUST-LEGACY-NULL")
        self.assertFalse(legacy.seller_id)
        legacy.write({"amount": 10.0})
        self.assertFalse(
            legacy.seller_id,
            "Saving a null-seller voucher must not backfill seller_id",
        )
        self.assertEqual(legacy.amount, 10.0)

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
        """state=pending without replacing designated proof must refuse reopen."""
        voucher = self._create_voucher()
        voucher.action_approve()
        with self.assertRaises(UserError):
            voucher.write({"state": "pending"})
        self.assertEqual(voucher.state, "approved")
        self.assertEqual(voucher.reviewed_by, self.env.user)

    def test_replace_main_resets_pending_clears_audit_and_rotation(self):
        """Replacing message_main_attachment_id MUST reopen review and reset rotation."""
        voucher = self._create_voucher(
            customer_identification="CUST-ATT-RST",
            document_id="DOC-ATT-RST",
        )
        first = post_voucher_proof(voucher, "old.png", PNG_B64)
        voucher.write({"attachment_rotation": 90})
        voucher.action_approve()
        self.assertEqual(voucher.state, "approved")
        self.assertTrue(voucher.reviewed_by)
        replacement = self.env["ir.attachment"].create(
            {
                "name": "new.pdf",
                "raw": b64decode(PDF_B64),
                "res_model": "collection.voucher",
                "res_id": voucher.id,
            }
        )
        voucher.write({"message_main_attachment_id": replacement.id})
        self.assertEqual(voucher.state, "pending")
        self.assertFalse(voucher.reviewed_by)
        self.assertFalse(voucher.reviewed_at)
        self.assertEqual(voucher.attachment_rotation, 0)
        self.assertEqual(voucher.message_main_attachment_id, replacement)
        self.assertNotEqual(voucher.message_main_attachment_id, first)

    def test_extra_chatter_does_not_reset_review_or_rotation(self):
        """Extra chatter files MUST NOT reset review, audit, or rotation."""
        voucher = self._create_voucher(customer_identification="CUST-ATT-EXTRA")
        proof = post_voucher_proof(voucher, "keep.png", PNG_B64)
        voucher.write({"attachment_rotation": 180})
        voucher.action_reject()
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
        self.assertEqual(voucher.state, "rejected")
        self.assertEqual(voucher.reviewed_by, self.env.user)
        self.assertTrue(voucher.reviewed_at)
        self.assertEqual(voucher.attachment_rotation, 180)
        self.assertEqual(voucher.message_main_attachment_id, proof)

    def test_clear_main_resets_rotation_keeps_decided(self):
        """Clearing designated proof MUST reset rotation and MUST NOT reopen."""
        voucher = self._create_voucher(customer_identification="CUST-ATT-CLR")
        post_voucher_proof(voucher, "clear-me.png", PNG_B64)
        voucher.write({"attachment_rotation": 270})
        voucher.action_approve()
        voucher.write({"message_main_attachment_id": False})
        self.assertEqual(voucher.state, "approved")
        self.assertEqual(voucher.reviewed_by, self.env.user)
        self.assertEqual(voucher.attachment_rotation, 0)
        self.assertFalse(voucher.message_main_attachment_id)

    def test_omit_proof_remains_valid(self):
        """Omit/empty designated proof MUST remain valid on create."""
        voucher = self._create_voucher(customer_identification="CUST-ATT-OMIT")
        self.assertTrue(voucher.id)
        self.assertFalse(voucher.message_main_attachment_id)

    def test_invalid_main_attachment_raises_user_error(self):
        """Setting designated proof to a non-image/non-PDF MUST raise UserError."""
        voucher = self._create_voucher(customer_identification="CUST-ATT-BAD")
        extra = self.env["ir.attachment"].create(
            {
                "name": "notes.txt",
                "raw": b"hello world",
                "res_model": "collection.voucher",
                "res_id": voucher.id,
            }
        )
        with self.assertRaises(UserError):
            voucher.write({"message_main_attachment_id": extra.id})
        self.assertFalse(voucher.message_main_attachment_id)

    def test_assigned_without_seller_fails(self):
        """Assigned voucher MUST keep a non-null seller."""
        sheet = self.env["collection.sheet"].create({"seller_id": self.env.user.id})
        voucher = self._create_voucher(customer_identification="CUST-SHEET-NO-SELLER")
        self.assertFalse(voucher.seller_id)
        with mute_logger("odoo.sql_db"):
            try:
                voucher.write({"sheet_id": sheet.id})
            except (UserError, ValidationError, IntegrityError):
                return
        self.fail("Assigning a seller-less voucher to a sheet must be rejected")

    # --- Chatter designated proof ---

    def _inherit_names(self):
        inherit = self.env["collection.voucher"]._inherit
        if isinstance(inherit, str):
            return [inherit]
        return list(inherit)

    def test_proof_is_message_main_attachment_id(self):
        """Designated proof MUST be message_main_attachment_id, not Binary fields."""
        fields_map = self.env["collection.voucher"]._fields
        self.assertIn("message_main_attachment_id", fields_map)
        self.assertNotIn("attachment", fields_map)
        self.assertNotIn("attachment_filename", fields_map)
        self.assertIn("mail.thread.main.attachment", self._inherit_names())
        voucher = self._create_voucher(customer_identification="CUST-PROOF-MAIN")
        proof = post_voucher_proof(voucher, "proof.png", PNG_B64)
        self.assertEqual(voucher.message_main_attachment_id, proof)
        self.assertEqual(proof.name, "proof.png")
        self.assertFalse(proof.res_field)

    def test_picker_promotes_pdf_when_main_empty(self):
        """Triangulation: a valid PDF chatter file MUST become designated proof."""
        voucher = self._create_voucher(customer_identification="CUST-PROOF-PDF")
        proof = post_voucher_proof(voucher, "receipt.pdf", PDF_B64)
        self.assertEqual(voucher.message_main_attachment_id, proof)
        self.assertEqual(proof.name, "receipt.pdf")
        self.assertTrue(
            (proof.mimetype or "").startswith("application/pdf")
            or proof.mimetype == "application/pdf"
        )

    def test_picker_force_cannot_promote_non_image_pdf(self):
        """MIME picker MUST refuse non-image/non-PDF even when force=True."""
        voucher = self._create_voucher(customer_identification="CUST-PROOF-FORCE")
        extra = self.env["ir.attachment"].create(
            {
                "name": "notes.txt",
                "raw": b"hello world",
                "res_model": "collection.voucher",
                "res_id": voucher.id,
            }
        )
        voucher._message_set_main_attachment_id(extra, force=True)
        voucher.invalidate_recordset()
        self.assertFalse(voucher.message_main_attachment_id)


def _load_collection_migrate(filename):
    path = (
        Path(__file__).resolve().parents[1] / "migrations" / "19.0.1.13.0" / filename
    )
    spec = spec_from_file_location(filename, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestCollectionVoucherAttachmentMigrate(TransactionCase):
    """RED/GREEN: Binary field attachments migrate onto chatter designated proof."""

    def _insert_field_attachment(self, voucher, name, datas_b64, filename=None):
        attachment = self.env["ir.attachment"].create(
            {
                "name": name,
                "raw": b64decode(datas_b64),
                "res_model": "collection.voucher",
                "res_id": voucher.id,
                "res_field": "attachment",
            }
        )
        if filename is not None and "attachment_filename" in voucher._fields:
            self.env.cr.execute(
                """
                UPDATE collection_voucher
                   SET attachment_filename = %s
                 WHERE id = %s
                """,
                (filename or None, voucher.id),
            )
        elif filename is not None:
            self.env.cr.execute(
                """
                SELECT 1
                  FROM information_schema.columns
                 WHERE table_name = 'collection_voucher'
                   AND column_name = 'attachment_filename'
                """
            )
            if self.env.cr.fetchone():
                self.env.cr.execute(
                    """
                    UPDATE collection_voucher
                       SET attachment_filename = %s
                     WHERE id = %s
                    """,
                    (filename or None, voucher.id),
                )
        return attachment

    def _run_migrate(self):
        _load_collection_migrate("pre-migrate.py").migrate(self.env.cr, "19.0.1.12.0")
        _load_collection_migrate("post-migrate.py").migrate(self.env.cr, "19.0.1.12.0")
        self.env.invalidate_all()

    def test_binary_field_attachment_migrates_to_chatter_main(self):
        voucher = self.env["collection.voucher"].create(
            {
                "customer_identification": "CUST-MIG-MAIN",
                "document_type": "bank_transfer",
            }
        )
        attachment = self._insert_field_attachment(
            voucher, "attachment", PNG_B64, filename="migrated.png"
        )
        self._run_migrate()
        attachment.invalidate_recordset()
        voucher.invalidate_recordset()
        self.assertFalse(attachment.res_field)
        self.assertEqual(attachment.name, "migrated.png")
        self.assertEqual(voucher.message_main_attachment_id, attachment)
        self.assertTrue(
            voucher.message_ids.filtered(
                lambda message: attachment in message.attachment_ids
            )
        )
        leftover = self.env["ir.attachment"].search(
            [
                ("res_model", "=", "collection.voucher"),
                ("res_id", "=", voucher.id),
                ("res_field", "=", "attachment"),
            ]
        )
        self.assertFalse(leftover)

    def test_empty_filename_falls_back_to_proof_bin(self):
        """Triangulation: empty attachment_filename MUST become proof.bin."""
        voucher = self.env["collection.voucher"].create(
            {
                "customer_identification": "CUST-MIG-BIN",
                "document_type": "cash_deposit",
            }
        )
        attachment = self._insert_field_attachment(
            voucher, "attachment", PDF_B64, filename=""
        )
        self._run_migrate()
        attachment.invalidate_recordset()
        voucher.invalidate_recordset()
        self.assertEqual(attachment.name, "proof.bin")
        self.assertEqual(voucher.message_main_attachment_id, attachment)
        self.assertFalse(attachment.res_field)
