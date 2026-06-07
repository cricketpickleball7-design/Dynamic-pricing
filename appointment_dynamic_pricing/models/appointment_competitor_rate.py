from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AppointmentCompetitorRate(models.Model):
    _name = "appointment.competitor.rate"
    _description = "Appointment Competitor Rate"
    _order = "observed_at desc, id desc"

    name = fields.Char(required=True)
    config_id = fields.Many2one(
        "appointment.dynamic.pricing.config",
        required=True,
        ondelete="cascade",
    )
    appointment_type_id = fields.Many2one(
        related="config_id.appointment_type_id",
        store=True,
        readonly=True,
    )
    product_id = fields.Many2one(
        related="config_id.product_id",
        store=True,
        readonly=True,
    )
    observed_at = fields.Datetime(default=fields.Datetime.now, required=True)
    competitor_name = fields.Char(required=True)
    competitor_price = fields.Monetary(currency_field="currency_id", required=True)
    currency_id = fields.Many2one(
        "res.currency",
        related="config_id.currency_id",
        readonly=True,
    )
    competitor_score = fields.Float(
        default=50.0,
        required=True,
        help="0 means competitor is much lower; 100 means competitor is much higher.",
    )
    source_url = fields.Char()
    note = fields.Text()

    @api.constrains("competitor_score", "competitor_price")
    def _check_competitor_values(self):
        for rate in self:
            if rate.competitor_price < 0:
                raise ValidationError(_("Competitor price cannot be negative."))
            if not 0 <= rate.competitor_score <= 100:
                raise ValidationError(_("Competitor score must be between 0 and 100."))

