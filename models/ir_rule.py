# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from contextvars import ContextVar

from odoo import api, models
from odoo.fields import Domain

from .collection_common import is_company_restricted

# Apply the extra company boundary to the requested model's company_id. Delegated
# parent models may carry a different company (e.g. res.users' shared contact).
# This state is server-owned, never a caller-supplied RPC context flag.
_COMPUTING_NATIVE_RULES = ContextVar("collection_computing_native_rules", default=False)


class IrRule(models.Model):
    _inherit = "ir.rule"

    @api.model
    def _compute_domain(self, model_name, mode="read"):
        if _COMPUTING_NATIVE_RULES.get():
            return super()._compute_domain(model_name, mode=mode)
        token = _COMPUTING_NATIVE_RULES.set(True)
        try:
            domain = super()._compute_domain(model_name, mode=mode)
        finally:
            _COMPUTING_NATIVE_RULES.reset(token)
        field = self.env[model_name]._fields.get("company_id")
        if (
            field
            and field.type == "many2one"
            and field.comodel_name == "res.company"
            # Some wizards expose a computed company summary with no searchable
            # ownership column (e.g. mail.activity.schedule). Their underlying
            # business records still receive the company boundary.
            and (field.store or field.search)
            and is_company_restricted(self.env)
        ):
            # Intersect after native global/group rules so extra roles cannot
            # widen access. The user's profile company is independent of context.
            domain &= Domain("company_id", "=", self.env.user.company_id.id)
        return domain
