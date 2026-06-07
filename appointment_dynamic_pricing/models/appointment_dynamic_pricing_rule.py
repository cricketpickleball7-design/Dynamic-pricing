from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AppointmentDynamicPricingRule(models.Model):
    _name = "appointment.dynamic.pricing.rule"
    _description = "Appointment Dynamic Pricing Time Rule"
    _order = "sequence, id"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
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
    score = fields.Float(
        default=50.0,
        required=True,
        help="Demand score from 0 to 100 when this rule matches.",
    )
    start_time = fields.Float(
        string="Start Time",
        default=0.0,
        required=True,
        help="24-hour float time. Example: 18.5 means 18:30.",
    )
    end_time = fields.Float(
        string="End Time",
        default=24.0,
        required=True,
        help="24-hour float time. Use the same value as Start Time for all day.",
    )
    date_start = fields.Date()
    date_end = fields.Date()
    monday = fields.Boolean(default=True)
    tuesday = fields.Boolean(default=True)
    wednesday = fields.Boolean(default=True)
    thursday = fields.Boolean(default=True)
    friday = fields.Boolean(default=True)
    saturday = fields.Boolean(default=True)
    sunday = fields.Boolean(default=True)

    @api.constrains("score", "start_time", "end_time", "date_start", "date_end")
    def _check_rule_values(self):
        for rule in self:
            if not 0 <= rule.score <= 100:
                raise ValidationError(_("Rule score must be between 0 and 100."))
            if not 0 <= rule.start_time <= 24:
                raise ValidationError(_("Start time must be between 0 and 24."))
            if not 0 <= rule.end_time <= 24:
                raise ValidationError(_("End time must be between 0 and 24."))
            if rule.date_start and rule.date_end and rule.date_end < rule.date_start:
                raise ValidationError(_("End date must be after start date."))

    def _matches_slot(self, slot_local):
        self.ensure_one()
        slot_date = slot_local.date()
        if self.date_start and slot_date < self.date_start:
            return False
        if self.date_end and slot_date > self.date_end:
            return False

        weekday_field = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ][slot_local.weekday()]
        if not self[weekday_field]:
            return False

        start_minutes = self._float_time_to_minutes(self.start_time)
        end_minutes = self._float_time_to_minutes(self.end_time)
        current_minutes = slot_local.hour * 60 + slot_local.minute
        if start_minutes == end_minutes:
            return True
        if start_minutes < end_minutes:
            return start_minutes <= current_minutes < end_minutes
        return current_minutes >= start_minutes or current_minutes < end_minutes

    @api.model
    def _float_time_to_minutes(self, value):
        return int(round((value % 24) * 60)) % (24 * 60)

