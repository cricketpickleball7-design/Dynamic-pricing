from datetime import datetime, timedelta

import pytz

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestCricketAvailability(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.location = cls.env.ref("cricket_lane_booking.cricket_location_main")
        cls.location.write({"minimum_notice_minutes": 0, "max_booking_days_ahead": 365})
        cls.lane = cls.env.ref("cricket_lane_booking.lane_1")
        cls.hold_model = cls.env["cricket.booking.hold"]

    def _slot_start(self):
        timezone = pytz.timezone(self.location.timezone)
        local_start = timezone.localize(
            datetime.now().replace(hour=13, minute=0, second=0, microsecond=0)
            + timedelta(days=2),
            is_dst=False,
        )
        return local_start.isoformat()

    def _payload(self):
        return {
            "location_id": self.location.id,
            "booking_type": "lane",
            "lane_ids": [self.lane.id],
            "slot_start": self._slot_start(),
            "people_count": 2,
            "addon_ids": [],
            "customer": {
                "first_name": "Asha",
                "last_name": "Patel",
                "phone": "1234567890",
                "email": "asha@example.com",
            },
        }

    def test_55_minute_play_and_60_minute_block(self):
        hold = self.hold_model.create_hold_from_payload(self._payload())
        self.assertEqual((hold.play_end - hold.slot_start).total_seconds(), 55 * 60)
        self.assertEqual((hold.slot_end - hold.slot_start).total_seconds(), 60 * 60)

    def test_active_hold_prevents_overlap(self):
        self.hold_model.create_hold_from_payload(self._payload())
        with self.assertRaises(UserError):
            self.hold_model.create_hold_from_payload(self._payload())

    def test_admin_slot_block_prevents_hold(self):
        slot_start = self.hold_model._parse_datetime_in_location_tz(
            self._payload()["slot_start"],
            self.location,
        )
        _play_end, slot_end = self.hold_model._get_slot_bounds_for_location(
            self.location,
            self.env.ref("cricket_lane_booking.booking_type_lane"),
            slot_start,
        )
        self.env["cricket.slot.block"].create({
            "name": "Maintenance",
            "location_id": self.location.id,
            "lane_ids": [(6, 0, [self.lane.id])],
            "slot_start": slot_start,
            "slot_end": slot_end,
            "reason": "maintenance",
        })
        with self.assertRaises(UserError):
            self.hold_model.create_hold_from_payload(self._payload())
