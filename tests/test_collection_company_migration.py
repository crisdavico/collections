# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from re import compile as re_compile
from re import fullmatch
from uuid import uuid4

from odoo.tests import TransactionCase

from .common_connector import force_sheet_state
from .test_collection_payment import dummy_customer_partner, ensure_enabled_seller

ALL_TYPE_CODES = frozenset({"bank_transfer", "check", "cash_deposit", "unsupported"})
SEVEN_TYPE_CODES = ALL_TYPE_CODES | {
    "echeck",
    "cash",
    "retention_certificate",
}
EIGHT_TYPE_CODES = SEVEN_TYPE_CODES | {"seller_deposit"}
NINE_TYPE_CODES = EIGHT_TYPE_CODES | {"seller_commission"}
MIGRATE_PATH = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "19.0.1.17.0"
    / "post-migrate.py"
)

# Sheet-state membership gates. Invoice ``open`` files are exempt; vocabulary
# (Selection, default, labels, dispatcher keys, write destinations) is not a gate.
_SHEET_OPEN_GATE_RE = re_compile(
    r"(?:"
    r"""\(\s*["']state["']\s*,\s*["']=["']\s*,\s*["']open["']"""
    r"|"
    r"""\.state\s*(?:!=|==)\s*["']open["']"""
    r"|"
    r"""\(vals\.get\(\s*["']state["']\s*\)\s*or\s*["']open["']\)"""
    r")"
)
_INVOICE_OPEN_EXEMPT = frozenset(
    {
        "models/collection_connector.py",
        "tools/customer_debt.py",
    }
)


def _sheet_open_gate_offenders(module_root):
    """Return production sheet-state ``"open"`` gate leftovers outside common."""
    offenders = []
    for folder in ("models", "tools"):
        for path in sorted((module_root / folder).glob("*.py")):
            rel = f"{folder}/{path.name}"
            if path.name == "collection_common.py" or rel in _INVOICE_OPEN_EXEMPT:
                continue
            for lineno, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), 1
            ):
                if _SHEET_OPEN_GATE_RE.search(line):
                    offenders.append(f"{rel}:{lineno}:{line.strip()}")
    return offenders


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
        if vals.get("document_type") != "unsupported" and "amount" not in vals:
            vals["amount"] = 100.0
        if (
            vals.get("document_type")
            in (
                "check",
                "echeck",
            )
            and "check_number" not in vals
        ):
            # check_number is mandatory at save for check/echeck
            # (_check_check_number_required); a random default keeps
            # existing fixtures unique enough to dodge
            # _check_check_number_unique without spelling one out.
            vals["check_number"] = f"CHK-{uuid4().hex[:10]}"
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

    def test_manifest_version_is_1_50_0(self):
        module_root = Path(__file__).resolve().parents[1]
        manifest = module_root / "__manifest__.py"
        manifest_text = manifest.read_text(encoding="utf-8")
        self.assertIn('"version": "19.0.1.50.0"', manifest_text)
        self.assertNotIn('"version": "19.0.1.47.0"', manifest_text)
        for leftover in (
            "19.0.1.26.0",
            "19.0.1.27.0",
            "19.0.1.29.0",
            "19.0.1.30.0",
            "19.0.1.35.0",
            "19.0.1.36.0",
            "19.0.1.37.0",
            "19.0.1.38.0",
            "19.0.1.39.0",
            "19.0.1.40.1",
            "19.0.1.41.0",
            "19.0.1.42.0",
            "19.0.1.44.0",
            "19.0.1.45.0",
            "19.0.1.47.0",
            "19.0.1.49.0",
        ):
            self.assertFalse(
                (module_root / "migrations" / leftover).exists(),
                f"No migrations/{leftover}/ folder",
            )
        migrate_146 = module_root / "migrations" / "19.0.1.46.0" / "post-migrate.py"
        self.assertTrue(
            migrate_146.is_file(), "Need 19.0.1.46.0 cash_on_hand recompute"
        )
        text_146 = migrate_146.read_text(encoding="utf-8")
        self.assertIn("cash_on_hand", text_146)
        self.assertIn("add_to_compute", text_146)
        migrate_148 = module_root / "migrations" / "19.0.1.48.0" / "post-migrate.py"
        self.assertTrue(migrate_148.is_file(), "Need 19.0.1.48.0 allow-list union")
        text_148 = migrate_148.read_text(encoding="utf-8")
        self.assertIn("_collection_enable_all_document_types", text_148)
        self.assertNotIn("_collection_seed_allowed_document_types", text_148)
        self.assertNotIn("backfill", text_148.lower())
        self.assertNotIn("commission_withheld", text_148)
        migrate_143 = module_root / "migrations" / "19.0.1.43.0" / "post-migrate.py"
        self.assertTrue(migrate_143.is_file(), "Need 19.0.1.43.0 allow-list union")
        text_143 = migrate_143.read_text(encoding="utf-8")
        self.assertIn("_collection_enable_all_document_types", text_143)
        self.assertNotIn("_collection_seed_allowed_document_types", text_143)
        migrate_140 = module_root / "migrations" / "19.0.1.40.0" / "post-migrate.py"
        self.assertTrue(migrate_140.is_file(), "Need 19.0.1.40.0 allow-list union")
        text_140 = migrate_140.read_text(encoding="utf-8")
        self.assertIn("_collection_enable_all_document_types", text_140)
        self.assertNotIn("_collection_seed_allowed_document_types", text_140)
        migrate_128 = module_root / "migrations" / "19.0.1.28.0" / "post-migrate.py"
        self.assertTrue(migrate_128.is_file(), "Need 19.0.1.28.0 allocation remap")
        text_128 = migrate_128.read_text(encoding="utf-8")
        self.assertIn("THEN 'draft'", text_128)
        self.assertIn("THEN 'confirmed'", text_128)
        self.assertIn("'validated'", text_128)
        self.assertNotIn("CA/", text_128)
        self.assertNotIn("_collection_copy_sequences", text_128)
        migrate_131 = module_root / "migrations" / "19.0.1.31.0" / "post-migrate.py"
        self.assertTrue(migrate_131.is_file(), "Need 19.0.1.31.0 voucher state remap")
        text_131 = migrate_131.read_text(encoding="utf-8")
        self.assertIn("UPDATE collection_voucher", text_131)
        self.assertIn("THEN 'draft'", text_131)
        self.assertIn("THEN 'validated_collections'", text_131)
        self.assertIn("'pending'", text_131)
        self.assertIn("'approved'", text_131)
        self.assertIn("'rejected'", text_131)
        self.assertNotIn("UPDATE collection_voucher_review_snapshot", text_131)
        migrate_132 = module_root / "migrations" / "19.0.1.32.0" / "post-migrate.py"
        self.assertTrue(migrate_132.is_file(), "Need 19.0.1.32.0 residual_reason drop")
        text_132 = migrate_132.read_text(encoding="utf-8")
        self.assertIn("DROP", text_132)
        self.assertIn("residual_reason", text_132)
        self.assertIn("collection_allocation", text_132)
        self.assertIn("collection_allocation_revision", text_132)
        migrate_133 = module_root / "migrations" / "19.0.1.33.0" / "post-migrate.py"
        self.assertTrue(migrate_133.is_file(), "Need 19.0.1.33.0 reassign XMLID unlink")
        text_133 = migrate_133.read_text(encoding="utf-8")
        self.assertIn("view_collection_voucher_reassign_kanban", text_133)
        self.assertIn("ir_ui_view", text_133)
        self.assertIn("ir_model_data", text_133)
        self.assertNotIn("UPDATE collection_sheet", text_133)
        self.assertNotIn("THEN 'proposal'", text_133)
        self.assertNotIn("THEN 'cancelled'", text_133)
        migrate_134 = module_root / "migrations" / "19.0.1.34.0" / "post-migrate.py"
        self.assertTrue(migrate_134.is_file(), "Need 19.0.1.34.0 additive migrate")
        text_134 = migrate_134.read_text(encoding="utf-8")
        self.assertIn("def migrate", text_134)
        self.assertNotIn("INSERT INTO collection_receipt", text_134)
        self.assertNotIn("INSERT INTO collection_receipt_value", text_134)
        self.assertNotIn("INSERT INTO collection.receipt", text_134)

    def test_upgrade_134_does_not_backfill_receipts(self):
        """Upgrade to 19.0.1.34.0 MUST add tables and MUST NOT backfill receipts."""
        seller = ensure_enabled_seller(self.env)
        partner = dummy_customer_partner(self.env, customer="MIG-RCPT")
        sheet = self.env["collection.sheet"].create({"seller_id": seller.id})
        voucher = self._create_voucher(
            {
                "document_type": "bank_transfer",
                "seller_id": seller.id,
                "sheet_id": sheet.id,
                "amount": 40.0,
                "partner_id": partner.id,
            }
        )
        allocation = self.env["collection.allocation"].create(
            {
                "sheet_id": sheet.id,
                "partner_id": partner.id,
                "voucher_ids": [(6, 0, [voucher.id])],
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "external_invoice_id": "MIG-INV-1",
                            "invoice_number": "M-1",
                            "invoice_balance": 40.0,
                            "amount_applied": 40.0,
                        },
                    )
                ],
            }
        )
        self.assertFalse(allocation.receipt_ids)
        self.env.cr.execute("SELECT to_regclass('public.collection_receipt')")
        self.assertTrue(self.env.cr.fetchone()[0])
        self.env.cr.execute("SELECT to_regclass('public.collection_receipt_value')")
        self.assertTrue(self.env.cr.fetchone()[0])
        migrate_path = (
            Path(__file__).resolve().parents[1]
            / "migrations"
            / "19.0.1.34.0"
            / "post-migrate.py"
        )
        spec = spec_from_file_location("collection_receipts_post_migrate", migrate_path)
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        module.migrate(self.env.cr, "19.0.1.33.0")
        self.env.invalidate_all()
        leftover = self.env["collection.allocation"].browse(allocation.id)
        self.assertTrue(leftover.exists())
        self.assertFalse(leftover.receipt_ids)
        self.assertTrue(voucher.exists())

    def test_remaining_tests_drop_two_state_leftovers(self):
        """Remaining tests MUST NOT expect Close/Reopen or a two-/four-state bar."""
        tests_dir = Path(__file__).resolve().parent
        leftovers = []
        for path in sorted(tests_dir.glob("test_*.py")):
            if path.name == Path(__file__).name:
                continue
            for lineno, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), 1
            ):
                stripped = line.strip()
                if 'statusbar_visible"), "open,closed"' in stripped:
                    leftovers.append(f"{path.name}:{lineno}: two-state statusbar")
                if '"open,proposal,closed,cancelled"' in stripped:
                    leftovers.append(f"{path.name}:{lineno}: four-state statusbar")
                if '{"open", "proposal", "closed", "cancelled"}' in stripped:
                    leftovers.append(f"{path.name}:{lineno}: four-state selection")
                if "Sheet state can only be changed via Close or Reopen" in stripped:
                    leftovers.append(f"{path.name}:{lineno}: Close or Reopen error")
                if "action_reopen()" in stripped and not any(
                    token in stripped
                    for token in ("hasattr", "assertNotIn", "assertFalse")
                ):
                    leftovers.append(f"{path.name}:{lineno}: {stripped}")
        self.assertFalse(leftovers, leftovers)

    def test_agents_md_five_state_workflow(self):
        """AGENTS.md MUST document five-state Selection/UI and the leftover pin."""
        agents = (Path(__file__).resolve().parents[1] / "AGENTS.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Module metadata `19.0.1.50.0`", agents)
        self.assertNotIn("Module metadata `19.0.1.47.0`", agents)
        self.assertIn("`migrations/19.0.1.33.0/`", agents)
        self.assertIn("`migrations/19.0.1.43.0/`", agents)
        self.assertIn("`migrations/19.0.1.48.0/`", agents)
        self.assertIn(
            "`open`/`submitted`/`proposal`/`closed`/`cancelled`",
            agents,
        )
        self.assertIn("Submitted by Seller", agents)
        self.assertIn("Rendida", agents)
        self.assertIn("open,submitted,proposal,closed,cancelled", agents)
        self.assertIn(
            "Do **not** add `migrations/19.0.1.42.0/`",
            " ".join(agents.split()),
        )
        self.assertIn(
            "Do **not** add `migrations/19.0.1.44.0/`",
            " ".join(agents.split()),
        )
        self.assertIn(
            "Do **not** add `migrations/19.0.1.45.0/`",
            " ".join(agents.split()),
        )
        self.assertIn(
            "Do **not** add `migrations/19.0.1.47.0/`",
            " ".join(agents.split()),
        )
        self.assertIn(
            "Do **not** add `migrations/19.0.1.49.0/`",
            " ".join(agents.split()),
        )
        self.assertIn("`migrations/19.0.1.46.0/`", agents)
        self.assertIn("`CONFIRM_REVIEW_EXEMPT_TYPES`", agents)
        self.assertIn("`CASH_REPLACEMENT_TYPES`", agents)
        self.assertIn("`collection_seller_commission_mint`", agents)
        self.assertIn("`seller_commission`", agents)
        self.assertIn("`collection.partner_seller_commission`", agents)
        self.assertNotIn("dispatches connector `create_receipt`", agents)
        self.assertIn(
            "MUST NOT consult the connector",
            " ".join(agents.split()),
        )
        self.assertIn(
            "MUST NOT call `create_receipt`",
            " ".join(agents.split()),
        )
        self.assertIn("`draft`/`closed`/`issued`", agents)
        self.assertIn("reopens local `closed` receipts", agents)
        self.assertIn("freeze create", " ".join(agents.split()))
        self.assertIn("`close_collection_sheet`", agents)
        self.assertIn("`action_seller_close`", agents)
        self.assertIn("Confirm/Close/Cancel/Open", agents)
        self.assertIn("Allocations, Vouchers, and Debt", " ".join(agents.split()))
        self.assertIn("one-open still `open` only", " ".join(agents.split()))
        self.assertNotIn("action_reopen", agents)
        self.assertNotIn("**Reassign Customers**", agents)
        self.assertNotIn("Keep reassign kanban", agents)
        self.assertNotIn("Allocations-only", agents)
        self.assertNotIn("Module metadata `19.0.1.34.0`", agents)
        self.assertNotIn("Module metadata `19.0.1.35.0`", agents)
        self.assertNotIn("Module metadata `19.0.1.36.0`", agents)
        self.assertNotIn("Module metadata `19.0.1.37.0`", agents)
        self.assertNotIn("Module metadata `19.0.1.38.0`", agents)
        self.assertNotIn("Module metadata `19.0.1.39.0`", agents)
        self.assertNotIn("Module metadata `19.0.1.40.1`", agents)
        self.assertNotIn("Module metadata `19.0.1.40.0`", agents)
        self.assertNotIn("`partner_id.group_expand`", agents)
        self.assertIn(
            '"Closed collection sheets cannot change membership. Reopen first."',
            agents,
        )
        self.assertIn("`migrations/19.0.1.32.0/`", agents)

    def test_readme_description_five_state_workflow(self):
        """readme/DESCRIPTION.md MUST describe five-state sheets and three tabs."""
        description = (
            Path(__file__).resolve().parents[1] / "readme" / "DESCRIPTION.md"
        ).read_text(encoding="utf-8")
        self.assertIn("`open`", description)
        self.assertIn("`submitted`", description)
        self.assertIn("Submitted by Seller", description)
        self.assertIn("Rendida", description)
        self.assertIn("`proposal`", description)
        self.assertIn("`closed`", description)
        self.assertIn("`cancelled`", description)
        self.assertIn("Allocations, Vouchers, and Debt", description)
        self.assertIn("seller_commission", description)
        self.assertNotIn("(`open`/`closed`)", description)
        self.assertNotIn("Reassign Customers", description)
        self.assertNotIn("Reopen", description)

    def test_sheet_selection_includes_dormant_submitted(self):
        """Sheet state Selection MUST include dormant Submitted by Seller."""
        selection = self.env["collection.sheet"]._fields["state"].selection
        self.assertEqual(
            selection,
            [
                ("open", "Open"),
                ("submitted", "Submitted by Seller"),
                ("proposal", "Proposal"),
                ("closed", "Closed"),
                ("cancelled", "Cancelled"),
            ],
        )
        self.assertNotIn("submitted", dict(selection).get("open", ""))

    def test_sheet_report_labels_include_rendida(self):
        """PDF labels MUST map submitted to Rendida and keep the four Spanish labels."""
        from odoo.addons.collection.models.collection_sheet_report import (
            _SHEET_STATE_LABELS,
        )

        self.assertEqual(_SHEET_STATE_LABELS.get("submitted"), "Rendida")
        self.assertEqual(
            _SHEET_STATE_LABELS,
            {
                "open": "Abierta",
                "submitted": "Rendida",
                "proposal": "Propuesta",
                "closed": "Cerrada",
                "cancelled": "Cancelada",
            },
        )

    def test_sheet_form_statusbar_is_five_state(self):
        """Sheet form statusbar MUST list submitted between open and proposal."""
        views = (
            Path(__file__).resolve().parents[1] / "views" / "collection_views.xml"
        ).read_text(encoding="utf-8")
        self.assertIn(
            'statusbar_visible="open,submitted,proposal,closed,cancelled"',
            views,
        )
        self.assertNotIn(
            'statusbar_visible="open,proposal,closed,cancelled"',
            views,
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
            NINE_TYPE_CODES,
        )
        self.assertIn(extra, self.env.company.allowed_document_type_ids)
        self.assertEqual(
            set(self.env.company.allowed_document_type_ids.mapped("code")),
            NINE_TYPE_CODES | {"wire_mig"},
        )

    def test_upgrade_140_unions_three_types_keeps_extras(self):
        """1.40.0 MUST union echeck/cash/retention_certificate and keep extras."""
        migrate_path = (
            Path(__file__).resolve().parents[1]
            / "migrations"
            / "19.0.1.40.0"
            / "post-migrate.py"
        )
        self.assertTrue(migrate_path.is_file(), "Need 19.0.1.40.0 allow-list union")
        text = migrate_path.read_text(encoding="utf-8")
        self.assertIn("_collection_enable_all_document_types", text)
        self.assertNotIn("_collection_seed_allowed_document_types", text)
        extra = self.env["collection.document.type"].create(
            {"code": "wire_140", "name": "Wire 140"}
        )
        four_ids = [
            self.env.ref(f"collection.document_type_{code}").id
            for code in ("bank_transfer", "check", "cash_deposit", "unsupported")
        ]
        company_b = self._create_company("Union Types Co B")
        company_b.write({"allowed_document_type_ids": [(6, 0, four_ids + [extra.id])]})
        spec = spec_from_file_location("collection_140_post_migrate", migrate_path)
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        module.migrate(self.env.cr, "19.0.1.39.0")
        self.env.invalidate_all()
        codes = set(company_b.allowed_document_type_ids.mapped("code"))
        self.assertEqual(codes, NINE_TYPE_CODES | {"wire_140"})
        self.assertIn(extra, company_b.allowed_document_type_ids)

    def test_upgrade_143_unions_seller_deposit_keeps_extras(self):
        """1.43.0 MUST union seller_deposit and keep extras. No 19.0.1.42.0/."""
        module_root = Path(__file__).resolve().parents[1]
        self.assertFalse(
            (module_root / "migrations" / "19.0.1.42.0").exists(),
            "leftover pin still forbids migrations/19.0.1.42.0/",
        )
        migrate_path = module_root / "migrations" / "19.0.1.43.0" / "post-migrate.py"
        self.assertTrue(migrate_path.is_file(), "Need 19.0.1.43.0 allow-list union")
        text = migrate_path.read_text(encoding="utf-8")
        self.assertIn("_collection_enable_all_document_types", text)
        self.assertNotIn("_collection_seed_allowed_document_types", text)
        extra = self.env["collection.document.type"].create(
            {"code": "wire_143", "name": "Wire 143"}
        )
        seven_ids = [
            self.env.ref(f"collection.document_type_{code}").id
            for code in SEVEN_TYPE_CODES
        ]
        company_b = self._create_company("Union Seller Deposit Co B")
        company_b.write({"allowed_document_type_ids": [(6, 0, seven_ids + [extra.id])]})
        self.assertEqual(
            set(company_b.allowed_document_type_ids.mapped("code")),
            SEVEN_TYPE_CODES | {"wire_143"},
        )
        spec = spec_from_file_location("collection_143_post_migrate", migrate_path)
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        module.migrate(self.env.cr, "19.0.1.42.0")
        self.env.invalidate_all()
        codes = set(company_b.allowed_document_type_ids.mapped("code"))
        self.assertEqual(codes, NINE_TYPE_CODES | {"wire_143"})
        self.assertIn(extra, company_b.allowed_document_type_ids)
        self.assertIn("seller_deposit", codes)

    def test_upgrade_148_unions_seller_commission_keeps_extras(self):
        """1.48.0 MUST union seller_commission and keep extras. No 19.0.1.49.0/."""
        module_root = Path(__file__).resolve().parents[1]
        self.assertFalse(
            (module_root / "migrations" / "19.0.1.49.0").exists(),
            "leftover pin still forbids migrations/19.0.1.49.0/",
        )
        migrate_path = module_root / "migrations" / "19.0.1.48.0" / "post-migrate.py"
        self.assertTrue(migrate_path.is_file(), "Need 19.0.1.48.0 allow-list union")
        text = migrate_path.read_text(encoding="utf-8")
        self.assertIn("_collection_enable_all_document_types", text)
        self.assertNotIn("_collection_seed_allowed_document_types", text)
        extra = self.env["collection.document.type"].create(
            {"code": "wire_148", "name": "Wire 148"}
        )
        eight_ids = [
            self.env.ref(f"collection.document_type_{code}").id
            for code in EIGHT_TYPE_CODES
        ]
        company_b = self._create_company("Union Seller Commission Co B")
        company_b.write({"allowed_document_type_ids": [(6, 0, eight_ids + [extra.id])]})
        self.assertEqual(
            set(company_b.allowed_document_type_ids.mapped("code")),
            EIGHT_TYPE_CODES | {"wire_148"},
        )
        spec = spec_from_file_location("collection_148_post_migrate", migrate_path)
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        module.migrate(self.env.cr, "19.0.1.47.0")
        self.env.invalidate_all()
        codes = set(company_b.allowed_document_type_ids.mapped("code"))
        self.assertEqual(codes, NINE_TYPE_CODES | {"wire_148"})
        self.assertIn(extra, company_b.allowed_document_type_ids)
        self.assertIn("seller_commission", codes)

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
        force_sheet_state(
            self.env["collection.sheet"].search([("state", "=", "open")]),
            "closed",
        )
        seller = ensure_enabled_seller(self.env)
        sheet_a = self.env["collection.sheet"].create({"seller_id": seller.id})
        sheet_b = self.env["collection.sheet"].create(
            {"seller_id": seller_b.id, "company_id": company_b.id}
        )
        n_sheet_a = self._seq_number(sheet_a.name, "CS")
        self.assertEqual(self._seq_number(sheet_b.name, "CS"), 1)
        force_sheet_state(sheet_a, "closed")
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
            NINE_TYPE_CODES,
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

    def test_sheet_state_open_gates_live_only_in_collection_common(self):
        """Sheet-state ``"open"`` gates MUST NOT appear outside collection_common."""
        module_root = Path(__file__).resolve().parents[1]
        common = (module_root / "models" / "collection_common.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("DRAFT_SHEET_STATES", common)
        offenders = _sheet_open_gate_offenders(module_root)
        self.assertFalse(offenders, offenders)

    def test_invoice_open_is_exempt_from_sheet_open_scan(self):
        """Invoice connector state ``open`` MUST remain and MUST NOT fail the scan."""
        module_root = Path(__file__).resolve().parents[1]
        connector = (module_root / "models" / "collection_connector.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('frozenset({"open", "overdue"})', connector)
        debt = (module_root / "tools" / "customer_debt.py").read_text(encoding="utf-8")
        self.assertIn('if state == "open":', debt)
        offenders = _sheet_open_gate_offenders(module_root)
        self.assertFalse(
            [
                row
                for row in offenders
                if row.startswith("models/collection_connector.py")
            ]
        )
        self.assertFalse(
            [row for row in offenders if row.startswith("tools/customer_debt.py")]
        )
        self.assertFalse(
            [row for row in offenders if row.startswith("models/collection_common.py")]
        )

    def test_seller_and_admin_editable_sets_are_open_only(self):
        """Named sets MUST widen admin/draft for submitted; seller stays open-only."""
        from odoo.addons.collection.models.collection_common import (
            ADMIN_EDITABLE_SHEET_STATES,
            CONFIRMED_SHEET_STATE,
            DRAFT_SHEET_STATES,
            FROZEN_SHEET_STATES,
            SELLER_DECLARATION_STATES,
            SELLER_SHEET_STATES,
        )

        self.assertEqual(SELLER_SHEET_STATES, frozenset({"open"}))
        self.assertEqual(ADMIN_EDITABLE_SHEET_STATES, frozenset({"open", "submitted"}))
        self.assertEqual(SELLER_DECLARATION_STATES, frozenset({"submitted"}))
        self.assertEqual(
            DRAFT_SHEET_STATES,
            frozenset({"open", "submitted", "proposal", "cancelled"}),
        )
        self.assertEqual(CONFIRMED_SHEET_STATE, "closed")
        self.assertEqual(FROZEN_SHEET_STATES, frozenset({"closed", "cancelled"}))
        self.assertNotIn("submitted", SELLER_SHEET_STATES)
        self.assertIn("submitted", ADMIN_EDITABLE_SHEET_STATES)
        self.assertIn("submitted", DRAFT_SHEET_STATES)
        self.assertIn("submitted", SELLER_DECLARATION_STATES)

    def test_force_sheet_state_writes_closed_without_confirm(self):
        """force_sheet_state MUST close an open sheet without Confirm."""
        from .common_connector import force_sheet_state

        seller = ensure_enabled_seller(self.env)
        sheet = self.env["collection.sheet"].create({"seller_id": seller.id})
        self.assertEqual(sheet.state, "open")
        force_sheet_state(sheet, "closed")
        self.assertEqual(sheet.state, "closed")

    def test_advance_sheet_to_reaches_proposal_via_confirm(self):
        """advance_sheet_to MUST Confirm an empty open sheet to proposal."""
        from .common_connector import advance_sheet_to

        seller = ensure_enabled_seller(self.env)
        sheet = self.env["collection.sheet"].create({"seller_id": seller.id})
        self.assertEqual(sheet.state, "open")
        advance_sheet_to(sheet, "proposal")
        self.assertEqual(sheet.state, "proposal")
