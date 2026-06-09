from odoo.tests.common import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestCricketWebsiteBookingFlow(HttpCase):
    def test_booking_page_loads(self):
        response = self.url_open("/book-cricket-lane")
        self.assertEqual(response.status_code, 200)
