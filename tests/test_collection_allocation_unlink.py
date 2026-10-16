# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date

from psycopg2 import IntegrityError

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import TransactionCase
from odoo.tools import mute_logger

from odoo.addons.collection.models.collection_common import privileged

from .common_connector import confirm_sheet
from .test_collection_payment import dummy_customer_partner, ensure_enabled_seller


class TestCollectionAllocationUnlink(TransactionCase):
    """Deleting an allocation MUST NOT silently drop ledger or audit rows."""

    def setUp(self):
        super().setUp()
        self.seller = ensure_enabled_seller(self.env)
        self.sheet = self.env["collection.sheet"].create({"seller_id": self.seller.id})
        self.partner = dummy_customer_partner(self.env, customer="CUST-UNLINK")
        self.voucher = self._voucher(self.partner, 100.0, "bank_transfer")
        self.allocation = self.env["collection.allocation"].create(
            {
                "sheet_id": self.sheet.id,
                "partner_id": self.partner.id,
                "voucher_ids": [Command.set(self.voucher.ids)],
                "line_ids": [
                    Command.create(
                        {
                            "external_invoice_id": "INV-UNLINK",
                            "invoice_number": "A-1",
                            "invoice_balance": 100.0,
                            "amount_applied": 100.0,
                        }
                    )
                ],
            }
        )
        self.receipt = self.env["collection.receipt"].create(
            {"allocation_id": self.allocation.id, "document_kind": "invoice"}
        )
        self.value = self.env["collection.receipt.value"].create(
            {
                "receipt_id": self.receipt.id,
                "voucher_id": self.voucher.id,
                "amount": 100.0,
            }
        )

    def _voucher(self, partner, amount, document_type, **extra):
        vals = {
            "partner_id": partner.id,
            "document_type": document_type,
            "amount": amount,
            "seller_id": self.seller.id,
            "sheet_id": self.sheet.id,
        }
        vals.update(extra)
        return self.env["collection.voucher"].create(vals)

    def _agent_request(self):
        """Record an agent request on the allocation, as the MCP tool does."""
        request_id = f"req-{self._testMethodName}"
        with privileged("collection_allocation_request"):
            self.allocation.write(
                {
                    "request_id": request_id,
                    "content_hash": "hash",
                    "request_log": {request_id: {"revision": 1}},
                }
            )

    def _cash_replacement(self):
        catalog = self.env.ref("collection.document_type_seller_deposit")
        self.env.company.write(
            {"allowed_document_type_ids": [Command.link(catalog.id)]}
        )
        cash = self._voucher(self.partner, 50.0, "cash")
        self.allocation.write({"voucher_ids": [Command.link(cash.id)]})
        self.env["collection.receipt.value"].create(
            {"receipt_id": self.receipt.id, "voucher_id": cash.id, "amount": 50.0}
        )
        deposit = self.env["collection.voucher"].create(
            {
                "document_type": "seller_deposit",
                "seller_id": self.seller.id,
                "sheet_id": self.sheet.id,
                "amount": 20.0,
                "voucher_number": f"SD-{self._testMethodName}",
                "voucher_date": date(2026, 9, 8),
            }
        )
        moved = self.env["collection.receipt.value"]._cash_replace(
            self.receipt, cash, deposit, 20.0
        )
        self.assertAlmostEqual(moved, 20.0, places=2)
        return deposit

    def _validate_members(self):
        with privileged("collection_audited_state"):
            self.sheet.voucher_ids.write({"state": "validated_collections"})

    def _assert_ledger_kept(self):
        self.assertTrue(self.allocation.exists())
        self.assertTrue(self.receipt.exists())
        self.assertTrue(self.value.exists())
        self.assertEqual(self.voucher.allocation_id, self.allocation)

    def test_draft_allocation_on_a_cancelled_sheet_cannot_be_deleted(self):
        """Cancelled sheets are frozen: their draft allocations stay."""
        self._validate_members()
        confirm_sheet(self.sheet)
        self.sheet.action_cancel()
        self.assertEqual(self.allocation.state, "draft")
        with self.assertRaises(UserError):
            self.allocation.unlink()
        self._assert_ledger_kept()

    def test_draft_allocation_on_a_proposal_sheet_cannot_be_deleted(self):
        """After Confirm the allocation set is what the sheet proposes."""
        self._validate_members()
        confirm_sheet(self.sheet)
        self.assertEqual(self.sheet.state, "proposal")
        with self.assertRaises(UserError):
            self.allocation.unlink()
        self._assert_ledger_kept()

    def test_issued_receipt_blocks_the_delete(self):
        """A receipt already sent to the ERP MUST survive."""
        with privileged("collection_receipt_issuing"):
            self.receipt.write({"state": "issued", "external_receipt_id": "ERP-1"})
        with self.assertRaises(UserError):
            self.allocation.unlink()
        self._assert_ledger_kept()
        self.assertEqual(self.receipt.external_receipt_id, "ERP-1")

    def test_cash_swap_does_not_block_the_delete(self):
        """A cash swap on its receipt MUST NOT pin the draft allocation."""
        deposit = self._cash_replacement()
        receipt_id = self.receipt.id
        self.allocation.unlink()
        self.assertFalse(self.allocation.exists())
        self.assertFalse(self.env["collection.receipt"].browse(receipt_id).exists())
        self.assertTrue(deposit.exists())
        self.assertFalse(deposit.receipt_value_ids)

    def test_agent_request_does_not_block_the_delete(self):
        """An allocation the agent wrote MUST delete like any draft allocation."""
        self._agent_request()
        self.allocation.unlink()
        self.assertFalse(self.allocation.exists())
        self.assertTrue(self.voucher.exists())
        self.assertFalse(self.voucher.allocation_id)

    def test_open_sheet_delete_takes_receipts_and_values_along(self):
        """A plain draft allocation on an open sheet still deletes cleanly."""
        receipt_id, value_id = self.receipt.id, self.value.id
        self.allocation.unlink()
        self.assertFalse(self.env["collection.receipt"].browse(receipt_id).exists())
        self.assertFalse(self.env["collection.receipt.value"].browse(value_id).exists())
        self.assertTrue(self.voucher.exists())
        self.assertFalse(self.voucher.allocation_id)

    def test_submitted_sheet_delete_is_allowed(self):
        """Submitted sheets are still edited by the back office."""
        self._validate_members()
        self.sheet.action_seller_close()
        self.assertEqual(self.sheet.state, "submitted")
        allocation_id = self.allocation.id
        self.allocation.unlink()
        self.assertFalse(
            self.env["collection.allocation"].browse(allocation_id).exists()
        )
        self.assertFalse(self.voucher.allocation_id)

    def test_sheet_delete_takes_an_agent_allocation_along(self):
        """Deleting an open sheet MUST also delete an agent-written allocation."""
        self._agent_request()
        self.sheet.unlink()
        self.assertFalse(self.sheet.exists())
        self.assertFalse(self.allocation.exists())
        self.assertTrue(self.voucher.exists())

    def test_receipt_delete_takes_its_values_along(self):
        """A draft receipt on an open sheet removes its values explicitly."""
        value_id = self.value.id
        self.allocation.write({"receipt_ids": [Command.delete(self.receipt.id)]})
        self.assertFalse(self.receipt.exists())
        self.assertFalse(self.env["collection.receipt.value"].browse(value_id).exists())

    def test_receipt_with_a_cash_swap_can_be_rebuilt(self):
        """Rebuilding receipts MUST NOT be blocked by a cash swap on them."""
        self._cash_replacement()
        self.allocation.write({"receipt_ids": [Command.clear()]})
        self.assertFalse(self.receipt.exists())

    def test_receipt_values_restrict_their_parent_delete(self):
        """The database itself MUST refuse to cascade receipt values."""
        self.assertEqual(
            self.env["collection.receipt.value"]._fields["receipt_id"].ondelete,
            "restrict",
        )
        self.env.flush_all()
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self.env.cr.execute(
                    "DELETE FROM collection_allocation WHERE id = %s",
                    [self.allocation.id],
                )
