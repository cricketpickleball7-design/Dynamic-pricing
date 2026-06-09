from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestCricketCompetitorPricing(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.location = cls.env.ref("cricket_lane_booking.cricket_location_main")
        cls.location.write({
            "minimum_notice_minutes": 0,
            "max_booking_days_ahead": 365,
            "competitor_capture_percent": 30.0,
            "competitor_min_adjustment": -10.0,
            "competitor_max_adjustment": 10.0,
        })
        cls.lane = cls.env.ref("cricket_lane_booking.lane_4")
        cls.booking_type = cls.env.ref("cricket_lane_booking.booking_type_lane")

    def test_competitor_gap_adjustment(self):
        self.env["cricket.competitor.rate"].create({
            "competitor_name": "Reference Center",
            "location_id": self.location.id,
            "booking_type_id": self.booking_type.id,
            "lane_length_ft": 80,
            "price": 30.0,
        })
        start = fields.Datetime.now() + timedelta(days=8)
        quote = self.env["cricket.booking.hold"].quote_from_payload({
            "location_id": self.location.id,
            "booking_type": "lane",
            "lane_ids": [self.lane.id],
            "slot_start": fields.Datetime.to_string(start.replace(hour=13, minute=0, second=0, microsecond=0)),
            "people_count": 2,
            "addon_ids": [],
        })
        self.assertGreater(quote["breakdown"]["competitor_adjustment"], 0.0)
