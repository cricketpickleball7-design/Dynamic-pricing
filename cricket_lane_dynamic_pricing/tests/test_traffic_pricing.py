from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestCricketTrafficPricing(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.location = cls.env.ref("cricket_lane_booking.cricket_location_main")
        cls.location.write({
            "minimum_notice_minutes": 0,
            "max_booking_days_ahead": 365,
            "high_traffic_count": 2,
            "very_high_traffic_count": 5,
        })
        cls.lane = cls.env.ref("cricket_lane_booking.lane_1")

    def test_high_traffic_multiplier(self):
        metric_model = self.env["cricket.traffic.metric"]
        for index in range(3):
            metric_model.create({
                "event_type": "page_view",
                "location_id": self.location.id,
                "session_token": "traffic-%s" % index,
            })
        start = fields.Datetime.now() + timedelta(days=7)
        quote = self.env["cricket.booking.hold"].quote_from_payload({
            "location_id": self.location.id,
            "booking_type": "lane",
            "lane_ids": [self.lane.id],
            "slot_start": fields.Datetime.to_string(start.replace(hour=13, minute=0, second=0, microsecond=0)),
            "people_count": 2,
            "addon_ids": [],
        })
        self.assertEqual(quote["breakdown"]["traffic_factor"], self.location.high_traffic_multiplier)
