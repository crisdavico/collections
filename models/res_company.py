# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools.translate import _

COLLECTION_SEQUENCE_SPECS = (
    ("collection.voucher", "Payment Voucher", "COL/%(year)s/", 4),
    ("collection.sheet", "Collection Sheet", "CS/%(year)s/", 4),
)
COLLECTION_TYPE_CODES = (
    "bank_transfer",
    "check",
    "cash_deposit",
    "unsupported",
)


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def _default_allowed_document_type_ids(self):
        return self.env["collection.document.type"].search([])

    document_review_enabled = fields.Boolean(default=False)
    enabled_seller_ids = fields.Many2many(
        comodel_name="res.users",
        relation="res_company_collection_enabled_seller_rel",
        column1="company_id",
        column2="user_id",
        string="Enabled Sellers",
        domain=[("share", "=", False)],
    )
    auto_create_sheet = fields.Boolean(default=True)
    allowed_document_type_ids = fields.Many2many(
        comodel_name="collection.document.type",
        relation="res_company_collection_allowed_document_type_rel",
        column1="company_id",
        column2="document_type_id",
        string="Allowed Document Types",
        default=_default_allowed_document_type_ids,
    )

    @api.private
    def _assert_new_work(self, seller, document_type=None):
        """Reject NEW work when seller or type is missing, empty, or not allowed."""
        self.ensure_one()
        seller_record = seller
        if seller and not isinstance(seller, models.Model):
            seller_record = self.env["res.users"].browse(seller)
        if not seller_record:
            raise UserError(_("A seller is required."))
        if seller_record not in self.enabled_seller_ids:
            raise UserError(_("Seller is not enabled for this company."))
        if document_type is not None:
            allowed_codes = set(self.allowed_document_type_ids.mapped("code"))
            if document_type not in allowed_codes:
                raise UserError(_("Document type is not allowed for this company."))

    @api.model
    @api.private
    def _document_review_enabled(self):
        return bool(self.env.company.document_review_enabled)

    @api.model
    def _collection_seed_allowed_document_types(self):
        """Enable all catalog types on companies that have none yet."""
        types = self.env["collection.document.type"].search([])
        if not types:
            return True
        companies = self.search([("allowed_document_type_ids", "=", False)])
        if companies:
            companies.write({"allowed_document_type_ids": [Command.set(types.ids)]})
        return True

    @api.private
    def _collection_catalog_types(self):
        return self.env["collection.document.type"].search(
            [("code", "in", list(COLLECTION_TYPE_CODES))]
        )

    @api.private
    def _collection_enable_all_document_types(self):
        """Union all four catalog types onto each company; keep extras."""
        types = self._collection_catalog_types()
        if not types or not self:
            return True
        self.write(
            {
                "allowed_document_type_ids": [
                    Command.link(type_id) for type_id in types.ids
                ]
            }
        )
        return True

    @api.private
    def _collection_copy_sequences(self):
        """Ensure each company has voucher and sheet sequences."""
        Sequence = self.env["ir.sequence"]
        main = self.env.ref("base.main_company")
        for company in self:
            for code, name, prefix, padding in COLLECTION_SEQUENCE_SPECS:
                existing = Sequence.search(
                    [("code", "=", code), ("company_id", "=", company.id)],
                    limit=1,
                )
                if existing:
                    continue
                template = Sequence.search(
                    [("code", "=", code), ("company_id", "=", main.id)],
                    limit=1,
                )
                if not template:
                    template = Sequence.search([("code", "=", code)], limit=1)
                Sequence.create(
                    {
                        "name": template.name if template else name,
                        "code": code,
                        "prefix": template.prefix if template else prefix,
                        "padding": template.padding if template else padding,
                        "implementation": (
                            template.implementation if template else "standard"
                        ),
                        "number_increment": (
                            template.number_increment if template else 1
                        ),
                        "number_next": 1,
                        "company_id": company.id,
                        "use_date_range": bool(
                            template.use_date_range if template else False
                        ),
                    }
                )
        return True

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        companies._collection_copy_sequences()
        companies._collection_enable_all_document_types()
        return companies

    def write(self, vals):
        result = super().write(vals)
        if "document_review_enabled" in vals:
            self.env.registry.clear_cache()
        return result
