from datetime import time

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class CricketSlotRule(models.Model):
    _name = "cricket.slot.rule"
    _description = "Cricket Slot Rule"
    _order = "location_id, dayofweek, sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    location_id = fields.Many2one("cricket.location", required=True, ondelete="cascade")
    booking_type_id = fields.Many2one("cricket.booking.type", ondelete="cascade")
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
        required=True,
    )
    open_time_float = fields.Float(default=9.0, required=True)
    close_time_float = fields.Float(default=21.0, required=True)
    slot_step_minutes = fields.Integer(default=60, required=True)
    play_minutes = fields.Integer(default=55, required=True)
    cleaning_minutes = fields.Integer(default=5, required=True)
    active = fields.Boolean(default=True)
    date_from = fields.Date()
    date_to = fields.Date()

    @api.constrains(
        "open_time_float",
        "close_time_float",
        "slot_step_minutes",
        "play_minutes",
        "cleaning_minutes",
        "date_from",
        "date_to",
    )
    def _check_slot_rule_values(self):
        for rule in self:
            if not 0 <= rule.open_time_float <= 24:
                raise ValidationError(_("Open time must be between 0 and 24."))
            if not 0 <= rule.close_time_float <= 24:
                raise ValidationError(_("Close time must be between 0 and 24."))
            if rule.open_time_float >= rule.close_time_float:
                raise ValidationError(_("Close time must be after open time."))
            if rule.slot_step_minutes < 1:
                raise ValidationError(_("Slot step must be positive."))
            if rule.play_minutes < 1:
                raise ValidationError(_("Play minutes must be positive."))
            if rule.cleaning_minutes < 0:
                raise ValidationError(_("Cleaning minutes cannot be negative."))
            if rule.play_minutes + rule.cleaning_minutes > rule.slot_step_minutes:
                raise ValidationError(_("Play plus cleaning time cannot exceed slot step."))
            if rule.date_from and rule.date_to and rule.date_to < rule.date_from:
                raise ValidationError(_("End date must be after start date."))

    def _matches_date(self, target_date, booking_type):
        self.ensure_one()
        if self.booking_type_id and self.booking_type_id != booking_type:
            return False
        if self.dayofweek != str(target_date.weekday()):
            return False
        if self.date_from and target_date < self.date_from:
            return False
        if self.date_to and target_date > self.date_to:
            return False
        return True

    @api.model
    def _find_rule(self, location, booking_type, target_date):
        return self.search([
            ("active", "=", True),
            ("location_id", "=", location.id),
            ("dayofweek", "=", str(target_date.weekday())),
            "|",
            ("booking_type_id", "=", booking_type.id),
            ("booking_type_id", "=", False),
        ], order="booking_type_id desc, sequence, id").filtered(
            lambda rule: rule._matches_date(target_date, booking_type)
        )[:1]

    @api.model
    def _float_to_time(self, value):
        total_minutes = int(round((value % 24) * 60))
        return time(total_minutes // 60, total_minutes % 60)
