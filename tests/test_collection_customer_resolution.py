# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import inspect
from unittest.mock import patch

from psycopg2.errors import UniqueViolation

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import TransactionCase

from .common_connector import TEST_CONNECTOR_TYPE, install_test_connector_type
from .test_collection_payment import (
    create_collection_user,
    create_internal_seller,
    ensure_enabled_seller,
)

BINDING = "collection.connector.customer.binding"
CUSTOMER_UNAVAILABLE = "The requested customer is not available."
DOCUMENT_CONFLICT = "Payment document_id conflict could not be resolved."
IDENT = "20-11111111-1"


class TestCollectionCustomerResolution(TransactionCase):
    """resolve_customer_partner gate, fast path, D3 vat, nested UniqueViolation."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        install_test_connector_type(cls)
        cls.seller = create_internal_seller(cls.env, "collection_resolve_seller")
        cls.internal_user = create_collection_user(cls.env, "collection_resolve_user")

    def setUp(self):
        super().setUp()
        install_test_connector_type(self)
        self.connector = self.env["collection.connector"].create(
            {"name": "Resolve Customer Connector", "type": TEST_CONNECTOR_TYPE}
        )
        self.env.company.write({"collection_connector_id": self.connector.id})
        ensure_enabled_seller(self.env, self.seller)
        self.env["collection.connector.seller.binding"].create(
            {
                "connector_id": self.connector.id,
                "external_seller_id": "ext-bound",
                "user_id": self.seller.id,
            }
        )

    def _create_partner(self, name, vat=None, **extra):
        Partner = self.env["res.partner"].with_context(
            tracking_disable=True,
            mail_create_nolog=True,
            mail_notrack=True,
            mail_create_nosubscribe=True,
        )
        vals = {"name": name, **extra}
        if vat:
            vals["vat"] = vat
        if "autopost_bills" in Partner._fields:
            vals["autopost_bills"] = "ask"
            return Partner.create(vals)
        self.env.cr.execute(
            """
            SELECT 1 FROM information_schema.columns
             WHERE table_name = 'res_partner' AND column_name = 'autopost_bills'
            """
        )
        if not self.env.cr.fetchone():
            return Partner.create(vals)
        self.env.cr.execute(
            """
            INSERT INTO res_partner (
                name, email, vat, company_id, customer_rank,
                active, complete_name, type, autopost_bills,
                create_uid, write_uid, create_date, write_date
            )
            VALUES (
                %s, %s, %s, %s, %s, true, %s, 'contact', 'ask',
                1, 1, (now() AT TIME ZONE 'UTC'), (now() AT TIME ZONE 'UTC')
            )
            RETURNING id
            """,
            (
                name,
                extra.get("email") or f"{name}@example.com",
                vat or None,
                extra.get("company_id"),
                extra.get("customer_rank") or 0,
                name,
            ),
        )
        partner = Partner.browse(self.env.cr.fetchone()[0])
        partner.invalidate_recordset()
        return partner

    def _create_binding(
        self, partner, identification=IDENT, external_id="cust-bound-active"
    ):
        return self.env[BINDING].create(
            {
                "connector_id": self.connector.id,
                "external_customer_id": external_id,
                "identification": identification,
                "partner_id": partner.id,
                "customer_code": "C-BOUND-1",
            }
        )

    def _resolve(self, identification, seller_id=None, connector=None):
        connector = connector or self.connector
        return connector.resolve_customer_partner(
            seller_id if seller_id is not None else self.seller.id,
            identification,
        )

    def _assert_unavailable(self, func):
        with self.assertRaises(UserError) as ctx:
            func()
        self.assertEqual(str(ctx.exception), CUSTOMER_UNAVAILABLE)
        self.assertNotIn(DOCUMENT_CONFLICT, str(ctx.exception))

    def _partner_rank(self, partner):
        """Return `customer_rank`, or None when `account` is not installed."""
        if "customer_rank" in partner._fields:
            return partner.customer_rank
        self.env.cr.execute(
            """
            SELECT 1 FROM information_schema.columns
             WHERE table_name = 'res_partner' AND column_name = 'customer_rank'
            """
        )
        if not self.env.cr.fetchone():
            return None
        self.env.cr.execute(
            "SELECT customer_rank FROM res_partner WHERE id = %s", (partner.id,)
        )
        return self.env.cr.fetchone()[0]

    def _assert_customer_rank_one(self, partner):
        """`customer_rank` belongs to `account`: assert it wherever it exists."""
        rank = self._partner_rank(partner)
        if rank is None:
            self.assertNotIn("customer_rank", partner._fields)
            return
        self.assertEqual(rank, 1)

    def _binding_count(self, identification=IDENT):
        return self.env[BINDING].search_count(
            [
                ("connector_id", "=", self.connector.id),
                ("identification", "=", identification),
            ]
        )

    def _spy_dispatch(self):
        ops = []
        orig = type(self.connector)._dispatch

        def wrapped(this, op, *args):
            ops.append(op)
            return orig(this, op, *args)

        return ops, wrapped

    def test_disabled_or_unbound_seller_raises_before_lookup(self):
        """Enabled Seller gate MUST run before binding lookup or adapter dispatch."""
        self._create_binding(self._create_partner("Already Bound", vat=IDENT))
        ops, wrapped = self._spy_dispatch()
        cases = {
            "not_enabled": lambda: self.env.company.write(
                {"enabled_seller_ids": [Command.unlink(self.seller.id)]}
            ),
            "not_bound": lambda: self.connector.seller_binding_ids.unlink(),
        }
        with patch.object(type(self.connector), "_dispatch", wrapped):
            for label, prepare in cases.items():
                with self.subTest(label=label):
                    prepare()
                    ops.clear()
                    before_partners = self.env["res.partner"].search_count(
                        [("vat", "=", IDENT)]
                    )
                    before_bindings = self._binding_count()
                    with self.assertRaises(UserError) as ctx:
                        self._resolve(IDENT)
                    self.assertNotEqual(str(ctx.exception), DOCUMENT_CONFLICT)
                    self.assertNotIn("list_customers", ops)
                    self.assertEqual(
                        self.env["res.partner"].search_count([("vat", "=", IDENT)]),
                        before_partners,
                    )
                    self.assertEqual(self._binding_count(), before_bindings)
                    ensure_enabled_seller(self.env, self.seller)
                    if not self.connector.seller_binding_ids:
                        self.env["collection.connector.seller.binding"].create(
                            {
                                "connector_id": self.connector.id,
                                "external_seller_id": "ext-bound",
                                "user_id": self.seller.id,
                            }
                        )

    def test_blank_identification_fails_closed_without_adapter(self):
        """Empty identification MUST raise the generic customer error before lookup."""
        ops, wrapped = self._spy_dispatch()
        before = self.env[BINDING].search_count(
            [("connector_id", "=", self.connector.id)]
        )
        with patch.object(type(self.connector), "_dispatch", wrapped):
            for value in (None, "", "   "):
                with self.subTest(value=value):
                    ops.clear()
                    self._assert_unavailable(lambda v=value: self._resolve(v))
                    self.assertNotIn("list_customers", ops)
        self.assertEqual(
            self.env[BINDING].search_count([("connector_id", "=", self.connector.id)]),
            before,
        )

    def test_binding_fast_path_skips_adapter(self):
        """Existing identification binding MUST return that partner without adapter."""
        partner = self._create_partner("Fast Path Partner", vat=IDENT)
        binding = self._create_binding(partner)
        ops, wrapped = self._spy_dispatch()
        with patch.object(type(self.connector), "_dispatch", wrapped):
            result = self._resolve(f"  {IDENT}  ")
        self.assertEqual(result, partner)
        self.assertEqual(result, binding.partner_id)
        self.assertNotIn("list_customers", ops)

    def test_unique_vat_binds_existing_partner(self):
        """Exactly one vat match MUST bind that partner and MUST NOT create another."""
        existing = self._create_partner("Existing Vat Partner", vat=IDENT)
        before = self.env["res.partner"].search_count([("vat", "=", IDENT)])
        result = self._resolve(IDENT)
        self.assertEqual(result, existing)
        self.assertEqual(
            self.env["res.partner"].search_count([("vat", "=", IDENT)]), before
        )
        binding = self.env[BINDING].search(
            [
                ("connector_id", "=", self.connector.id),
                ("identification", "=", IDENT),
            ]
        )
        self.assertEqual(len(binding), 1)
        self.assertEqual(binding.partner_id, existing)
        self.assertEqual(binding.external_customer_id, "cust-bound-active")
        self.assertEqual(binding.customer_code, "C-BOUND-1")
        self.assertFalse(existing.ref)

    def test_no_vat_match_creates_partner_and_binding(self):
        """Zero vat matches MUST create partner (vat, company, rank 1) and a binding."""
        before_vat = self.env["res.partner"].search_count([("vat", "=", IDENT)])
        result = self._resolve(
            IDENT, connector=self.connector.with_user(self.internal_user)
        )
        self.assertEqual(result.vat, IDENT)
        self.assertEqual(result.name, "Bound Active Customer")
        self.assertEqual(result.company_id, self.connector.company_id)
        self._assert_customer_rank_one(result)
        self.assertFalse(result.category_id)
        self.assertFalse(result.ref)
        self.assertEqual(
            self.env["res.partner"].search_count([("vat", "=", IDENT)]),
            before_vat + 1,
        )
        binding = self.env[BINDING].search(
            [
                ("connector_id", "=", self.connector.id),
                ("identification", "=", IDENT),
            ]
        )
        self.assertEqual(len(binding), 1)
        self.assertEqual(binding.partner_id, result)
        self.assertEqual(binding.customer_code, "C-BOUND-1")
        self.assertEqual(binding.external_customer_id, "cust-bound-active")
        company_model = type(self.env.company)
        self.assertTrue(hasattr(company_model, "_collection_create_partners"))
        self.assertFalse(hasattr(company_model, "_collection_create_seller_partners"))
        source = inspect.getsource(company_model._collection_create_partners)
        self.assertIn("vat", source)
        self.assertIn("company_id", source)
        self.assertIn("customer_rank", source)
        resolve_source = inspect.getsource(
            type(self.connector).resolve_customer_partner
        )
        self.assertNotIn("sudo()", resolve_source)
        self.assertNotIn(".sudo(", resolve_source)

    def test_no_cuit_normalize_creates_when_digits_differ(self):
        """VAT matching MUST use the exact stripped string, not CUIT normalize."""
        digits_only = self._create_partner("Digits Vat", vat="20111111111")
        result = self._resolve(IDENT)
        self.assertNotEqual(result, digits_only)
        self.assertEqual(result.vat, IDENT)
        self._assert_customer_rank_one(result)

    def test_ambiguous_vat_fails_closed(self):
        """More than one vat match MUST raise the generic error with no writes."""
        first = self._create_partner("Vat Twin A", vat=IDENT)
        second = self._create_partner("Vat Twin B", vat=IDENT)
        self.assertEqual(len(first | second), 2)
        before_bindings = self._binding_count()
        before_partners = self.env["res.partner"].search_count([("vat", "=", IDENT)])
        self._assert_unavailable(lambda: self._resolve(IDENT))
        self.assertEqual(self._binding_count(), before_bindings)
        self.assertEqual(
            self.env["res.partner"].search_count([("vat", "=", IDENT)]),
            before_partners,
        )

    def test_unknown_inactive_other_seller_fails_closed(self):
        """Unknown, inactive, or other-seller identification MUST fail closed."""
        before = self.env[BINDING].search_count(
            [("connector_id", "=", self.connector.id)]
        )
        cases = {
            "unknown": "NO-SUCH-ID",
            "inactive": "20-22222222-2",
            "other_seller": "20-33333333-3",
        }
        for label, identification in cases.items():
            with self.subTest(label=label):
                self._assert_unavailable(
                    lambda ident=identification: self._resolve(ident)
                )
                self.assertEqual(self._binding_count(identification), 0)
        self.assertEqual(
            self.env[BINDING].search_count([("connector_id", "=", self.connector.id)]),
            before,
        )

    def test_nested_unique_violation_converges_without_document_conflict(self):
        """Binding UniqueViolation MUST reuse the winner, not a document_id error."""
        winner = self._create_partner("Race Winner", vat=IDENT)
        winner_binding = self._create_binding(winner)
        BindingModel = type(self.env[BINDING])
        orig_search = BindingModel.search
        searches = {"n": 0}
        creates = {"n": 0}

        def search_wrapper(this, *args, **kwargs):
            searches["n"] += 1
            if searches["n"] == 1:
                return this.browse()
            return orig_search(this, *args, **kwargs)

        def create_wrapper(this, vals_list):
            creates["n"] += 1
            raise UniqueViolation()

        def invoke():
            try:
                return self._resolve(IDENT)
            except UniqueViolation as err:
                raise UserError(DOCUMENT_CONFLICT) from err

        with (
            patch.object(BindingModel, "search", search_wrapper),
            patch.object(BindingModel, "create", create_wrapper),
        ):
            result = invoke()
        self.assertTrue(creates["n"])
        self.assertEqual(result, winner)
        self.assertEqual(result, winner_binding.partner_id)
        self.assertEqual(self._binding_count(), 1)

    def test_unique_violation_without_winner_reraises(self):
        """Missing binding after UniqueViolation MUST re-raise, not document_id."""
        BindingModel = type(self.env[BINDING])

        def create_wrapper(this, vals_list):
            raise UniqueViolation()

        with patch.object(BindingModel, "create", create_wrapper):
            with self.assertRaises(UniqueViolation):
                self._resolve(IDENT)
        self.assertEqual(self._binding_count(), 0)
