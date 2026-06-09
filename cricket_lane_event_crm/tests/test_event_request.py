from odoo.tests.common import TransactionCase


class TestCricketEventRequest(TransactionCase):
    def test_event_request_lead_fields(self):
        location = self.env.ref("cricket_lane_booking.cricket_location_main")
        lead = self.env["crm.lead"].create({
            "name": "Box Cricket Event - Test",
            "contact_name": "Test Customer",
            "email_from": "event@example.com",
            "type": "opportunity",
            "cricket_event_type": "Birthday",
            "cricket_preferred_date": "2026-06-08",
            "cricket_preferred_time": 18.0,
            "cricket_people_count": 25,
            "cricket_location_id": location.id,
            "cricket_booking_type_id": self.env.ref("cricket_lane_booking.booking_type_event").id,
        })
        self.assertEqual(lead.cricket_people_count, 25)
        self.assertEqual(lead.cricket_location_id, location)
