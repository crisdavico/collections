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
    ("collection.document_type_echeck", "echeck", "Echeck"),
    ("collection.document_type_cash", "cash", "Cash"),
    (
        "collection.document_type_retention_certificate",
        "retention_certificate",
        "Retention Certificate",
    ),
    (
        "collection.document_type_seller_deposit",
        "seller_deposit",
        "Seller Deposit",
    ),
    (
        "collection.document_type_seller_commission",
        "seller_commission",
        "Seller Commission",
    ),
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

    def test_catalog_has_exactly_nine_seeded_types(self):
        """Install data seeds the nine catalog codes including seller_commission."""
        types = self.env["collection.document.type"].search([])
        self.assertEqual(set(types.mapped("code")), ALL_TYPE_CODES)
        self.assertEqual(len(types), 9)
        self.assertEqual(len(CATALOG_XMLIDS), 9)
        self.assertIn("seller_commission", ALL_TYPE_CODES)

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

    def test_env_company_allows_all_nine_document_types(self):
        codes = set(self.env.company.allowed_document_type_ids.mapped("code"))
        self.assertEqual(
            codes,
            ALL_TYPE_CODES,
            "all nine document types must start enabled on the company",
        )

    def test_new_company_enables_all_nine_document_types(self):
        """Triangulation: a company with no prior settings enables all nine types."""
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
        remaining = set(self.env.company.allowed_document_type_ids.mapped("code"))
        self.assertNotIn("unsupported", remaining)
        self.assertTrue(remaining)

    def test_enabled_seller_ids_default_empty(self):
        """Empty enabled sellers means none, not all. Field has no 'all' default."""
        field = self.env["res.company"]._fields["enabled_seller_ids"]
        self.assertFalse(
            field.default,
            "enabled_seller_ids must default to none (not all internal users)",
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

    def test_settings_collection_connector_id_is_related_writable(self):
        """Collection Settings MUST expose a writable related active connector."""
        field = self.env["res.config.settings"]._fields["collection_connector_id"]
        self.assertEqual(field.related, "company_id.collection_connector_id")
        self.assertFalse(field.readonly)

    def test_company_a_saves_connector_via_settings(self):
        """Company A MUST persist its active connector from Collection Settings."""
        connector = self.env["collection.connector"].create(
            {"name": "Company A Connector"}
        )
        self.assertEqual(connector.company_id, self.env.company)
        settings = self.env["res.config.settings"].create(
            {"collection_connector_id": connector.id}
        )
        settings.execute()
        self.assertEqual(self.env.company.collection_connector_id, connector)

    def test_company_b_keeps_connector_when_a_saves(self):
        """Triangulation: saving A's connector MUST NOT change company B's."""
        company_b = self._create_company("Connector Isolation Co B")
        connector_a = self.env["collection.connector"].create(
            {
                "name": "A Connector",
                "company_id": self.env.company.id,
            }
        )
        connector_b = self.env["collection.connector"].create(
            {
                "name": "B Connector",
                "company_id": company_b.id,
            }
        )
        company_b.write({"collection_connector_id": connector_b.id})
        settings = self.env["res.config.settings"].create(
            {"collection_connector_id": connector_a.id}
        )
        settings.execute()
        self.assertEqual(self.env.company.collection_connector_id, connector_a)
        self.assertEqual(company_b.collection_connector_id, connector_b)
