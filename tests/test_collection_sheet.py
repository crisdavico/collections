# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date

from psycopg2 import IntegrityError

from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase
from odoo.tools import mute_logger


class TestCollectionSheet(TransactionCase):
    """RED/GREEN: collection.sheet sequence, frozen seller, no workflow."""

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

    def test_sequence_assigned_on_create(self):
        year = date.today().year
        sheet = self._create_sheet()
        self.assertRegex(
            sheet.name,
            rf"^CS/{year}/\d{{4}}$",
            "Sheet name must match CS/<year>/<padded number>",
        )
        self.assertNotIn("state", self.env["collection.sheet"]._fields)

    def test_sequence_names_are_unique(self):
        first = self._create_sheet()
        second = self._create_sheet()
        self.assertNotEqual(first.name, second.name)
        self.assertRegex(first.name, r"^CS/\d{4}/\d{4}$")
        self.assertRegex(second.name, r"^CS/\d{4}/\d{4}$")

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
