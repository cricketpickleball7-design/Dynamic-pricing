from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestCricketHolds(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.location = cls.env.ref("cricket_lane_booking.cricket_location_main")
        cls.location.write({"minimum_notice_minutes": 0, "max_booking_days_ahead": 365})
        cls.lane = cls.env.ref("cricket_lane_booking.lane_2")
        cls.hold_model = cls.env["cricket.booking.hold"]

    def _payload(self):
        start = fields.Datetime.now() + timedelta(days=3)
        start = start.replace(hour=14, minute=0, second=0, microsecond=0)
        return {
            "location_id": self.location.id,
            "booking_type": "lane",
            "lane_ids": [self.lane.id],
            "slot_start": fields.Datetime.to_string(start),
            "people_count": 2,
            "addon_ids": [],
            "customer": {
                "first_name": "Ravi",
                "last_name": "Mehta",
                "phone": "1234567890",
                "email": "ravi@example.com",
            },
        }

    def test_expired_hold_releases_slot(self):
        hold = self.hold_model.create_hold_from_payload(self._payload())
        hold.expires_at = fields.Datetime.now() - timedelta(minutes=1)
        self.hold_model._cron_expire_holds()
        self.assertEqual(hold.state, "expired")
        replacement = self.hold_model.create_hold_from_payload(self._payload())
        self.assertEqual(replacement.state, "active")

    def test_sale_order_confirmation_creates_booking(self):
        hold = self.hold_model.create_hold_from_payload(self._payload())
        order = hold.action_create_sale_order()
        order.action_confirm()
        self.assertEqual(hold.state, "converted")
        self.assertTrue(order.cricket_booking_id)
        self.assertEqual(order.cricket_booking_id.state, "confirmed")

    def test_multi_slot_hold_blocks_continuous_range(self):
        payload = self._payload()
        start = self.hold_model._parse_datetime_in_location_tz(
            payload["slot_start"],
            self.location,
        )
        payload["slot_starts"] = [
            fields.Datetime.to_string(start),
            fields.Datetime.to_string(start + timedelta(hours=1)),
        ]
        hold = self.hold_model.create_hold_from_payload(payload)
        self.assertEqual(hold.slot_count, 2)
        self.assertEqual((hold.slot_end - hold.slot_start).total_seconds(), 120 * 60)
