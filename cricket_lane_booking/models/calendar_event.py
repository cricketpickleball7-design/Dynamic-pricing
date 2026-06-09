from odoo import fields, models


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    cricket_booking_id = fields.Many2one(
        "cricket.booking",
        string="Cricket Booking",
        copy=False,
    )
    cricket_hold_id = fields.Many2one(
        "cricket.booking.hold",
        string="Cricket Booking Hold",
        copy=False,
    )
