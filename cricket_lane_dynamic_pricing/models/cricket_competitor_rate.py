from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class CricketCompetitorRate(models.Model):
    _name = "cricket.competitor.rate"
    _description = "Cricket Competitor Rate"
    _order = "captured_at desc, id desc"

    competitor_name = fields.Char(required=True)
    location_id = fields.Many2one("cricket.location", ondelete="cascade")
    booking_type_id = fields.Many2one("cricket.booking.type", ondelete="cascade")
    lane_length_ft = fields.Integer()
    time_band = fields.Char()
    dayofweek = fields.Selection(
        [
            ("0", "Monday"),
            ("1", "Tuesday"),
            ("2", "Wednesday"),
            ("3", "Thursday"),
            ("4", "Friday"),
            ("5", "Saturday"),
            ("6", "Sunday"),
        ],
    )
    price = fields.Monetary(currency_field="currency_id", required=True)
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    source_type = fields.Selection(
        [
            ("manual", "Manual"),
            ("csv", "CSV"),
            ("api", "API"),
            ("scraper", "Scraper"),
        ],
        default="manual",
        required=True,
    )
    source_url = fields.Char()
    captured_at = fields.Datetime(default=fields.Datetime.now, required=True)
    confidence = fields.Selection(
        [
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
        ],
        default="medium",
        required=True,
    )
    active = fields.Boolean(default=True)

    @api.constrains("price")
    def _check_price(self):
        for rate in self:
            if rate.price < 0:
                raise ValidationError(_("Competitor price cannot be negative."))
