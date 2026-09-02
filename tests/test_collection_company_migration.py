# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from re import fullmatch

from odoo.tests import TransactionCase

from .test_collection_payment import dummy_customer_partner, ensure_enabled_seller

ALL_TYPE_CODES = frozenset({"bank_transfer", "check", "cash_deposit", "unsupported"})
MIGRATE_PATH = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "19.0.1.17.0"
    / "post-migrate.py"
)


def _load_company_config_migrate():
    spec = spec_from_file_location(
        "collection_company_config_post_migrate", MIGRATE_PATH
    )
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestCollectionCompanyMigration(TransactionCase):
    """RED: upgrade stamps, seeds, four types, and per-company sequences."""

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

    def _create_partner(self, name, is_company=False, email=None):
        """Create a partner; set autopost_bills when the DB column exists."""
        Partner = self.env["res.partner"].with_context(
            tracking_disable=True,
            mail_create_nolog=True,
            mail_notrack=True,
            mail_create_nosubscribe=True,
        )
        partner_vals = {"name": name, "is_company": is_company}
        if email:
            partner_vals["email"] = email
        if "autopost_bills" in Partner._fields:
            partner_vals["autopost_bills"] = "ask"
            return Partner.create(partner_vals)
        if self._partner_has_autopost_bills_column():
            self.env.cr.execute(
                """
                INSERT INTO res_partner (
                    name, email, active, complete_name, type, is_company,
                    autopost_bills, create_uid, write_uid, create_date, write_date
                )
                VALUES (
                    %s, %s, true, %s, 'contact', %s, 'ask',
                    1, 1,
                    (now() AT TIME ZONE 'UTC'),
                    (now() AT TIME ZONE 'UTC')
                )
                RETURNING id
                """,
                (name, email, name, is_company),
            )
            return Partner.browse(self.env.cr.fetchone()[0])
        return Partner.create(partner_vals)

    def _create_company(self, name):
        partner = self._create_partner(
            name, is_company=True, email=f"{name}@example.com"
        )
        return self.env["res.company"].create({"name": name, "partner_id": partner.id})

    def _create_seller(self, login, company):
        partner = self._create_partner(login, email=f"{login}@example.com")
        seller = (
            self.env["res.users"]
            .with_context(no_reset_password=True, tracking_disable=True)
            .create(
                {
                    "name": login,
                    "login": login,
                    "email": f"{login}@example.com",
                    "partner_id": partner.id,
                    "company_id": company.id,
                    "company_ids": [(6, 0, [company.id])],
                    "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
                }
            )
        )
        ensure_enabled_seller(self.env, seller, company=company)
        ensure_enabled_seller(self.env, seller, company=self.env.company)
        return seller

    def _run_migrate(self):
        _load_company_config_migrate().migrate(self.env.cr, "19.0.1.16.0")
        self.env.invalidate_all()

    def _seq_number(self, name, prefix):
        year = date.today().year
        match = fullmatch(rf"{prefix}/{year}/(\d{{4,}})", name)
        self.assertTrue(match, f"{name!r} must match {prefix}/<year>/<number>")
        return int(match.group(1))

    def _null_collection_sequences(self):
        self.env.cr.execute(
            """
            UPDATE ir_sequence
               SET company_id = NULL
             WHERE code IN ('collection.voucher', 'collection.sheet')
            """
        )
        self.env.invalidate_all()

    def _create_voucher(self, vals):
        company = self.env["res.company"].browse(
            vals.get("company_id") or self.env.company.id
        )
        vals = dict(vals)
        partner = dummy_customer_partner(self.env, extra=vals, default="MIG-CUST")
        vals["partner_id"] = partner.id
        if not vals.get("seller_id"):
            vals = dict(
                vals,
                seller_id=ensure_enabled_seller(self.env, company=company).id,
            )
        else:
            ensure_enabled_seller(
                self.env,
                self.env["res.users"].browse(vals["seller_id"]),
                company=company,
            )
        return self.env["collection.voucher"].create(vals)

    def test_sequence_xml_binds_to_main_company(self):
        xml_path = Path(__file__).resolve().parents[1] / "data" / "ir_sequence_data.xml"
        text = xml_path.read_text(encoding="utf-8")
        self.assertIn('ref="base.main_company"', text)
        self.assertNotIn('eval="False"', text)
        self.assertIn("noupdate", text)
        self.assertIn("seq_collection_allocation", text)
        self.assertIn("CA/%(year)s/", text)

    def test_manifest_version_is_1_27_0(self):
        module_root = Path(__file__).resolve().parents[1]
        manifest = module_root / "__manifest__.py"
        self.assertIn('"version": "19.0.1.27.0"', manifest.read_text(encoding="utf-8"))
        self.assertFalse(
            (module_root / "migrations" / "19.0.1.27.0").exists(),
            "No migrations/19.0.1.27.0/ folder — this bump has no stored-field migrate",
        )

    def test_allocation_sequence_in_specs_not_in_1_17_0_codes(self):
        specs_path = Path(__file__).resolve().parents[1] / "models" / "res_company.py"
        specs_text = specs_path.read_text(encoding="utf-8")
        self.assertIn('("collection.allocation", "Collection Allocation"', specs_text)
        self.assertIn('"CA/%(year)s/"', specs_text)
        migrate_117 = _load_company_config_migrate()
        self.assertNotIn("collection.allocation", migrate_117.COLLECTION_SEQUENCE_CODES)
        migrate_125 = (
            Path(__file__).resolve().parents[1]
            / "migrations"
            / "19.0.1.25.0"
            / "post-migrate.py"
        )
        self.assertTrue(migrate_125.is_file())
        text_125 = migrate_125.read_text(encoding="utf-8")
        self.assertIn("_collection_copy_sequences", text_125)
        self.assertNotIn("COLLECTION_SEQUENCE_CODES", text_125)

    def test_sheet_company_stamped_from_seller_else_main(self):
        main = self.env.ref("base.main_company")
        company_b = self._create_company("Stamp Sheet Co B")
        seller_b = self._create_seller("stamp_sheet_seller_b", company_b)
        sheet_from_seller = self.env["collection.sheet"].create(
            {"seller_id": seller_b.id, "company_id": main.id}
        )
        seller_main = self._create_seller("stamp_sheet_seller_main", main)
        ensure_enabled_seller(self.env, seller_main, company=company_b)
        sheet_default = self.env["collection.sheet"].create(
            {"seller_id": seller_main.id, "company_id": company_b.id}
        )
        self.assertEqual(sheet_from_seller.company_id, main)
        self.assertEqual(sheet_default.company_id, company_b)
        self._run_migrate()
        self.assertEqual(sheet_from_seller.company_id, company_b)
        self.assertEqual(sheet_default.company_id, main)

    def test_voucher_company_from_sheet_then_seller_or_main(self):
        main = self.env.ref("base.main_company")
        company_b = self._create_company("Stamp Voucher Co B")
        seller_b = self._create_seller("stamp_voucher_seller_b", company_b)
        sheet_b = self.env["collection.sheet"].create(
            {"seller_id": seller_b.id, "company_id": company_b.id}
        )
        from_sheet = self._create_voucher(
            {
                "customer_identification": "STAMP-SHEET",
                "document_type": "bank_transfer",
                "seller_id": seller_b.id,
                "sheet_id": sheet_b.id,
                "company_id": main.id,
            }
        )
        no_sheet = self._create_voucher(
            {
                "customer_identification": "STAMP-SELLER",
                "document_type": "check",
                "company_id": main.id,
            }
        )
        self.env.cr.execute(
            """
            UPDATE collection_voucher
               SET seller_id = %s, sheet_id = NULL, company_id = %s
             WHERE id = %s
            """,
            (seller_b.id, main.id, no_sheet.id),
        )
        null_seller = self._create_voucher(
            {
                "customer_identification": "STAMP-MAIN",
                "document_type": "cash_deposit",
                "company_id": company_b.id,
            }
        )
        self.env.cr.execute(
            """
            UPDATE collection_voucher
               SET seller_id = NULL, sheet_id = NULL, company_id = %s
             WHERE id = %s
            """,
            (company_b.id, null_seller.id),
        )
        self.env.invalidate_all()
        self._run_migrate()
        self.assertEqual(from_sheet.company_id, company_b)
        self.assertEqual(no_sheet.company_id, company_b)
        self.assertEqual(null_seller.company_id, main)

    def test_repair_member_voucher_matches_sheet_company(self):
        main = self.env.ref("base.main_company")
        company_b = self._create_company("Repair Co B")
        seller_b = self._create_seller("repair_seller_b", company_b)
        sheet_b = self.env["collection.sheet"].create(
            {"seller_id": seller_b.id, "company_id": company_b.id}
        )
        member = self._create_voucher(
            {
                "customer_identification": "REPAIR-MEMBER",
                "document_type": "bank_transfer",
                "seller_id": seller_b.id,
                "sheet_id": sheet_b.id,
                "company_id": main.id,
            }
        )
        self.assertEqual(member.company_id, main)
        self._run_migrate()
        self.assertEqual(member.company_id, sheet_b.company_id)
        self.assertEqual(member.company_id, company_b)

    def test_seed_sellers_from_vouchers_and_sheets_keeps_disabled(self):
        company_b = self._create_company("Seed Sellers Co B")
        seller_sheet = self._create_seller("seed_sheet_seller", company_b)
        seller_voucher = self._create_seller("seed_voucher_seller", company_b)
        seller_disabled = self._create_seller("seed_disabled_seller", company_b)
        self.env["collection.sheet"].create(
            {"seller_id": seller_sheet.id, "company_id": company_b.id}
        )
        orphan = self._create_voucher(
            {
                "customer_identification": "SEED-VOUCHER",
                "document_type": "check",
                "company_id": company_b.id,
            }
        )
        self.env.cr.execute(
            """
            UPDATE collection_voucher
               SET seller_id = %s, sheet_id = NULL, company_id = %s
             WHERE id = %s
            """,
            (seller_voucher.id, company_b.id, orphan.id),
        )
        disabled_voucher = self._create_voucher(
            {
                "customer_identification": "SEED-DISABLED",
                "document_type": "cash_deposit",
                "company_id": company_b.id,
            }
        )
        self.env.cr.execute(
            """
            UPDATE collection_voucher
               SET seller_id = %s, sheet_id = NULL, company_id = %s
             WHERE id = %s
            """,
            (seller_disabled.id, company_b.id, disabled_voucher.id),
        )
        seller_disabled.write({"active": False})
        company_b.write({"enabled_seller_ids": [(5, 0, 0)]})
        self.env.invalidate_all()
        self.assertFalse(company_b.enabled_seller_ids)
        self._run_migrate()
        seeded = company_b.with_context(active_test=False).enabled_seller_ids
        self.assertIn(seller_sheet, seeded)
        self.assertIn(seller_voucher, seeded)
        self.assertIn(seller_disabled, seeded)

    def test_migrate_enables_all_four_types_including_partial_lists(self):
        check = self.env.ref("collection.document_type_check")
        company_b = self._create_company("Partial Types Co B")
        company_b.write({"allowed_document_type_ids": [(6, 0, [check.id])]})
        extra = self.env["collection.document.type"].create(
            {"code": "wire_mig", "name": "Wire Mig"}
        )
        self.env.company.write(
            {
                "allowed_document_type_ids": [
                    (4, extra.id),
                ]
            }
        )
        self.assertEqual(
            set(company_b.allowed_document_type_ids.mapped("code")), {"check"}
        )
        self._run_migrate()
        self.assertEqual(
            set(company_b.allowed_document_type_ids.mapped("code")),
            ALL_TYPE_CODES,
        )
        self.assertIn(extra, self.env.company.allowed_document_type_ids)
        self.assertEqual(
            set(self.env.company.allowed_document_type_ids.mapped("code")),
            ALL_TYPE_CODES | {"wire_mig"},
        )

    def test_migrate_binds_null_sequences_to_main_and_copies_others(self):
        main = self.env.ref("base.main_company")
        voucher_seq = self.env.ref("collection.seq_collection_voucher")
        sheet_seq = self.env.ref("collection.seq_collection_sheet")
        preserved = voucher_seq.number_next_actual
        company_b = self._create_company("Seq Copy Co B")
        self._null_collection_sequences()
        self._run_migrate()
        leftover = self.env["ir.sequence"].search(
            [
                ("code", "in", ["collection.voucher", "collection.sheet"]),
                ("company_id", "=", False),
            ]
        )
        self.assertFalse(leftover, "company-less sequences must not remain")
        self.assertEqual(voucher_seq.company_id, main)
        self.assertEqual(sheet_seq.company_id, main)
        self.assertEqual(voucher_seq.number_next_actual, preserved)
        for code in ("collection.voucher", "collection.sheet"):
            copies = self.env["ir.sequence"].search(
                [("code", "=", code), ("company_id", "=", company_b.id)]
            )
            self.assertEqual(len(copies), 1, f"{code} must exist for company B")

    def test_voucher_and_sheet_numbers_isolated_per_company(self):
        company_b = self._create_company("Number Isol Co B")
        # Auto-assign would consume CS/ numbers in the voucher company; this
        # test measures sequence isolation, not sheet auto-create.
        self.env.company.write({"auto_create_sheet": False})
        company_b.write({"auto_create_sheet": False})
        seller_b = self._create_seller("isol_sheet_seller_b", company_b)
        voucher_a = self._create_voucher(
            {
                "customer_identification": "ISO-A",
                "document_type": "bank_transfer",
            }
        )
        voucher_b = self._create_voucher(
            {
                "customer_identification": "ISO-B",
                "document_type": "check",
                "company_id": company_b.id,
            }
        )
        n_a = self._seq_number(voucher_a.name, "COL")
        self.assertEqual(self._seq_number(voucher_b.name, "COL"), 1)
        voucher_a2 = self._create_voucher(
            {
                "customer_identification": "ISO-A2",
                "document_type": "cash_deposit",
            }
        )
        voucher_b2 = self._create_voucher(
            {
                "customer_identification": "ISO-B2",
                "document_type": "unsupported",
                "company_id": company_b.id,
            }
        )
        self.assertEqual(self._seq_number(voucher_a2.name, "COL"), n_a + 1)
        self.assertEqual(self._seq_number(voucher_b2.name, "COL"), 2)
        self.env["collection.sheet"].search([("state", "=", "open")]).action_close()
        seller = ensure_enabled_seller(self.env)
        sheet_a = self.env["collection.sheet"].create({"seller_id": seller.id})
        sheet_b = self.env["collection.sheet"].create(
            {"seller_id": seller_b.id, "company_id": company_b.id}
        )
        n_sheet_a = self._seq_number(sheet_a.name, "CS")
        self.assertEqual(self._seq_number(sheet_b.name, "CS"), 1)
        sheet_a.action_close()
        sheet_a2 = self.env["collection.sheet"].create({"seller_id": seller.id})
        self.assertEqual(self._seq_number(sheet_a2.name, "CS"), n_sheet_a + 1)

    def test_leftover_false_sequence_does_not_steal_company_numbers(self):
        company_b = self._create_company("Thief Seq Co B")
        self.env["ir.sequence"].create(
            {
                "name": "Thief Payment Voucher",
                "code": "collection.voucher",
                "prefix": "COL/%(year)s/",
                "padding": 4,
                "company_id": False,
                "number_next": 9999,
            }
        )
        voucher_b = self._create_voucher(
            {
                "customer_identification": "THIEF-B",
                "document_type": "bank_transfer",
                "company_id": company_b.id,
            }
        )
        self.assertEqual(self._seq_number(voucher_b.name, "COL"), 1)
        self.assertNotEqual(voucher_b.name, f"COL/{date.today().year}/9999")

    def test_new_company_copies_sequences_seeds_types_empty_sellers(self):
        check = self.env.ref("collection.document_type_check")
        partner = self._create_partner(
            "Create Hook Co", is_company=True, email="create-hook@example.com"
        )
        company = self.env["res.company"].create(
            {
                "name": "Create Hook Co",
                "partner_id": partner.id,
                "allowed_document_type_ids": [(6, 0, [check.id])],
            }
        )
        self.assertFalse(company.enabled_seller_ids)
        self.assertEqual(
            set(company.allowed_document_type_ids.mapped("code")),
            ALL_TYPE_CODES,
        )
        for code, prefix in (
            ("collection.voucher", "COL"),
            ("collection.sheet", "CS"),
            ("collection.allocation", "CA"),
        ):
            seqs = self.env["ir.sequence"].search(
                [("code", "=", code), ("company_id", "=", company.id)]
            )
            self.assertEqual(len(seqs), 1, f"{code} must be copied on company create")
            self.assertTrue(seqs.prefix.startswith(prefix))
