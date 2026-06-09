from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestBoxCricketAvailability(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.location = cls.env.ref("cricket_lane_booking.cricket_location_main")
        cls.location.write({"minimum_notice_minutes": 0, "max_booking_days_ahead": 365})
        cls.lane_4 = cls.env.ref("cricket_lane_booking.lane_4")
        cls.box = cls.env.ref("cricket_lane_booking.lane_box_cricket")
        cls.hold_model = cls.env["cricket.booking.hold"]

    def _start(self):
        start = fields.Datetime.now() + timedelta(days=4)
        return fields.Datetime.to_string(start.replace(hour=15, minute=0, second=0, microsecond=0))

    def test_lane_four_blocks_box_cricket(self):
        start = self._start()
        self.hold_model.create_hold_from_payload({
            "location_id": self.location.id,
            "booking_type": "lane",
            "lane_ids": [self.lane_4.id],
            "slot_start": start,
            "people_count": 2,
            "addon_ids": [],
            "customer": {"email": "lane4@example.com"},
        })
        with self.assertRaises(UserError):
            self.hold_model.create_hold_from_payload({
                "location_id": self.location.id,
                "booking_type": "box_cricket",
                "lane_ids": [self.box.id],
                "slot_start": start,
                "people_count": 6,
                "addon_ids": [],
                "customer": {"email": "box@example.com"},
            })

    def test_box_cricket_blocks_lane_four(self):
        start = self._start()
        self.hold_model.create_hold_from_payload({
            "location_id": self.location.id,
            "booking_type": "box_cricket",
            "lane_ids": [self.box.id],
            "slot_start": start,
            "people_count": 6,
            "addon_ids": [],
            "customer": {"email": "box@example.com"},
        })
        with self.assertRaises(UserError):
            self.hold_model.create_hold_from_payload({
                "location_id": self.location.id,
                "booking_type": "lane",
                "lane_ids": [self.lane_4.id],
                "slot_start": start,
                "people_count": 2,
                "addon_ids": [],
                "customer": {"email": "lane4@example.com"},
            })
