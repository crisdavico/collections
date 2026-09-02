# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools.translate import _

COLLECTION_SEQUENCE_SPECS = (
    ("collection.voucher", "Payment Voucher", "COL/%(year)s/", 4),
    ("collection.sheet", "Collection Sheet", "CS/%(year)s/", 4),
    ("collection.allocation", "Collection Allocation", "CA/%(year)s/", 4),
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
    collection_connector_id = fields.Many2one(
        comodel_name="collection.connector",
        string="Collection Connector",
        ondelete="set null",
        check_company=True,
        domain="[('company_id', '=', id)]",
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

    @api.private
    def _sync_enabled_sellers_from_connector(self):
        """Replace enabled sellers from the active connector list."""
        self.ensure_one()
        connector = self._collection_active_connector()
        rows = list(connector.list_sellers().get("sellers") or [])
        normalize = self.env["muk_mcp.mixin"]._collection_normalize_ar_mobile
        self._collection_validate_connector_seller_rows(rows, normalize)
        resolved = self._collection_resolve_connector_sellers(
            connector, rows, normalize
        )
        self._collection_upsert_seller_bindings(connector, resolved, rows)
        imported = self.env["res.users"].browse([user.id for _ext, user in resolved])
        missing_company = imported.filtered(
            lambda user: self.id not in user.company_ids.ids
        )
        if missing_company:
            missing_company.write({"company_ids": [Command.link(self.id)]})
        self.write({"enabled_seller_ids": [Command.set(imported.ids)]})
        return True

    @api.private
    def _collection_active_connector(self):
        """Return the company's active connector or raise UserError."""
        connector = self.collection_connector_id
        if not connector:
            connector = self.with_context(active_test=False).collection_connector_id
        if not connector or not connector.active:
            raise UserError(_("No active collection connector is configured."))
        return connector

    @api.private
    def _collection_validate_connector_seller_rows(self, rows, normalize):
        """Reject missing ids, duplicate ids/phones, and invalid rates before write."""
        seen_ext = set()
        seen_phones = {}
        for row in rows:
            ext_id = row.get("external_seller_id") or ""
            if not ext_id:
                raise UserError(_("Connector seller is missing an external id."))
            if ext_id in seen_ext:
                raise UserError(
                    _("Duplicate external seller id in the connector source.")
                )
            seen_ext.add(ext_id)
            try:
                rate = float(row["commission_percent"])
            except (KeyError, TypeError, ValueError) as err:
                raise UserError(_("Seller commission percent is invalid.")) from err
            if rate < 0 or rate > 100:
                raise UserError(_("Seller commission percent is invalid."))
            row["commission_percent"] = rate
            needle = normalize(row.get("mobile"))
            if not needle:
                continue
            if needle in seen_phones:
                raise UserError(_("Duplicate seller phone in the connector source."))
            seen_phones[needle] = ext_id

    @api.private
    def _collection_claim_seller_user(self, assigned, user, ext_id):
        """Record that ext_id maps to user; abort if another row already claimed it."""
        previous = assigned.get(user.id)
        if previous and previous != ext_id:
            raise UserError(_("Two connector sellers map to the same Odoo user."))
        assigned[user.id] = ext_id
        return user

    @api.private
    def _collection_resolve_connector_sellers(self, connector, rows, normalize):
        """Resolve source rows to users: binding, unique phone, then create."""
        existing_bindings = {
            binding.external_seller_id: binding
            for binding in connector.seller_binding_ids
        }
        phone_index = self._collection_internal_users_by_mobile(normalize)
        assigned = {}
        resolved = []
        to_create = []
        empty = self.env["res.users"]
        for row in rows:
            ext_id = row["external_seller_id"]
            binding = existing_bindings.get(ext_id)
            if binding:
                user = self._collection_claim_seller_user(
                    assigned, binding.user_id, ext_id
                )
                resolved.append((ext_id, user))
                continue
            needle = normalize(row.get("mobile"))
            matches = phone_index.get(needle, empty) if needle else empty
            if len(matches) > 1:
                raise UserError(_("Multiple Odoo users share the same seller phone."))
            if len(matches) == 1:
                user = self._collection_claim_seller_user(assigned, matches, ext_id)
                resolved.append((ext_id, user))
                continue
            to_create.append(row)
        created_users = self._collection_create_connector_seller_users(to_create)
        for row, user in zip(to_create, created_users, strict=True):
            ext_id = row["external_seller_id"]
            user = self._collection_claim_seller_user(assigned, user, ext_id)
            resolved.append((ext_id, user))
        return resolved

    @api.private
    def _collection_upsert_seller_bindings(self, connector, resolved, rows):
        """Create missing bindings and write commission_percent on existing ones."""
        rates = {
            row["external_seller_id"]: row.get("commission_percent", 0.0)
            for row in rows
        }
        existing = {
            binding.external_seller_id: binding
            for binding in connector.seller_binding_ids
        }
        new_bindings = []
        for ext_id, user in resolved:
            rate = rates.get(ext_id, 0.0)
            binding = existing.get(ext_id)
            if binding:
                binding.write({"commission_percent": rate})
            else:
                new_bindings.append(
                    {
                        "connector_id": connector.id,
                        "external_seller_id": ext_id,
                        "user_id": user.id,
                        "commission_percent": rate,
                    }
                )
        if new_bindings:
            self.env["collection.connector.seller.binding"].create(new_bindings)

    @api.private
    def _collection_internal_users_by_mobile(self, normalize):
        """Map normalized AR mobile → internal users (no sudo, one search)."""
        internals = self.env["res.users"].search(
            [
                ("share", "=", False),
                ("phone", "!=", False),
                ("phone", "!=", ""),
            ]
        )
        index = {}
        for user in internals:
            needle = normalize(user.phone)
            if not needle:
                continue
            index[needle] = index.get(needle, self.env["res.users"]) | user
        return index

    @api.private
    def _collection_create_connector_seller_users(self, rows):
        """Batch-create internal users for unbound connector sellers."""
        if not rows:
            return self.env["res.users"]
        group_user = self.env.ref("base.group_user")
        logins = []
        partner_vals_list = []
        for row in rows:
            login = self._collection_connector_seller_login(row["external_seller_id"])
            logins.append(login)
            partner_vals_list.append(
                {
                    "name": row.get("name") or login,
                    "email": f"{login}@example.com",
                    "phone": row.get("mobile") or False,
                }
            )
        partners = self._collection_create_partners(partner_vals_list)
        user_vals_list = []
        for partner, login in zip(partners, logins, strict=True):
            user_vals_list.append(
                {
                    "name": partner.name,
                    "login": login,
                    "email": partner.email,
                    "partner_id": partner.id,
                    "company_id": self.id,
                    "company_ids": [Command.link(self.id)],
                    "group_ids": [Command.set([group_user.id])],
                }
            )
        return (
            self.env["res.users"]
            .with_context(
                no_reset_password=True,
                tracking_disable=True,
                mail_create_nolog=True,
                mail_notrack=True,
            )
            .create(user_vals_list)
        )

    @api.private
    def _collection_create_partners(self, vals_list):
        """Create partners; satisfy account.autopost_bills when the column exists."""
        Partner = self.env["res.partner"].with_context(
            tracking_disable=True,
            mail_create_nolog=True,
            mail_notrack=True,
            mail_create_nosubscribe=True,
        )
        if "autopost_bills" in Partner._fields:
            for vals in vals_list:
                vals["autopost_bills"] = "ask"
            return Partner.create(vals_list)
        if not self._collection_partner_has_autopost_bills_column():
            return Partner.create(vals_list)
        ids = []
        for vals in vals_list:
            self.env.cr.execute(
                """
                INSERT INTO res_partner (
                    name, email, phone, vat, company_id, customer_rank,
                    active, complete_name, type, autopost_bills,
                    create_uid, write_uid, create_date, write_date
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, true, %s, 'contact', 'ask',
                    1, 1,
                    (now() AT TIME ZONE 'UTC'),
                    (now() AT TIME ZONE 'UTC')
                )
                RETURNING id
                """,
                (
                    vals.get("name") or "",
                    vals.get("email") or "",
                    vals.get("phone") or None,
                    vals.get("vat") or None,
                    vals.get("company_id") or None,
                    vals.get("customer_rank") or 0,
                    vals.get("name") or "",
                ),
            )
            ids.append(self.env.cr.fetchone()[0])
        Partner.invalidate_model()
        return Partner.browse(ids)

    @api.model
    @api.private
    def _collection_partner_has_autopost_bills_column(self):
        self.env.cr.execute(
            """
            SELECT 1
              FROM information_schema.columns
             WHERE table_name = 'res_partner'
               AND column_name = 'autopost_bills'
            """
        )
        return bool(self.env.cr.fetchone())

    @api.private
    def _collection_connector_seller_login(self, external_seller_id):
        """Return a globally unique login for a connector seller user."""
        safe_ext = re.sub(r"[^A-Za-z0-9._-]+", "-", external_seller_id or "")
        safe_ext = safe_ext.strip("-.") or "seller"
        return f"collection.{self.id}.{safe_ext}"

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
        """Ensure each company has voucher, sheet, and allocation sequences."""
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
