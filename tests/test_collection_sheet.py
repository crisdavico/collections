# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date

from psycopg2 import IntegrityError

from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tests import TransactionCase
from odoo.tools import mute_logger

from .test_collection_payment import (
    create_internal_seller,
    dummy_customer_partner,
    ensure_enabled_seller,
)


class TestCollectionSheet(TransactionCase):
    """RED/GREEN: collection.sheet sequence, frozen seller, open/closed lifecycle."""

    def _other_internal_seller(self):
        return create_internal_seller(self.env, f"other_{self._testMethodName}")

    def _ensure_enabled_seller(self, seller=None):
        seller = seller or self.env.ref("base.user_admin")
        company = self.env.company
        if seller not in company.enabled_seller_ids:
            company.write({"enabled_seller_ids": [Command.link(seller.id)]})
            if seller not in company.enabled_seller_ids:
                self.env.cr.execute(
                    """
                    INSERT INTO res_company_collection_enabled_seller_rel
                        (company_id, user_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (company.id, seller.id),
                )
                company.invalidate_recordset(["enabled_seller_ids"])
        return seller

    def _seller(self):
        return self._ensure_enabled_seller()

    def _create_sheet(self, **extra):
        seller_id = extra.get("seller_id", self._seller().id)
        self._ensure_enabled_seller(self.env["res.users"].browse(seller_id))
        vals = {"seller_id": seller_id, **extra}
        return self.env["collection.sheet"].create(vals)

    def _create_voucher(self, customer=None, **extra):
        null_seller = extra.get("seller_id") is False
        if null_seller:
            extra = {key: value for key, value in extra.items() if key != "seller_id"}
            if not extra.get("sheet_id"):
                existing_open = self.env["collection.sheet"].search(
                    [
                        ("seller_id", "=", self._seller().id),
                        ("state", "=", "open"),
                    ],
                    limit=1,
                )
                if existing_open:
                    extra["sheet_id"] = existing_open.id
        seller_id = extra.get("seller_id", self._seller().id)
        if seller_id:
            self._ensure_enabled_seller(self.env["res.users"].browse(seller_id))
        partner = dummy_customer_partner(
            self.env, customer=customer, extra=extra, default="CUST-SHEET"
        )
        vals = {
            "partner_id": partner.id,
            "document_type": "unsupported",
            "seller_id": seller_id or self._seller().id,
        }
        vals.update(extra)
        before_sheets = self.env["collection.sheet"].browse(
            self.env["collection.sheet"].search([]).ids
        )
        voucher = self.env["collection.voucher"].create(vals)
        if null_seller:
            leftover_sheet = voucher.sheet_id
            self.env.cr.execute(
                """
                UPDATE collection_voucher
                   SET seller_id = NULL, sheet_id = NULL
                 WHERE id = %s
                """,
                (voucher.id,),
            )
            voucher.invalidate_recordset(["seller_id", "sheet_id"])
            leftover_sheet.invalidate_recordset(["voucher_ids"])
            if (
                leftover_sheet
                and leftover_sheet not in before_sheets
                and not leftover_sheet.voucher_ids
            ):
                leftover_sheet.unlink()
        return voucher

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
            rf"^CS/{year}/\d{{4,}}$",
            "Sheet name must match CS/<year>/<padded number>",
        )
        self.assertEqual(sheet.state, "open")
        state_field = self.env["collection.sheet"]._fields["state"]
        state_keys = {key for key, _label in state_field.selection}
        self.assertEqual(state_keys, {"open", "closed"})

    def test_sequence_names_are_unique(self):
        first = self._create_sheet()
        first.action_close()
        second = self._create_sheet()
        self.assertNotEqual(first.name, second.name)
        self.assertRegex(first.name, r"^CS/\d{4}/\d{4,}$")
        self.assertRegex(second.name, r"^CS/\d{4}/\d{4,}$")
        self.assertEqual(first.state, "closed")
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
        """write({state}) without audited-state context runs Close/Reopen."""
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

    def test_create_second_open_rejected(self):
        first = self._create_sheet()
        before = self._sheet_count()
        with self.assertRaises(UserError):
            self._create_sheet()
        self.assertEqual(self._sheet_count(), before)
        self.assertEqual(first.state, "open")
        other = self._other_internal_seller()
        other_sheet = self._create_sheet(seller_id=other.id)
        self.assertEqual(other_sheet.state, "open")
        self.assertEqual(other_sheet.seller_id, other)

    def test_reopen_rejected_if_another_open_exists(self):
        first = self._create_sheet()
        closed = self._create_sheet(state="closed")
        with self.assertRaises(UserError):
            closed.action_reopen()
        self.assertEqual(closed.state, "closed")
        self.assertEqual(first.state, "open")

    def test_leftover_multiple_opens_still_closeable(self):
        first = self._create_sheet()
        leftover = self._create_sheet(state="closed")
        leftover.with_context(collection_sheet_audited_state=True).write(
            {"state": "open"}
        )
        self.assertEqual(first.state, "open")
        self.assertEqual(leftover.state, "open")
        leftover.action_close()
        self.assertEqual(leftover.state, "closed")
        self.assertEqual(first.state, "open")
        first.action_close()
        self.assertEqual(first.state, "closed")

    def test_leftover_multiple_opens_reject_new_ops(self):
        first = self._create_sheet()
        leftover = self._create_sheet(state="closed")
        leftover.with_context(collection_sheet_audited_state=True).write(
            {"state": "open"}
        )
        before = self._sheet_count()
        with self.assertRaises(UserError):
            self._create_sheet()
        closed = self._create_sheet(state="closed")
        with self.assertRaises(UserError):
            closed.action_reopen()
        self.assertEqual(closed.state, "closed")
        voucher = self._create_voucher(
            customer_identification="CUST-LEFT-ACT", seller_id=False
        )
        voucher.write({"seller_id": self._seller().id})
        with self.assertRaises(UserError):
            voucher.action_create_collection_sheet()
        self.assertEqual(self._sheet_count(), before + 1)
        self.assertFalse(voucher.sheet_id)
        self.assertEqual(first.state, "open")
        self.assertEqual(leftover.state, "open")

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
        self.assertEqual(sheet.seller_id, self._seller())

    def test_action_creates_sheet_for_unassigned_same_seller_any_state(self):
        pending = self._create_voucher(
            customer_identification="CUST-ACT-P", seller_id=False
        )
        approved = self._create_voucher(
            customer_identification="CUST-ACT-A", seller_id=False
        )
        pending.write({"seller_id": self._seller().id})
        approved.write({"seller_id": self._seller().id})
        approved.action_approve()
        before = self._sheet_count()
        action = (pending | approved).action_create_collection_sheet()
        self.assertEqual(self._sheet_count(), before + 1)
        sheet = self.env["collection.sheet"].browse(action["res_id"])
        self.assertEqual(sheet.seller_id, self._seller())
        self.assertEqual(set(sheet.voucher_ids.ids), {pending.id, approved.id})
        self.assertEqual(pending.sheet_id, sheet)
        self.assertEqual(approved.sheet_id, sheet)
        self.assertEqual(action["res_model"], "collection.sheet")

    def test_action_rejects_ineligible_selection(self):
        other = self._other_internal_seller()
        self._ensure_enabled_seller(other)
        mixed_a = self._create_voucher(
            customer_identification="CUST-MIX-A", seller_id=False
        )
        mixed_b = self._create_voucher(
            customer_identification="CUST-MIX-B", seller_id=False
        )
        assigned = self._create_voucher(
            customer_identification="CUST-ASG", seller_id=False
        )
        mixed_a.write({"seller_id": self._seller().id})
        mixed_b.write({"seller_id": other.id})
        assigned.write({"seller_id": self._seller().id})
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

    def test_action_rejected_when_open_sheet_exists(self):
        open_sheet = self._create_sheet()
        pending = self._create_voucher(
            customer_identification="CUST-ACT-OPEN-P", seller_id=False
        )
        approved = self._create_voucher(
            customer_identification="CUST-ACT-OPEN-A", seller_id=False
        )
        pending.write({"seller_id": self._seller().id})
        approved.write({"seller_id": self._seller().id})
        approved.action_approve()
        before = self._sheet_count()
        with self.assertRaises(UserError):
            (pending | approved).action_create_collection_sheet()
        self.assertEqual(self._sheet_count(), before)
        self.assertFalse(pending.sheet_id)
        self.assertFalse(approved.sheet_id)
        self.assertEqual(open_sheet.state, "open")

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
        voucher = self._create_voucher(
            customer_identification="CUST-REASG", sheet_id=sheet_a.id
        )
        voucher.write({"sheet_id": False})
        sheet_a.action_close()
        sheet_b = self._create_sheet()
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
        first = self._create_voucher(
            customer_identification="CUST-DT-1", seller_id=False
        )
        second = self._create_voucher(
            customer_identification="CUST-DT-2", seller_id=False
        )
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
        (first | second).write({"seller_id": self._seller().id, "sheet_id": sheet.id})
        self.assertEqual(sheet.date_from, date(2026, 8, 16))
        self.assertEqual(sheet.date_to, date(2026, 8, 17))

    def test_unlink_sheet_unassigns_vouchers(self):
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-UNL", sheet_id=sheet.id
        )
        self.assertFalse(sheet.allocation_ids)
        voucher_id = voucher.id
        sheet.unlink()
        leftover = self.env["collection.voucher"].browse(voucher_id)
        self.assertTrue(leftover.exists())
        self.assertFalse(leftover.sheet_id)

    def test_unlink_closed_sheet_unassigns_vouchers(self):
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-UNL-CL", sheet_id=sheet.id
        )
        self.assertFalse(sheet.allocation_ids)
        sheet.action_close()
        voucher_id = voucher.id
        sheet.unlink()
        leftover = self.env["collection.voucher"].browse(voucher_id)
        self.assertTrue(leftover.exists())
        self.assertFalse(leftover.sheet_id)

    def test_unlink_refused_when_allocations_exist(self):
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-UNL-ALLOC",
            sheet_id=sheet.id,
            amount=25.0,
        )
        allocation = self.env["collection.allocation"].create(
            {
                "sheet_id": sheet.id,
                "partner_id": voucher.partner_id.id,
                "voucher_ids": [Command.set(voucher.ids)],
                "line_ids": [
                    Command.create(
                        {
                            "external_invoice_id": "INV-UNL",
                            "invoice_number": "U-1",
                            "invoice_balance": 25.0,
                            "amount_applied": 25.0,
                        }
                    )
                ],
            }
        )
        self.assertTrue(sheet.allocation_ids)
        sheet_id = sheet.id
        voucher_id = voucher.id
        with self.assertRaises(UserError):
            sheet.unlink()
        leftover_sheet = self.env["collection.sheet"].browse(sheet_id)
        leftover_voucher = self.env["collection.voucher"].browse(voucher_id)
        self.assertTrue(leftover_sheet.exists())
        self.assertTrue(leftover_voucher.exists())
        self.assertEqual(leftover_voucher.sheet_id, leftover_sheet)
        self.assertEqual(leftover_voucher.allocation_id, allocation)
        self.assertEqual(allocation.sheet_id, leftover_sheet)

    def test_delete_command_unassigns_without_destroying_voucher(self):
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-DELCMD", sheet_id=sheet.id
        )
        sheet.write({"voucher_ids": [Command.delete(voucher.id)]})
        self.assertTrue(voucher.exists())
        self.assertFalse(voucher.sheet_id)
        self.assertFalse(sheet.voucher_ids)

    def test_freeze_rejects_add_remove_and_reassign(self):
        sheet = self._create_sheet()
        member = self._create_voucher(
            customer_identification="CUST-FRZ-MEM", sheet_id=sheet.id
        )
        outsider = self._create_voucher(
            customer_identification="CUST-FRZ-OUT", seller_id=False
        )
        outsider.write({"seller_id": self._seller().id})
        sheet.action_close()
        with self.assertRaises(UserError):
            outsider.write({"sheet_id": sheet.id})
        with self.assertRaises(UserError):
            sheet.write({"voucher_ids": [Command.link(outsider.id)]})
        with self.assertRaises(UserError):
            member.write({"sheet_id": False})
        with self.assertRaises(UserError):
            sheet.write({"voucher_ids": [Command.unlink(member.id)]})
        with self.assertRaises(UserError):
            sheet.write({"voucher_ids": [Command.delete(member.id)]})
        target = self._create_sheet()
        with self.assertRaises(UserError):
            member.write({"sheet_id": target.id})
        with self.assertRaises(UserError):
            self._create_voucher(
                customer_identification="CUST-FRZ-CRT", sheet_id=sheet.id
            )
        self.assertEqual(member.sheet_id, sheet)
        self.assertFalse(outsider.sheet_id)
        self.assertEqual(sheet.voucher_ids, member)
        self.assertTrue(member.exists())

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
        sheet_b = self._create_sheet(seller_id=self._other_internal_seller().id)
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
        unsaved = self.env["collection.sheet"].new({"seller_id": self._seller().id})
        self.assertFalse(isinstance(unsaved.id, int))
        self.assertFalse(unsaved.id)
        with self.assertRaises(UserError):
            unsaved.action_open_document_review()

    def test_empty_sheet_voucher_count_is_zero(self):
        """A sheet with no members MUST report non-stored voucher_count 0."""
        field = self.env["collection.sheet"]._fields["voucher_count"]
        self.assertTrue(field.compute)
        self.assertFalse(field.store)
        sheet = self._create_sheet()
        self.assertFalse(sheet.voucher_ids)
        self.assertEqual(sheet.voucher_count, 0)

    def test_voucher_count_matches_member_count(self):
        """Triangulation: voucher_count MUST equal the number of sheet members."""
        sheet = self._create_sheet()
        first = self._create_voucher(
            customer_identification="CUST-VC-1", sheet_id=sheet.id
        )
        second = self._create_voucher(
            customer_identification="CUST-VC-2", sheet_id=sheet.id
        )
        self.assertEqual(sheet.voucher_ids, first | second)
        self.assertEqual(sheet.voucher_count, 2)

    def test_action_open_vouchers_returns_filtered_act_window(self):
        """Saved sheet MUST open vouchers for that sheet only (no menu path)."""
        sheet = self._create_sheet()
        self.assertIsInstance(sheet.id, int)
        self.assertGreater(sheet.id, 0)
        action = sheet.action_open_vouchers()
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "collection.voucher")
        self.assertEqual(action["view_mode"], "list,kanban,form")
        self.assertEqual(action["domain"], [("sheet_id", "=", sheet.id)])
        self.assertEqual(action["context"]["default_sheet_id"], sheet.id)
        self.assertEqual(action["context"]["default_seller_id"], sheet.seller_id.id)
        self.assertFalse(action.get("path"))

    def test_action_open_vouchers_domain_matches_each_saved_sheet(self):
        """Triangulation: domain and defaults bind to the invoked sheet."""
        sheet_a = self._create_sheet()
        sheet_b = self._create_sheet(seller_id=self._other_internal_seller().id)
        self.assertNotEqual(sheet_a.id, sheet_b.id)
        action_a = sheet_a.action_open_vouchers()
        action_b = sheet_b.action_open_vouchers()
        self.assertEqual(action_a["domain"], [("sheet_id", "=", sheet_a.id)])
        self.assertEqual(action_b["domain"], [("sheet_id", "=", sheet_b.id)])
        self.assertEqual(action_a["context"]["default_seller_id"], sheet_a.seller_id.id)
        self.assertEqual(action_b["context"]["default_seller_id"], sheet_b.seller_id.id)
        self.assertEqual(action_a["view_mode"], "list,kanban,form")
        self.assertEqual(action_b["view_mode"], "list,kanban,form")

    def test_action_open_vouchers_refused_on_new_id(self):
        """Unsaved .new() records (NewId) must not open vouchers."""
        unsaved = self.env["collection.sheet"].new({"seller_id": self._seller().id})
        self.assertFalse(isinstance(unsaved.id, int))
        self.assertFalse(unsaved.id)
        with self.assertRaises(UserError):
            unsaved.action_open_vouchers()

    def test_document_review_enabled_helper_is_non_stored_and_follows_flag(self):
        """Non-stored helper mirrors company._document_review_enabled() (no DDL)."""
        field = self.env["collection.sheet"]._fields["document_review_enabled"]
        self.assertTrue(field.compute)
        self.assertFalse(field.store)
        self.env.company.write({"document_review_enabled": True})
        on_sheet = self._create_sheet()
        self.assertTrue(on_sheet.document_review_enabled)
        on_sheet.action_close()
        self.env.company.write({"document_review_enabled": False})
        off_sheet = self._create_sheet()
        self.assertFalse(off_sheet.document_review_enabled)

    def test_create_with_seller_assigns_unique_open_sheet(self):
        """Unique open sheet MUST receive vouchers created with that seller."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(customer_identification="CUST-AA-UNIQ")
        self.assertEqual(voucher.sheet_id, sheet)
        self.assertEqual(sheet.voucher_ids, voucher)

    def test_create_with_seller_creates_open_sheet_when_none(self):
        """Zero opens MUST create one open sheet and assign the voucher."""
        before = self._sheet_count()
        voucher = self._create_voucher(customer_identification="CUST-AA-NONE")
        self.assertEqual(self._sheet_count(), before + 1)
        self.assertTrue(voucher.sheet_id)
        self.assertEqual(voucher.sheet_id.seller_id, self._seller())
        self.assertEqual(voucher.sheet_id.state, "open")
        self.assertIn(voucher, voucher.sheet_id.voucher_ids)

    def test_create_with_seller_rejected_when_multiple_opens(self):
        """More than one open MUST raise UserError with no voucher written."""
        first = self._create_sheet()
        leftover = self._create_sheet(state="closed")
        leftover.with_context(collection_sheet_audited_state=True).write(
            {"state": "open"}
        )
        before_vouchers = self.env["collection.voucher"].search_count([])
        before_sheets = self._sheet_count()
        with self.assertRaises(UserError):
            self._create_voucher(customer_identification="CUST-AA-MULTI")
        self.assertEqual(
            self.env["collection.voucher"].search_count([]), before_vouchers
        )
        self.assertEqual(self._sheet_count(), before_sheets)
        self.assertEqual(first.state, "open")
        self.assertEqual(leftover.state, "open")

    def test_create_honors_explicit_open_sheet_id(self):
        """Explicit open same-seller sheet_id MUST be used instead of resolving."""
        sheet = self._create_sheet()
        voucher = self._create_voucher(
            customer_identification="CUST-AA-EXPL", sheet_id=sheet.id
        )
        self.assertEqual(voucher.sheet_id, sheet)
        falsey = self._create_voucher(
            customer_identification="CUST-AA-FALSEY", sheet_id=False
        )
        self.assertEqual(falsey.sheet_id, sheet)

    def test_create_with_closed_sheet_id_fails(self):
        """Assigning a closed sheet on create MUST fail (Phase 2 freeze)."""
        sheet = self._create_sheet()
        sheet.action_close()
        before = self.env["collection.voucher"].search_count([])
        with self.assertRaises(UserError):
            self._create_voucher(
                customer_identification="CUST-AA-CLOSED", sheet_id=sheet.id
            )
        self.assertEqual(self.env["collection.voucher"].search_count([]), before)
        self.assertFalse(sheet.voucher_ids)

    def test_create_without_seller_stays_unassigned(self):
        """Null seller_id MUST leave the voucher unassigned even if an open exists."""
        sheet = self._create_sheet()
        before = self.env["collection.voucher"].search_count([])
        with self.assertRaises(UserError):
            self.env["collection.voucher"].create(
                {
                    "partner_id": dummy_customer_partner(
                        self.env, customer="CUST-AA-OMIT"
                    ).id,
                    "document_type": "unsupported",
                }
            )
        self.assertEqual(self.env["collection.voucher"].search_count([]), before)

        historical = self._create_voucher(
            customer_identification="CUST-AA-HIST-NULL", seller_id=False
        )
        self.env.cr.execute(
            """
            UPDATE collection_voucher
               SET seller_id = NULL, sheet_id = NULL
             WHERE id = %s
            """,
            (historical.id,),
        )
        historical.invalidate_recordset(["seller_id", "sheet_id"])
        self.assertFalse(historical.seller_id)
        self.assertFalse(historical.sheet_id)
        self.assertNotIn(historical, sheet.voucher_ids)

    def test_later_seller_write_does_not_auto_assign(self):
        """Writing seller_id on an existing voucher MUST NOT auto-assign."""
        sheet = self._create_sheet()
        omitted = self._create_voucher(
            customer_identification="CUST-AA-WRITE-OMIT",
            sheet_id=sheet.id,
        )
        omitted.write({"sheet_id": False})
        omitted.write({"seller_id": self._seller().id})
        self.assertFalse(omitted.sheet_id)

        member = self._create_voucher(
            customer_identification="CUST-AA-WRITE-UNASG", sheet_id=sheet.id
        )
        member.write({"sheet_id": False})
        self.assertFalse(member.sheet_id)
        member.write({"seller_id": self._seller().id})
        self.assertFalse(member.sheet_id)

        other = self._other_internal_seller()
        other_sheet = self._create_sheet(seller_id=other.id)
        linked = self._create_voucher(
            customer_identification="CUST-AA-WRITE-UNL",
            seller_id=other.id,
            sheet_id=other_sheet.id,
        )
        other_sheet.unlink()
        self.assertFalse(linked.sheet_id)
        linked.write({"seller_id": other.id})
        self.assertFalse(linked.sheet_id)
        self.assertEqual(sheet.state, "open")
        self.assertNotIn(omitted, sheet.voucher_ids)
        self.assertNotIn(member, sheet.voucher_ids)

    def test_batch_create_resolves_one_open_per_seller(self):
        """Batch create MUST resolve once per seller and share that sheet."""
        seller = self._seller()
        other = self._other_internal_seller()
        self._ensure_enabled_seller(other)
        self.env["collection.sheet"].search(
            [
                ("seller_id", "in", [seller.id, other.id]),
                ("state", "=", "open"),
            ]
        ).action_close()
        before = self._sheet_count()
        vouchers = self.env["collection.voucher"].create(
            [
                {
                    "partner_id": dummy_customer_partner(
                        self.env, customer="CUST-AA-BATCH-A"
                    ).id,
                    "document_type": "unsupported",
                    "seller_id": seller.id,
                },
                {
                    "partner_id": dummy_customer_partner(
                        self.env, customer="CUST-AA-BATCH-B"
                    ).id,
                    "document_type": "unsupported",
                    "seller_id": seller.id,
                },
                {
                    "partner_id": dummy_customer_partner(
                        self.env, customer="CUST-AA-BATCH-C"
                    ).id,
                    "document_type": "unsupported",
                    "seller_id": other.id,
                },
            ]
        )
        self.assertEqual(self._sheet_count(), before + 2)
        first, second, third = vouchers
        self.assertTrue(first.sheet_id)
        self.assertEqual(first.sheet_id, second.sheet_id)
        self.assertEqual(first.sheet_id.seller_id, seller)
        self.assertEqual(first.sheet_id.state, "open")
        self.assertNotEqual(third.sheet_id, first.sheet_id)
        self.assertEqual(third.sheet_id.seller_id, other)
        self.assertEqual(third.sheet_id.state, "open")

    def _enable_sellers(self, *sellers):
        self.env.company.write(
            {"enabled_seller_ids": [Command.set([seller.id for seller in sellers])]}
        )

    def _clear_enabled_sellers(self):
        self.env.company.write({"enabled_seller_ids": [Command.clear()]})

    def test_sheet_create_empty_enabled_sellers_rejected(self):
        """NEW sheet create MUST reject a seller when the enabled list is empty."""
        seller = self.env.ref("base.user_admin")
        self._clear_enabled_sellers()
        before = self._sheet_count()
        with self.assertRaises(UserError):
            self.env["collection.sheet"].create({"seller_id": seller.id})
        self.assertEqual(self._sheet_count(), before)

    def test_sheet_create_disabled_seller_rejected(self):
        """Triangulation: a seller missing from the enabled list MUST be rejected."""
        enabled = self.env.ref("base.user_admin")
        disabled = create_internal_seller(self.env, "sheet_disabled_seller")
        self._enable_sellers(enabled)
        before = self._sheet_count()
        with self.assertRaises(UserError):
            self.env["collection.sheet"].create({"seller_id": disabled.id})
        self.assertEqual(self._sheet_count(), before)

    def test_disabled_seller_sheet_stays_visible_and_closeable(self):
        seller = self.env.ref("base.user_admin")
        self._enable_sellers(seller)
        sheet = self.env["collection.sheet"].create({"seller_id": seller.id})
        self._clear_enabled_sellers()
        found = self.env["collection.sheet"].search([("id", "=", sheet.id)])
        self.assertEqual(found, sheet, "disabled-seller sheet must stay listed")
        sheet.action_close()
        self.assertEqual(sheet.state, "closed")
        self.assertTrue(sheet.exists())

    def test_disabled_seller_sheet_reopen_skips_helper(self):
        """Triangulation: Reopen MUST skip the new-work helper."""
        seller = self.env.ref("base.user_admin")
        self._enable_sellers(seller)
        sheet = self.env["collection.sheet"].create({"seller_id": seller.id})
        sheet.action_close()
        self._clear_enabled_sellers()
        sheet.action_reopen()
        self.assertEqual(sheet.state, "open")
        self.assertTrue(sheet.exists())

    def _partner_has_autopost_bills_column(self):
        self.env.cr.execute(
            """
            SELECT 1
              FROM information_schema.columns
             WHERE table_name = 'res_partner'
               AND column_name = 'autopost_bills'
            """
        )
        return bool(self.env.cr.fetchone())

    def _create_company(self, name):
        """Persist a second company; satisfy partner.autopost_bills when present."""
        Partner = self.env["res.partner"].with_context(
            tracking_disable=True,
            mail_create_nolog=True,
            mail_notrack=True,
            mail_create_nosubscribe=True,
        )
        partner_vals = {"name": name, "is_company": True}
        if "autopost_bills" in Partner._fields:
            partner_vals["autopost_bills"] = "ask"
            partner = Partner.create(partner_vals)
        elif self._partner_has_autopost_bills_column():
            self.env.cr.execute(
                """
                INSERT INTO res_partner (
                    name, email, active, complete_name, type, is_company,
                    autopost_bills, create_uid, write_uid, create_date, write_date
                )
                VALUES (
                    %s, %s, true, %s, 'contact', true, 'ask',
                    1, 1,
                    (now() AT TIME ZONE 'UTC'),
                    (now() AT TIME ZONE 'UTC')
                )
                RETURNING id
                """,
                (name, f"{name}@example.com", name),
            )
            partner = Partner.browse(self.env.cr.fetchone()[0])
        else:
            partner = Partner.create(partner_vals)
        return self.env["res.company"].create(
            {
                "name": name,
                "partner_id": partner.id,
            }
        )

    def test_auto_create_off_skips_create_and_assign(self):
        """OFF + omitted sheet_id MUST persist unassigned and not create a sheet."""
        self.env.company.write({"auto_create_sheet": False})
        before = self._sheet_count()
        voucher = self._create_voucher(customer_identification="CUST-AA-OFF")
        self.assertFalse(voucher.sheet_id)
        self.assertEqual(self._sheet_count(), before)

    def test_auto_create_off_skips_assign_when_open_exists(self):
        """Triangulation: OFF MUST skip assign even when an open sheet exists."""
        sheet = self._create_sheet()
        self.env.company.write({"auto_create_sheet": False})
        before = self._sheet_count()
        voucher = self._create_voucher(customer_identification="CUST-AA-OFF-OPEN")
        self.assertFalse(voucher.sheet_id)
        self.assertNotIn(voucher, sheet.voucher_ids)
        self.assertEqual(self._sheet_count(), before)
        self.assertEqual(sheet.state, "open")

    def test_action_creates_sheet_when_auto_create_off(self):
        """List Action MUST still create one open sheet when auto-create is OFF."""
        self.env.company.write({"auto_create_sheet": False})
        before = self._sheet_count()
        voucher = self._create_voucher(customer_identification="CUST-ACT-OFF")
        self.assertFalse(voucher.sheet_id)
        self.assertEqual(self._sheet_count(), before)
        action = voucher.action_create_collection_sheet()
        self.assertEqual(self._sheet_count(), before + 1)
        sheet = self.env["collection.sheet"].browse(action["res_id"])
        self.assertEqual(sheet.seller_id, self._seller())
        self.assertEqual(sheet.company_id, voucher.company_id)
        self.assertEqual(sheet.state, "open")
        self.assertEqual(voucher.sheet_id, sheet)

    def test_action_rejected_for_disabled_seller(self):
        """List Action MUST reject after the seller is removed from the enabled list."""
        self.env.company.write({"auto_create_sheet": False})
        seller = self._seller()
        voucher = self._create_voucher(customer_identification="CUST-ACT-DISABLED")
        self.assertEqual(voucher.seller_id, seller)
        self.assertFalse(voucher.sheet_id)
        other = self._other_internal_seller()
        self._enable_sellers(other)
        self.assertNotIn(seller, self.env.company.enabled_seller_ids)
        before = self._sheet_count()
        with self.assertRaises(UserError) as err:
            voucher.action_create_collection_sheet()
        self.assertIn("seller", str(err.exception).lower())
        self.assertEqual(self._sheet_count(), before)
        self.assertFalse(voucher.sheet_id)

    def test_same_seller_may_be_open_in_two_companies(self):
        """One-open is per (company, seller): A and B MAY both have one open."""
        seller = self._seller()
        sheet_a = self._create_sheet()
        company_b = self._create_company("One Open Co B")
        ensure_enabled_seller(self.env, seller, company_b)
        sheet_b = self.env["collection.sheet"].create(
            {
                "seller_id": seller.id,
                "company_id": company_b.id,
            }
        )
        self.assertEqual(sheet_a.state, "open")
        self.assertEqual(sheet_b.state, "open")
        self.assertEqual(sheet_a.company_id, self.env.company)
        self.assertEqual(sheet_b.company_id, company_b)
        self.assertEqual(sheet_a.seller_id, seller)
        self.assertEqual(sheet_b.seller_id, seller)
        with self.assertRaises(UserError):
            self._create_sheet()
        self.assertEqual(sheet_a.state, "open")
        self.assertEqual(sheet_b.state, "open")

    def test_auto_assign_creates_open_in_voucher_company(self):
        """ON auto-assign MUST resolve open sheets in the voucher company only."""
        seller = self._seller()
        sheet_a = self._create_sheet()
        company_b = self._create_company("Auto Assign Co B")
        ensure_enabled_seller(self.env, seller, company_b)
        voucher = self.env["collection.voucher"].create(
            {
                "partner_id": dummy_customer_partner(
                    self.env, customer="CUST-AA-COB"
                ).id,
                "document_type": "unsupported",
                "seller_id": seller.id,
                "company_id": company_b.id,
            }
        )
        self.assertEqual(voucher.company_id, company_b)
        self.assertTrue(voucher.sheet_id)
        self.assertEqual(voucher.sheet_id.company_id, company_b)
        self.assertEqual(voucher.sheet_id.seller_id, seller)
        self.assertEqual(voucher.sheet_id.state, "open")
        self.assertNotEqual(voucher.sheet_id, sheet_a)
        self.assertEqual(sheet_a.state, "open")

    def test_action_creates_sheet_in_selection_company(self):
        """List Action MUST stamp the vouchers' company, not env.company."""
        company_b = self._create_company("Action Co B")
        seller = self._seller()
        ensure_enabled_seller(self.env, seller, company_b)
        voucher = self._create_voucher(
            customer_identification="CUST-ACT-COB",
            seller_id=False,
            company_id=company_b.id,
        )
        voucher.write({"seller_id": seller.id})
        self.assertFalse(voucher.sheet_id)
        action = voucher.action_create_collection_sheet()
        sheet = self.env["collection.sheet"].browse(action["res_id"])
        self.assertEqual(sheet.company_id, company_b)
        self.assertEqual(sheet.seller_id, seller)
        self.assertEqual(voucher.sheet_id, sheet)

    def test_action_allowed_when_seller_open_in_other_company(self):
        """Triangulation: an open sheet in B MUST NOT block the Action in A."""
        seller = self._seller()
        company_b = self._create_company("Action Other Co")
        ensure_enabled_seller(self.env, seller, company_b)
        sheet_b = self.env["collection.sheet"].create(
            {
                "seller_id": seller.id,
                "company_id": company_b.id,
            }
        )
        voucher = self._create_voucher(
            customer_identification="CUST-ACT-OTHER", seller_id=False
        )
        voucher.write({"seller_id": seller.id})
        action = voucher.action_create_collection_sheet()
        sheet_a = self.env["collection.sheet"].browse(action["res_id"])
        self.assertEqual(sheet_a.company_id, self.env.company)
        self.assertEqual(sheet_a.seller_id, seller)
        self.assertEqual(voucher.sheet_id, sheet_a)
        self.assertEqual(sheet_b.state, "open")
        self.assertNotEqual(sheet_a, sheet_b)
