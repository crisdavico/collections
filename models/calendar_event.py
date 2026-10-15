# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

from .collection_common import default_record_company


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    company_id = fields.Many2one("res.company", index=True)

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        if "company_id" in fields_list and "company_id" not in values:
            # Create-time defaults leave existing unassigned events unassigned
            # on upgrade, rather than guessing their company at column init.
            values["company_id"] = default_record_company(self.env).id
        return values


class CalendarAttendee(models.Model):
    _inherit = "calendar.attendee"

    company_id = fields.Many2one(related="event_id.company_id", store=True, index=True)
