import json

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request


class CricketEventRequestController(http.Controller):
    def _payload(self):
        try:
            return json.loads(request.httprequest.get_data(as_text=True) or "{}")
        except json.JSONDecodeError:
            raise UserError("Invalid JSON payload.")

    @http.route("/cricket/api/event-request", type="http", auth="public", methods=["POST"], csrf=False, website=True)
    def event_request(self, **kwargs):
        try:
            payload = self._payload()
            first_name = payload.get("first_name")
            last_name = payload.get("last_name")
            email = payload.get("email")
            phone = payload.get("phone")
            if not first_name or not last_name or not email:
                raise UserError("First name, last name, and email are required.")
            booking_type = request.env["cricket.booking.type"].sudo().search([
                ("code", "=", "event"),
            ], limit=1)
            addon_ids = [int(addon_id) for addon_id in payload.get("addon_ids", [])]
            lead = request.env["crm.lead"].sudo().create({
                "name": "Box Cricket Event - %s %s" % (first_name, last_name),
                "contact_name": "%s %s" % (first_name, last_name),
                "email_from": email,
                "phone": phone,
                "description": payload.get("notes"),
                "type": "opportunity",
                "cricket_event_type": payload.get("event_type"),
                "cricket_preferred_date": payload.get("preferred_date"),
                "cricket_preferred_time": self._time_to_float(payload.get("preferred_time")),
                "cricket_people_count": int(payload.get("people_count") or 0),
                "cricket_addon_ids": [(6, 0, addon_ids)],
                "cricket_location_id": int(payload.get("location_id") or 0) or False,
                "cricket_booking_type_id": booking_type.id,
            })
            template = request.env.ref(
                "cricket_lane_event_crm.event_request_received_template",
                raise_if_not_found=False,
            )
            if template:
                template.sudo().send_mail(lead.id, force_send=False)
            return request.make_json_response({
                "lead_id": lead.id,
                "message": "Your event request has been submitted.",
            })
        except UserError as error:
            return request.make_json_response({"error": str(error)}, status=400)

    def _time_to_float(self, value):
        if not value:
            return 0.0
        hour, minute = str(value).split(":")[:2]
        return int(hour) + int(minute) / 60.0
