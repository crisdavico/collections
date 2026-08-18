# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date

from psycopg2 import IntegrityError

from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tests import TransactionCase
from odoo.tools import mute_logger


class TestCollectionSheet(TransactionCase):
    """RED/GREEN: collection.sheet sequence, frozen seller, open/closed lifecycle."""

    def _other_internal_seller(self):
        seller = self.env["res.users"].search(
            [("share", "=", False), ("id", "!=", self.env.uid)],
            order="id",
            limit=1,
        )
        self.assertTrue(
            seller,
            "Need a second internal user to prove seller is not create_uid",
        )
        return seller

    def _create_sheet(self, **extra):
        vals = {"seller_id": self.env.user.id, **extra}
        return self.env["collection.sheet"].create(vals)

    def _create_voucher(self, **extra):
        vals = {
            "customer_identification": "CUST-SHEET",
            "document_type": "unsupported",
            "seller_id": self.env.user.id,
        }
        vals.update(extra)
        return self.env["collection.voucher"].create(vals)

    def _sheet_count(self):
        return self.env["collection.sheet"].search_count([])

    def _assert_sheet_assign_rejected(self, voucher, sheet):
        with mute_logger("odoo.sql_db"):
            try:
                voucher.write({"sheet_id": sheet.id})
            except (UserError, ValidationError, IntegrityError):
                return
        self.fail("Assigning this voucher to the sheet must be rejected")

    def test_sequence_assigned_on_create(self):
        year = date.today().year
        sheet = self._create_sheet()
        self.assertRegex(
            sheet.name,
            rf"^CS/{year}/\d{{4}}$",
            "Sheet name must match CS/<year>/<padded number>",
        )
        self.assertEqual(sheet.state, "open")
        state_field = self.env["collection.sheet"]._fields["state"]
        state_keys = {key for key, _label in state_field.selection}
        self.assertEqual(state_keys, {"open", "closed"})

    def test_sequence_names_are_unique(self):
        first = self._create_sheet()
        second = self._create_sheet()
        self.assertNotEqual(first.name, second.name)
        self.assertRegex(first.name, r"^CS/\d{4}/\d{4}$")
        self.assertRegex(second.name, r"^CS/\d{4}/\d{4}$")
        self.assertEqual(first.state, "open")
        self.assertEqual(second.state, "open")
        self.assertEqual(first.seller_id, second.seller_id)

    def test_action_close_from_open(self):
        sheet = self._create_sheet()
        self.assertEqual(sheet.state, "open")
        sheet.action_close()
        self.assertEqual(sheet.state, "closed")

    def test_action_close_rejected_when_already_closed(self):
        sheet = self._create_sheet()
        sheet.action_close()
        with self.assertRaises(UserError):
            sheet.action_close()
        self.assertEqual(sheet.state, "closed")

    def test_action_reopen_from_closed(self):
        sheet = self._create_sheet()
        sheet.action_close()
        self.assertEqual(sheet.state, "closed")
        sheet.action_reopen()
        self.assertEqual(sheet.state, "open")

    def test_action_reopen_rejected_when_already_open(self):
        sheet = self._create_sheet()
        with self.assertRaises(UserError):
            sheet.action_reopen()
        self.assertEqual(sheet.state, "open")

    def test_raw_state_write_routes_to_close_and_reopen(self):
        """write({state}) without collection_sheet_audited_state must run Close/Reopen."""
        sheet = self._create_sheet()
        sheet.write({"state": "closed"})
        self.assertEqual(sheet.state, "closed")
        sheet.write({"state": "open"})
        self.assertEqual(sheet.state, "open")

    def test_raw_state_write_invalid_transition_rejected(self):
        """Intercepted write still enforces Close/Reopen preconditions."""
        sheet = self._create_sheet()
        with self.assertRaises(UserError):
            sheet.write({"state": "open"})
        self.assertEqual(sheet.state, "open")
        sheet.action_close()
        with self.assertRaises(UserError):
            sheet.write({"state": "closed"})
        self.assertEqual(sheet.state, "closed")

    def test_audited_state_write_allowed_with_context(self):
        """collection_sheet_audited_state allows the write used by Close/Reopen."""
        sheet = self._create_sheet()
        sheet.with_context(collection_sheet_audited_state=True).write(
            {"state": "closed"}
        )
        self.assertEqual(sheet.state, "closed")
        sheet.with_context(collection_sheet_audited_state=True).write({"state": "open"})
        self.assertEqual(sheet.state, "open")

    def test_create_without_seller_is_rejected(self):
        with mute_logger("odoo.sql_db"):
            try:
                self.env["collection.sheet"].create({})
            except (IntegrityError, ValidationError, UserError):
                return
        self.fail("Creating a sheet without seller_id must be rejected")

    def test_seller_is_not_copied_from_create_uid(self):
        seller = self._other_internal_seller()
        sheet = self._create_sheet(seller_id=seller.id)
        self.assertEqual(sheet.seller_id, seller)
        self.assertNotEqual(sheet.seller_id, sheet.create_uid)
        self.assertEqual(sheet.create_uid, self.env.user)

    def test_post_create_seller_write_is_rejected(self):
        sheet = self._create_sheet()
        original = sheet.seller_id
        other = self._other_internal_seller()
        with self.assertRaises(UserError):
            sheet.write({"seller_id": other.id})
        self.assertEqual(sheet.seller_id, original)

    def test_post_create_same_seller_write_is_rejected(self):
        sheet = self._create_sheet()
        with self.assertRaises(UserError):
            sheet.write({"seller_id": sheet.seller_id.id})
        self.assertEqual(sheet.seller_id, self.env.user)

    def test_action_creates_sheet_for_unassigned_same_seller_any_state(self):
        pending = self._create_voucher(customer_identification="CUST-ACT-P")
        approved = self._create_voucher(customer_identification="CUST-ACT-A")
        approved.action_approve()
        before = self._sheet_count()
        action = (pending | approved).action_create_collection_sheet()
        self.assertEqual(self._sheet_count(), before + 1)
        sheet = self.env["collection.sheet"].browse(action["res_id"])
        self.assertEqual(sheet.seller_id, self.env.user)
        self.assertEqual(set(sheet.voucher_ids.ids), {pending.id, approved.id})
        self.assertEqual(pending.sheet_id, sheet)
        self.assertEqual(approved.sheet_id, sheet)
        self.assertEqual(action["res_model"], "collection.sheet")

    def test_action_rejects_ineligible_selection(self):
        other = self._other_internal_seller()
        mixed_a = self._create_voucher(customer_identification="CUST-MIX-A")
        mixed_b = self._create_voucher(
            customer_identification="CUST-MIX-B", seller_id=other.id
        )
        assigned = self._create_voucher(customer_identification="CUST-ASG")
        sheet = self._create_sheet()
        assigned.sheet_id = sheet.id
        before = self._sheet_count()
        with self.assertRaises(UserError):
            (mixed_a | mixed_b).action_create_collection_sheet()
        with self.assertRaises(UserError):
            assigned.action_create_collection_sheet()
        with self.assertRaises(UserError):
            self.env["collection.voucher"].browse().action_create_collection_sheet()
        self.assertEqual(self._sheet_count(), before)

    def test_action_rejects_null_seller_selection(self):
        voucher = self._create_voucher(
            customer_identification="CUST-NULL-S", seller_id=False
        )
        self.assertFalse(voucher.seller_id)
        before = self._sheet_count()
        with self.assertRaises(UserError):
            voucher.action_create_collection_sheet()
        self.assertEqual(self._sheet_count(), before)
        self.assertFalse(voucher.sheet_id)

    def test_mixed_or_null_seller_assign_rejected(self):
        sheet = self._create_sheet()
        other = self._other_internal_seller()
        mixed = self._create_voucher(
            customer_identification="CUST-ASN-MIX", seller_id=other.id
        )
        null = self._create_voucher(
            customer_identification="CUST-ASN-NULL", seller_id=False
        )
        self._assert_sheet_assign_rejected(mixed, sheet)
        self._assert_sheet_assign_rejected(null, sheet)

    def test_reassign_moves_voucher_to_sheet_b_only(self):
        sheet_a = self._create_sheet()
        sheet_b = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-REASG", sheet_id=sheet_a.id
        )
        voucher.write({"sheet_id": sheet_b.id})
        self.assertEqual(voucher.sheet_id, sheet_b)
        self.assertNotIn(voucher, sheet_a.voucher_ids)
        self.assertIn(voucher, sheet_b.voucher_ids)

    def test_empty_sheet_dates_false_and_no_received_date(self):
        sheet = self._create_sheet()
        self.assertFalse(sheet.date_from)
        self.assertFalse(sheet.date_to)
        self.assertNotIn("received_date", self.env["collection.sheet"]._fields)
        self.assertNotIn("received_date", self.env["collection.voucher"]._fields)

    def test_dates_from_utc_member_create_date(self):
        first = self._create_voucher(customer_identification="CUST-DT-1")
        second = self._create_voucher(customer_identification="CUST-DT-2")
        self.env.cr.execute(
            "UPDATE collection_voucher SET create_date = %s WHERE id = %s",
            ["2026-08-16 23:30:00", first.id],
        )
        self.env.cr.execute(
            "UPDATE collection_voucher SET create_date = %s WHERE id = %s",
            ["2026-08-17 00:30:00", second.id],
        )
        self.env.invalidate_all()
        sheet = self._create_sheet()
        (first | second).write({"sheet_id": sheet.id})
        self.assertEqual(sheet.date_from, date(2026, 8, 16))
        self.assertEqual(sheet.date_to, date(2026, 8, 17))

    def test_unlink_sheet_unassigns_vouchers(self):
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-UNL", sheet_id=sheet.id
        )
        voucher_id = voucher.id
        sheet.unlink()
        leftover = self.env["collection.voucher"].browse(voucher_id)
        self.assertTrue(leftover.exists())
        self.assertFalse(leftover.sheet_id)

    def test_delete_command_unassigns_without_destroying_voucher(self):
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-DELCMD", sheet_id=sheet.id
        )
        sheet.write({"voucher_ids": [Command.delete(voucher.id)]})
        self.assertTrue(voucher.exists())
        self.assertFalse(voucher.sheet_id)
        self.assertFalse(sheet.voucher_ids)

    def test_create_sheet_action_is_list_bound_server_action(self):
        action = self.env.ref("collection.action_create_collection_sheet")
        self.assertEqual(action.type, "ir.actions.server")
        self.assertEqual(action.binding_view_types, "list")
        self.assertEqual(action.binding_model_id.model, "collection.voucher")

    def test_action_open_document_review_returns_client_action_with_sheet_id(self):
        """Saved sheet + flag ON must open Document Review with that sheet_id."""
        self.env.company.write({"document_review_enabled": True})
        sheet = self._create_sheet()
        self.assertIsInstance(sheet.id, int)
        self.assertGreater(sheet.id, 0)
        action = sheet.action_open_document_review()
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "collection.document_review")
        self.assertEqual(action["params"]["sheet_id"], sheet.id)

    def test_action_open_document_review_params_match_each_saved_sheet(self):
        """Triangulation: params.sheet_id is the invoked sheet, not a constant."""
        self.env.company.write({"document_review_enabled": True})
        sheet_a = self._create_sheet()
        sheet_b = self._create_sheet()
        self.assertNotEqual(sheet_a.id, sheet_b.id)
        action_a = sheet_a.action_open_document_review()
        action_b = sheet_b.action_open_document_review()
        self.assertEqual(action_a["params"]["sheet_id"], sheet_a.id)
        self.assertEqual(action_b["params"]["sheet_id"], sheet_b.id)
        self.assertEqual(action_a["tag"], "collection.document_review")
        self.assertEqual(action_b["tag"], "collection.document_review")

    def test_action_open_document_review_refused_when_flag_off(self):
        """Saved sheet + flag OFF must raise the voucher Document Review UserError."""
        self.env.company.write({"document_review_enabled": False})
        sheet = self._create_sheet()
        with self.assertRaises(UserError) as error:
            sheet.action_open_document_review()
        self.assertEqual(str(error.exception), "Document Review is not enabled.")

    def test_action_open_document_review_refused_on_new_id(self):
        """Unsaved .new() records (NewId) must not open Document Review."""
        self.env.company.write({"document_review_enabled": True})
        unsaved = self.env["collection.sheet"].new({"seller_id": self.env.user.id})
        self.assertFalse(isinstance(unsaved.id, int))
        self.assertFalse(unsaved.id)
        with self.assertRaises(UserError):
            unsaved.action_open_document_review()

    def test_document_review_enabled_helper_is_non_stored_and_follows_flag(self):
        """Non-stored helper mirrors company._document_review_enabled() (no DDL)."""
        field = self.env["collection.sheet"]._fields["document_review_enabled"]
        self.assertTrue(field.compute)
        self.assertFalse(field.store)
        self.env.company.write({"document_review_enabled": True})
        on_sheet = self._create_sheet()
        self.assertTrue(on_sheet.document_review_enabled)
        self.env.company.write({"document_review_enabled": False})
        off_sheet = self._create_sheet()
        self.assertFalse(off_sheet.document_review_enabled)
