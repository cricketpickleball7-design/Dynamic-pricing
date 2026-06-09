from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestCricketOccupancyPricing(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.location = cls.env.ref("cricket_lane_booking.cricket_location_main")
        cls.location.write({"minimum_notice_minutes": 0, "max_booking_days_ahead": 365})
        cls.lane_1 = cls.env.ref("cricket_lane_booking.lane_1")
        cls.lane_2 = cls.env.ref("cricket_lane_booking.lane_2")

    def test_occupancy_multiplier_increases_after_existing_hold(self):
        start = fields.Datetime.now() + timedelta(days=6)
        slot_start = fields.Datetime.to_string(start.replace(hour=16, minute=0, second=0, microsecond=0))
        self.env["cricket.booking.hold"].create_hold_from_payload({
            "location_id": self.location.id,
            "booking_type": "lane",
            "lane_ids": [self.lane_1.id],
            "slot_start": slot_start,
            "people_count": 2,
            "addon_ids": [],
            "customer": {"email": "hold@example.com"},
        })
        quote = self.env["cricket.booking.hold"].quote_from_payload({
            "location_id": self.location.id,
            "booking_type": "lane",
            "lane_ids": [self.lane_2.id],
            "slot_start": slot_start,
            "people_count": 2,
            "addon_ids": [],
        })
        self.assertGreaterEqual(quote["breakdown"]["occupancy_factor"], 1.10)
