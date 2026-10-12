# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import TransactionCase

from odoo.addons.collection.models.collection_common import ConnectorDataStaleError

from .common_connector import (
    TEST_STALE_MESSAGE,
    install_bound_test_connector,
    install_test_connector_type,
)
from .test_collection_payment import create_internal_seller, dummy_customer_partner

_IDENT = "20-11111111-1"
_AS_OF = datetime(2026, 10, 1, 12, 0, 0)


class TestCollectionDebtFreshness(TransactionCase):
    """Debt reads say when the figures were read and never hide stale data."""

    def setUp(self):
        super().setUp()
        install_test_connector_type(self)
        self.seller = create_internal_seller(self.env, "debt_freshness_seller")
        self.connector = install_bound_test_connector(self, self.seller)
        self.env.company.partner_id.tz = "America/Argentina/Buenos_Aires"
        self.partner = dummy_customer_partner(self.env, customer=_IDENT)
        self.env["collection.connector.customer.binding"].create(
            {
                "connector_id": self.connector.id,
                "external_customer_id": "cust-bound-active",
                "identification": _IDENT,
                "partner_id": self.partner.id,
                "customer_code": "C-BOUND-1",
            }
        )
        self.sheet = self.env["collection.sheet"].create({"seller_id": self.seller.id})

    def _allocation(self):
        """A saved allocation whose create does not read the connector."""
        return self.env["collection.allocation"].create(
            {
                "sheet_id": self.sheet.id,
                "partner_id": self.partner.id,
                "line_ids": [
                    Command.create(
                        {
                            "external_invoice_id": "inv-bound-overdue",
                            "invoice_number": "A-0001",
                            "invoice_amount": 100.0,
                            "invoice_balance": 100.0,
                            "invoice_state": "overdue",
                        }
                    )
                ],
            }
        )

    def test_payload_carries_the_adapter_time_in_the_company_timezone(self):
        """An adapter's naive UTC ``as_of`` comes back as ISO with the offset."""
        connector = self.connector.with_context(collection_test_as_of=_AS_OF)
        debt = connector.get_customer_debt(self.seller.id, _IDENT)
        self.assertEqual(debt["as_of"], "2026-10-01T09:00:00-03:00")

    def test_payload_of_a_live_adapter_is_stamped_at_read_time(self):
        """No adapter time means the figures are live: the read time stands."""
        before = fields.Datetime.now().replace(microsecond=0)
        debt = self.connector.get_customer_debt(self.seller.id, _IDENT)
        after = fields.Datetime.now()
        stamp = datetime.fromisoformat(debt["as_of"])
        self.assertEqual(stamp.utcoffset(), timedelta(hours=-3))
        naive_utc = (stamp - stamp.utcoffset()).replace(tzinfo=None)
        self.assertGreaterEqual(naive_utc, before)
        self.assertLessEqual(naive_utc, after)

    def test_mcp_customer_debt_carries_as_of(self):
        """The agent payload says when the debt was read."""
        mixin = self.env["muk_mcp.mixin"].with_context(collection_test_as_of=_AS_OF)
        payload = mixin.customer_debt(self.seller.id, _IDENT)
        self.assertEqual(payload["as_of"], "2026-10-01T09:00:00-03:00")
        self.assertNotIn("source", payload)

    def test_picker_shows_when_the_debt_was_read(self):
        """Add Debt shows the operator the time of the figures it offers."""
        allocation = self._allocation().with_context(collection_test_as_of=_AS_OF)
        action = allocation.action_open_debt_picker()
        picker = self.env["collection.allocation.debt.picker"].browse(action["res_id"])
        self.assertEqual(picker.debt_as_of, _AS_OF)
        self.assertEqual(
            set(picker.candidate_ids.mapped("external_invoice_id")),
            {"inv-bound-open"},
        )

    def test_stale_debt_reaches_the_picker_instead_of_an_empty_list(self):
        """Stale connector data is refused, not shown as "no debt"."""
        allocation = self._allocation().with_context(collection_test_stale=True)
        with self.assertRaises(ConnectorDataStaleError) as ctx:
            allocation.action_open_debt_picker()
        self.assertEqual(str(ctx.exception), TEST_STALE_MESSAGE)
        self.assertIsInstance(ctx.exception, UserError)

    def test_stale_debt_refuses_a_new_allocation_snapshot(self):
        """A UI allocation never snapshots stale debt into its lines."""
        Allocation = self.env["collection.allocation"].with_context(
            collection_test_stale=True
        )
        with self.assertRaises(ConnectorDataStaleError):
            Allocation.create(
                {"sheet_id": self.sheet.id, "partner_id": self.partner.id}
            )

    def test_other_connector_errors_still_leave_the_debt_empty(self):
        """An unknown customer keeps the old answer: nothing to add."""
        binding = self.env["collection.connector.customer.binding"].search(
            [("partner_id", "=", self.partner.id)]
        )
        binding.unlink()
        self.env["collection.connector.customer.binding"].create(
            {
                "connector_id": self.connector.id,
                "external_customer_id": "nobody",
                "identification": "NO-SUCH-CUSTOMER",
                "partner_id": self.partner.id,
            }
        )
        allocation = self._allocation()
        action = allocation.action_open_debt_picker()
        picker = self.env["collection.allocation.debt.picker"].browse(action["res_id"])
        self.assertFalse(picker.candidate_ids)
        self.assertFalse(picker.debt_as_of)
