import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class AppointmentDynamicPricingController(http.Controller):
    @http.route(
        "/appointment_dynamic_pricing/get_price",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        website=True,
    )
    def get_price(self, **kwargs):
        try:
            payload = json.loads(request.httprequest.get_data(as_text=True) or "{}")
        except json.JSONDecodeError:
            return request.make_json_response({
                "success": False,
                "error": "Invalid JSON payload.",
            }, status=400)

        try:
            response = request.env[
                "appointment.dynamic.pricing.config"
            ].sudo().get_dynamic_price(payload)
            status = 200 if response.get("success") else 400
            return request.make_json_response(response, status=status)
        except Exception as error:
            _logger.exception("Appointment dynamic pricing failed")
            return request.make_json_response({
                "success": False,
                "error": str(error),
            }, status=500)

