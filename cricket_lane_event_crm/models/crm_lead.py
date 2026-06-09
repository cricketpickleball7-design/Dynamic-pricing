from odoo import fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    cricket_event_type = fields.Char()
    cricket_preferred_date = fields.Date()
    cricket_preferred_time = fields.Float()
    cricket_people_count = fields.Integer()
    cricket_addon_ids = fields.Many2many(
        "cricket.addon",
        "crm_lead_cricket_addon_rel",
        "lead_id",
        "addon_id",
        string="Requested Cricket Add-ons",
    )
    cricket_location_id = fields.Many2one("cricket.location", string="Cricket Location")
    cricket_booking_type_id = fields.Many2one("cricket.booking.type", string="Booking Type")
