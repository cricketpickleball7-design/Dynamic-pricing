import json

import pytz

from odoo import _, fields, models
from odoo.tools import float_round


class CricketLocation(models.Model):
    _inherit = "cricket.location"

    traffic_window_minutes = fields.Integer(default=15)
    high_traffic_count = fields.Integer(default=20)
    very_high_traffic_count = fields.Integer(default=50)
    high_traffic_multiplier = fields.Float(default=1.05)
    very_high_traffic_multiplier = fields.Float(default=1.10)
    competitor_capture_percent = fields.Float(default=30.0)
    competitor_min_adjustment = fields.Monetary(
        currency_field="currency_id",
        default=-5.0,
    )
    competitor_max_adjustment = fields.Monetary(
        currency_field="currency_id",
        default=5.0,
    )


class CricketBookingHold(models.Model):
    _inherit = "cricket.booking.hold"

    def _calculate_price(
        self,
        location,
        booking_type,
        lanes,
        slot_start,
        people_count,
        addons,
    ):
        timezone = pytz.timezone(location.timezone or "UTC")
        slot_local = pytz.UTC.localize(slot_start).astimezone(timezone)
        priced_lane = lanes.sorted(lambda lane: lane.base_price, reverse=True)[:1]
        base_price = priced_lane.base_price if priced_lane else 0.0

        traffic_count = self.env["cricket.traffic.metric"].count_recent(
            location,
            location.traffic_window_minutes,
        )
        play_end, slot_end = self._get_slot_bounds_for_location(
            location,
            booking_type,
            slot_start,
        )
        occupancy = self.env["cricket.booking"].occupancy_percent(
            location,
            lanes,
            slot_start,
            slot_end,
        )

        time_factor = self._factor_from_rules(
            "time_day",
            1.0,
            location,
            booking_type,
            lanes,
            slot_local,
            people_count,
            occupancy,
            traffic_count,
        )
        occupancy_factor = self._factor_from_rules(
            "occupancy",
            self._default_occupancy_factor(occupancy),
            location,
            booking_type,
            lanes,
            slot_local,
            people_count,
            occupancy,
            traffic_count,
        )
        traffic_factor = self._factor_from_rules(
            "traffic",
            self._default_traffic_factor(location, traffic_count),
            location,
            booking_type,
            lanes,
            slot_local,
            people_count,
            occupancy,
            traffic_count,
        )

        included_people = max(lanes.mapped("included_people") or [0])
        extra_fee = max(lanes.mapped("extra_person_fee") or [0.0])
        people_fee = max(people_count - included_people, 0) * extra_fee
        addon_total = sum(addons.mapped("price"))

        subtotal = base_price * time_factor * occupancy_factor * traffic_factor
        competitor_adjustment, competitor_factor, competitor_price = self._competitor_adjustment(
            location,
            booking_type,
            lanes,
            slot_local,
            subtotal,
        )
        subtotal_with_competitor = subtotal + competitor_adjustment
        subtotal_before_addons = subtotal_with_competitor + people_fee
        final_price = subtotal_before_addons + addon_total
        final_price = self._apply_price_rules(
            final_price,
            "base",
            location,
            booking_type,
            lanes,
            slot_local,
            people_count,
            occupancy,
            traffic_count,
        )
        final_price = float_round(
            final_price,
            precision_rounding=location.currency_id.rounding,
        )
        return {
            "base_price": base_price,
            "lane_factor": 1.0,
            "time_factor": time_factor,
            "occupancy_factor": occupancy_factor,
            "occupancy_percent": occupancy,
            "traffic_factor": traffic_factor,
            "traffic_count": traffic_count,
            "competitor_factor": competitor_factor,
            "competitor_price": competitor_price,
            "competitor_adjustment": competitor_adjustment,
            "people_fee": people_fee,
            "addons": [
                {"id": addon.id, "name": addon.name, "price": addon.price}
                for addon in addons
            ],
            "subtotal_before_addons": subtotal_before_addons,
            "addon_total": addon_total,
            "final_price": final_price,
            "currency": location.currency_id.name,
        }

    def _default_occupancy_factor(self, occupancy):
        if occupancy <= 30:
            return 1.0
        if occupancy <= 70:
            return 1.10
        return 1.25

    def _default_traffic_factor(self, location, traffic_count):
        if traffic_count >= location.very_high_traffic_count:
            return location.very_high_traffic_multiplier
        if traffic_count >= location.high_traffic_count:
            return location.high_traffic_multiplier
        return 1.0

    def _matching_rules(
        self,
        apply_on,
        location,
        booking_type,
        lanes,
        slot_local,
        people_count,
        occupancy,
        traffic,
    ):
        rules = self.env["cricket.price.rule"].sudo().search([
            ("active", "=", True),
            ("apply_on", "=", apply_on),
        ])
        return rules.filtered(lambda rule: rule._matches(
            location=location,
            booking_type=booking_type,
            lanes=lanes,
            slot_local=slot_local,
            people_count=people_count,
            occupancy=occupancy,
            traffic=traffic,
        ))

    def _factor_from_rules(
        self,
        apply_on,
        default,
        location,
        booking_type,
        lanes,
        slot_local,
        people_count,
        occupancy,
        traffic,
    ):
        factor = default
        for rule in self._matching_rules(
            apply_on,
            location,
            booking_type,
            lanes,
            slot_local,
            people_count,
            occupancy,
            traffic,
        ):
            if rule.rule_type == "multiplier":
                factor *= rule.value
            elif rule.rule_type == "percent_add":
                factor *= 1.0 + rule.value / 100.0
            if rule.stop_further_rules:
                break
        return factor

    def _apply_price_rules(
        self,
        amount,
        apply_on,
        location,
        booking_type,
        lanes,
        slot_local,
        people_count,
        occupancy,
        traffic,
    ):
        result = amount
        for rule in self._matching_rules(
            apply_on,
            location,
            booking_type,
            lanes,
            slot_local,
            people_count,
            occupancy,
            traffic,
        ):
            result = rule._apply_to_amount(result)
            if rule.stop_further_rules:
                break
        return result

    def _competitor_adjustment(self, location, booking_type, lanes, slot_local, current_price):
        rates = self.env["cricket.competitor.rate"].sudo().search([
            ("active", "=", True),
            "|",
            ("location_id", "=", location.id),
            ("location_id", "=", False),
            "|",
            ("booking_type_id", "=", booking_type.id),
            ("booking_type_id", "=", False),
            "|",
            ("dayofweek", "=", str(slot_local.weekday())),
            ("dayofweek", "=", False),
        ], limit=20)
        lane_lengths = set(lanes.mapped("length_ft"))
        rates = rates.filtered(
            lambda rate: not rate.lane_length_ft or rate.lane_length_ft in lane_lengths
        )
        if not rates:
            return 0.0, 1.0, False
        competitor_avg = sum(rates.mapped("price")) / len(rates)
        gap = competitor_avg - current_price
        adjustment = gap * (location.competitor_capture_percent / 100.0)
        adjustment = min(max(adjustment, location.competitor_min_adjustment), location.competitor_max_adjustment)
        competitor_factor = (current_price + adjustment) / current_price if current_price else 1.0
        return adjustment, competitor_factor, competitor_avg


class CricketBooking(models.Model):
    _inherit = "cricket.booking"

    def get_price_breakdown(self):
        self.ensure_one()
        if not self.price_breakdown_json:
            return {}
        return json.loads(self.price_breakdown_json)
