from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AppointmentPricingSignal(models.Model):
    _name = "appointment.pricing.signal"
    _description = "Appointment Pricing Signal"
    _order = "observed_at desc, id desc"

    name = fields.Char(default="Pricing Signal")
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
    website_id = fields.Many2one("website")
    observed_at = fields.Datetime(default=fields.Datetime.now, required=True)
    traffic_count = fields.Integer()
    active_session_count = fields.Integer()
    behavior_event_count = fields.Integer()
    traffic_score = fields.Float(default=50.0, required=True)
    session_score = fields.Float(default=50.0, required=True)
    behavior_score = fields.Float(default=50.0, required=True)
    note = fields.Text()

    @api.constrains("traffic_score", "session_score", "behavior_score")
    def _check_scores(self):
        for signal in self:
            for score in (
                signal.traffic_score,
                signal.session_score,
                signal.behavior_score,
            ):
                if not 0 <= score <= 100:
                    raise ValidationError(_("Signal scores must be between 0 and 100."))

