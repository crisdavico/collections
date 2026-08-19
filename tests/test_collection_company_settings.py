# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from psycopg2 import IntegrityError

from odoo.tests import TransactionCase
from odoo.tools import mute_logger

CATALOG_XMLIDS = (
    ("collection.document_type_bank_transfer", "bank_transfer", "Bank Transfer"),
    ("collection.document_type_check", "check", "Check"),
    ("collection.document_type_cash_deposit", "cash_deposit", "Cash Deposit"),
    ("collection.document_type_unsupported", "unsupported", "Unsupported"),
)
ALL_TYPE_CODES = frozenset(code for _xmlid, code, _name in CATALOG_XMLIDS)


class TestCollectionCompanySettings(TransactionCase):
    """Collection Settings persistence: catalog, defaults, empty sellers."""

    def test_catalog_xmlids_exist_with_expected_codes(self):
        for xmlid, code, name in CATALOG_XMLIDS:
            rec = self.env.ref(xmlid)
            self.assertEqual(rec._name, "collection.document.type")
            self.assertEqual(rec.code, code, f"{xmlid} must store code {code}")
            self.assertEqual(rec.name, name, f"{xmlid} must store name {name}")

    def test_catalog_has_exactly_four_seeded_types(self):
        """Triangulation: install data seeds exactly the four catalog codes."""
        types = self.env["collection.document.type"].search([])
        self.assertEqual(set(types.mapped("code")), ALL_TYPE_CODES)
        self.assertEqual(len(types), 4)

    def test_catalog_duplicate_code_raises_integrity_error(self):
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self.env["collection.document.type"].create(
                    {"code": "check", "name": "Duplicate Check"}
                )

    def test_catalog_distinct_code_creates(self):
        rec = self.env["collection.document.type"].create(
            {"code": "wire", "name": "Wire"}
        )
        self.assertTrue(rec.id)
        self.assertEqual(rec.code, "wire")
        self.assertEqual(rec.name, "Wire")

    def test_auto_create_sheet_defaults_true_on_field(self):
        field = self.env["res.company"]._fields["auto_create_sheet"]
        self.assertTrue(
            field.default(self.env["res.company"]),
            "auto_create_sheet must default ON",
        )

    def test_auto_create_sheet_true_on_env_company(self):
        """Fresh install / no prior settings: auto_create_sheet MUST be ON."""
        self.assertTrue(
            self.env.company.auto_create_sheet,
            "current company auto_create_sheet must default ON",
        )

    def test_new_company_auto_create_sheet_defaults_true(self):
        """Triangulation: a new company record also defaults auto_create_sheet ON."""
        company = self.env["res.company"].new({"name": "Auto Sheet Default Co"})
        self.assertTrue(company.auto_create_sheet)

    def test_env_company_allows_all_four_document_types(self):
        codes = set(self.env.company.allowed_document_type_ids.mapped("code"))
        self.assertEqual(
            codes,
            ALL_TYPE_CODES,
            "all four document types must start enabled on the company",
        )

    def test_new_company_enables_all_four_document_types(self):
        """Triangulation: a company with no prior settings enables all four types."""
        company = self.env["res.company"].new({"name": "Catalog Default Co"})
        codes = set(company.allowed_document_type_ids.mapped("code"))
        self.assertEqual(codes, ALL_TYPE_CODES)

    def test_unsupported_can_be_disabled_independently(self):
        unsupported = self.env.ref("collection.document_type_unsupported")
        others = self.env.company.allowed_document_type_ids - unsupported
        self.env.company.write({"allowed_document_type_ids": [(6, 0, others.ids)]})
        self.assertNotIn(
            unsupported,
            self.env.company.allowed_document_type_ids,
            "Unsupported must remain independently configurable",
        )
        self.assertEqual(
            set(self.env.company.allowed_document_type_ids.mapped("code")),
            {"bank_transfer", "check", "cash_deposit"},
        )

    def test_enabled_seller_ids_default_empty(self):
        self.assertFalse(
            self.env.company.enabled_seller_ids,
            "empty enabled sellers must persist as none (not all)",
        )

    def test_new_company_starts_with_empty_enabled_sellers(self):
        """Triangulation: new companies start with no enabled sellers."""
        company = self.env["res.company"].new({"name": "Empty Sellers Co"})
        self.assertFalse(company.enabled_seller_ids)

    def test_enabled_seller_ids_persist_via_settings(self):
        seller = self.env.ref("base.user_admin")
        settings = self.env["res.config.settings"].create(
            {"enabled_seller_ids": [(6, 0, [seller.id])]}
        )
        settings.execute()
        self.assertEqual(self.env.company.enabled_seller_ids, seller)

    def test_empty_enabled_seller_ids_persist_via_settings(self):
        """Clearing enabled sellers MUST persist empty (none for NEW work)."""
        seller = self.env.ref("base.user_admin")
        self.env.company.write({"enabled_seller_ids": [(6, 0, [seller.id])]})
        self.assertEqual(self.env.company.enabled_seller_ids, seller)
        settings = self.env["res.config.settings"].create(
            {"enabled_seller_ids": [(6, 0, [])]}
        )
        settings.execute()
        self.assertFalse(
            self.env.company.enabled_seller_ids,
            "empty enabled-seller list must persist as none",
        )
