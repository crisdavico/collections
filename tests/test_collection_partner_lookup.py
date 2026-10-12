# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests import TransactionCase
from odoo.tools import mute_logger

from .common_connector import install_bound_test_connector, install_test_connector_type
from .test_collection_payment import create_internal_seller

_CUIT = "20-11111111-1"
_UNAVAILABLE = "The requested customer is not available."


class TestCollectionPartnerLookup(TransactionCase):
    """Lazy customer resolution matches the commercial partner by CUIT digits."""

    def setUp(self):
        super().setUp()
        install_test_connector_type(self)
        self.seller = create_internal_seller(self.env, "partner_lookup_seller")
        self.connector = install_bound_test_connector(self, self.seller)
        self.Partner = self.env["res.partner"].with_context(
            tracking_disable=True, mail_create_nolog=True, mail_notrack=True
        )

    def _partner(self, name, vat=None, parent=None, is_company=True):
        vals = {"name": name, "is_company": is_company and not parent}
        if vat is not None:
            vals["vat"] = vat
        if parent:
            vals["parent_id"] = parent.id
        if "autopost_bills" in self.Partner._fields:
            vals["autopost_bills"] = "ask"
        return self.Partner.create(vals)

    def _resolve(self):
        return self.connector.resolve_customer_partner(self.seller.id, _CUIT)

    def _partner_count(self):
        return self.env["res.partner"].search_count([])

    def test_digits_only_vat_matches_the_dashed_cuit(self):
        """The localization stores 20111111111; the ERP answers 20-11111111-1."""
        stored = self._partner("Digits SA", "20111111111")
        before = self._partner_count()
        self.assertEqual(self._resolve(), stored)
        self.assertEqual(self._partner_count(), before)

    def test_dashed_vat_matches_too(self):
        stored = self._partner("Dashes SA", _CUIT)
        self.assertEqual(self._resolve(), stored)

    def test_contacts_sharing_the_vat_do_not_make_it_ambiguous(self):
        """Odoo copies the VAT to contacts: only the commercial partner counts."""
        company = self._partner("Parent SA", "20111111111")
        contact = self._partner("Contact", parent=company, is_company=False)
        self.assertEqual(contact.vat, company.vat)
        self.assertEqual(self._resolve(), company)

    def test_two_commercial_partners_stay_ambiguous(self):
        self._partner("Twin One", "20111111111")
        self._partner("Twin Two", _CUIT)
        with self.assertRaises(UserError) as ctx:
            self._resolve()
        self.assertEqual(str(ctx.exception), _UNAVAILABLE)

    def test_other_binding_conflict_is_the_generic_error(self):
        """A partner already bound under another identification is refused cleanly."""
        partner = self._partner("Bound Elsewhere", "20111111111")
        self.env["collection.connector.customer.binding"].create(
            {
                "connector_id": self.connector.id,
                "external_customer_id": "someone-else",
                "identification": "27-99999999-9",
                "partner_id": partner.id,
            }
        )
        with mute_logger("odoo.sql_db"), self.assertRaises(UserError) as ctx:
            self._resolve()
        self.assertEqual(str(ctx.exception), _UNAVAILABLE)
