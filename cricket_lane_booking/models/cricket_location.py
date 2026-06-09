from odoo import _, api, fields, models
from odoo.addons.base.models.res_partner import _tz_get
from odoo.exceptions import ValidationError


class CricketLocation(models.Model):
    _name = "cricket.location"
    _description = "Cricket Facility Location"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char(required=True, tracking=True)
    partner_id = fields.Many2one("res.partner", string="Address")
    timezone = fields.Selection(
        _tz_get,
        default=lambda self: self.env.user.tz or "UTC",
        required=True,
    )
    active = fields.Boolean(default=True)
    website_published = fields.Boolean(default=True)
    default_open_time = fields.Float(default=9.0, required=True)
    default_close_time = fields.Float(default=21.0, required=True)
    minimum_notice_minutes = fields.Integer(default=60, required=True)
    max_booking_days_ahead = fields.Integer(default=30, required=True)
    hold_minutes = fields.Integer(default=10, required=True)
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    lane_ids = fields.One2many("cricket.lane", "location_id", string="Lanes")
    slot_rule_ids = fields.One2many(
        "cricket.slot.rule",
        "location_id",
        string="Slot Rules",
    )

    @api.constrains(
        "default_open_time",
        "default_close_time",
        "minimum_notice_minutes",
        "max_booking_days_ahead",
        "hold_minutes",
    )
    def _check_location_values(self):
        for location in self:
            if not 0 <= location.default_open_time <= 24:
                raise ValidationError(_("Default open time must be between 0 and 24."))
            if not 0 <= location.default_close_time <= 24:
                raise ValidationError(_("Default close time must be between 0 and 24."))
            if location.default_open_time >= location.default_close_time:
                raise ValidationError(_("Default close time must be after open time."))
            if location.minimum_notice_minutes < 0:
                raise ValidationError(_("Minimum notice cannot be negative."))
            if location.max_booking_days_ahead < 1:
                raise ValidationError(_("Maximum booking days ahead must be at least 1."))
            if location.hold_minutes < 1:
                raise ValidationError(_("Hold minutes must be at least 1."))
