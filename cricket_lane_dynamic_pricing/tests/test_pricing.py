from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestCricketPricing(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.location = cls.env.ref("cricket_lane_booking.cricket_location_main")
        cls.location.write({"minimum_notice_minutes": 0, "max_booking_days_ahead": 365})
        cls.lane = cls.env.ref("cricket_lane_booking.lane_3")
        cls.addon = cls.env.ref("cricket_lane_booking.addon_bola_machine")

    def test_people_and_addon_pricing(self):
        start = fields.Datetime.now() + timedelta(days=5)
        result = self.env["cricket.booking.hold"].quote_from_payload({
            "location_id": self.location.id,
            "booking_type": "lane",
            "lane_ids": [self.lane.id],
            "slot_start": fields.Datetime.to_string(start.replace(hour=13, minute=0, second=0, microsecond=0)),
            "people_count": 4,
            "addon_ids": [self.addon.id],
        })
        self.assertEqual(result["breakdown"]["people_fee"], 6.0)
        self.assertEqual(result["breakdown"]["addon_total"], 5.0)
