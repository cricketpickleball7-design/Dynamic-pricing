from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class CricketPriceRule(models.Model):
    _name = "cricket.price.rule"
    _description = "Cricket Dynamic Price Rule"
    _order = "sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    location_id = fields.Many2one("cricket.location", ondelete="cascade")
    booking_type_id = fields.Many2one("cricket.booking.type", ondelete="cascade")
    lane_id = fields.Many2one("cricket.lane", ondelete="cascade")
    lane_length_ft = fields.Integer()
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
    date_from = fields.Date()
    date_to = fields.Date()
    time_from_float = fields.Float()
    time_to_float = fields.Float()
    min_people = fields.Integer()
    max_people = fields.Integer()
    occupancy_min = fields.Float()
    occupancy_max = fields.Float()
    traffic_min = fields.Integer()
    traffic_max = fields.Integer()
    rule_type = fields.Selection(
        [
            ("base_override", "Base Override"),
            ("fixed_add", "Fixed Add"),
            ("percent_add", "Percent Add"),
            ("multiplier", "Multiplier"),
            ("min_price", "Minimum Price"),
            ("max_price", "Maximum Price"),
        ],
        default="multiplier",
        required=True,
    )
    value = fields.Float(required=True, default=1.0)
    apply_on = fields.Selection(
        [
            ("base", "Base"),
            ("time_day", "Time / Day"),
            ("occupancy", "Occupancy"),
            ("traffic", "Traffic"),
            ("competitor", "Competitor"),
            ("people", "People"),
        ],
        default="time_day",
        required=True,
    )
    stop_further_rules = fields.Boolean()

    @api.constrains("date_from", "date_to", "time_from_float", "time_to_float")
    def _check_rule_values(self):
        for rule in self:
            if rule.date_from and rule.date_to and rule.date_to < rule.date_from:
                raise ValidationError(_("End date must be after start date."))
            for value in (rule.time_from_float, rule.time_to_float):
                if value and not 0 <= value <= 24:
                    raise ValidationError(_("Rule times must be between 0 and 24."))

    def _matches(self, *, location, booking_type, lanes, slot_local, people_count, occupancy, traffic):
        self.ensure_one()
        if self.location_id and self.location_id != location:
            return False
        if self.booking_type_id and self.booking_type_id != booking_type:
            return False
        if self.lane_id and self.lane_id not in lanes:
            return False
        if self.lane_length_ft and self.lane_length_ft not in lanes.mapped("length_ft"):
            return False
        if self.dayofweek and self.dayofweek != str(slot_local.weekday()):
            return False
        slot_date = slot_local.date()
        if self.date_from and slot_date < self.date_from:
            return False
        if self.date_to and slot_date > self.date_to:
            return False
        slot_hour = slot_local.hour + slot_local.minute / 60.0
        if self.time_from_float or self.time_to_float:
            start = self.time_from_float
            end = self.time_to_float
            if start < end and not start <= slot_hour < end:
                return False
            if start > end and not (slot_hour >= start or slot_hour < end):
                return False
        if self.min_people and people_count < self.min_people:
            return False
        if self.max_people and people_count > self.max_people:
            return False
        if self.occupancy_min and occupancy < self.occupancy_min:
            return False
        if self.occupancy_max and occupancy > self.occupancy_max:
            return False
        if self.traffic_min and traffic < self.traffic_min:
            return False
        if self.traffic_max and traffic > self.traffic_max:
            return False
        return True

    def _apply_to_amount(self, amount):
        self.ensure_one()
        if self.rule_type == "base_override":
            return self.value
        if self.rule_type == "fixed_add":
            return amount + self.value
        if self.rule_type == "percent_add":
            return amount * (1.0 + self.value / 100.0)
        if self.rule_type == "multiplier":
            return amount * self.value
        if self.rule_type == "min_price":
            return max(amount, self.value)
        if self.rule_type == "max_price":
            return min(amount, self.value)
        return amount
