import json
import uuid

from odoo import http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request


class CricketLaneWebsiteBookingController(http.Controller):
    def _session_token(self):
        token = request.session.get("cricket_booking_session_token")
        if not token:
            token = uuid.uuid4().hex
            request.session["cricket_booking_session_token"] = token
        return token

    def _payload(self):
        try:
            return json.loads(request.httprequest.get_data(as_text=True) or "{}")
        except json.JSONDecodeError:
            raise UserError("Invalid JSON payload.")

    def _json(self, values, status=200):
        return request.make_json_response(values, status=status)

    @http.route("/book-cricket-lane", type="http", auth="public", website=True)
    def booking_page(self, **kwargs):
        return request.render("cricket_lane_website_booking.cricket_lane_booking_page")

    @http.route("/cricket/api/config", type="http", auth="public", methods=["GET"], csrf=False, website=True)
    def config(self, **kwargs):
        locations = request.env["cricket.location"].sudo().search([
            ("active", "=", True),
            ("website_published", "=", True),
        ])
        booking_types = request.env["cricket.booking.type"].sudo().search([
            ("active", "=", True),
            ("website_published", "=", True),
        ], order="sequence, id")
        addons = request.env["cricket.addon"].sudo().search([
            ("active", "=", True),
            ("website_published", "=", True),
        ], order="sequence, id")
        return self._json({
            "session_token": self._session_token(),
            "locations": [{
                "id": location.id,
                "name": location.name,
                "timezone": location.timezone,
                "minimum_notice_minutes": location.minimum_notice_minutes,
                "max_booking_days_ahead": location.max_booking_days_ahead,
                "currency": location.currency_id.name,
            } for location in locations],
            "booking_types": [{
                "id": booking_type.id,
                "name": booking_type.name,
                "code": booking_type.code,
                "description": booking_type.description,
                "allow_instant_payment": booking_type.allow_instant_payment,
                "create_crm_lead": booking_type.create_crm_lead,
                "play_minutes": booking_type.play_minutes,
                "cleaning_minutes": booking_type.cleaning_minutes,
            } for booking_type in booking_types],
            "addons": [{
                "id": addon.id,
                "name": addon.name,
                "price": addon.price,
                "state": addon.state,
                "description": addon.description,
                "booking_type_ids": addon.booking_type_ids.ids,
                "lane_ids": addon.lane_ids.ids,
            } for addon in addons],
        })

    @http.route("/cricket/api/lanes", type="http", auth="public", methods=["GET"], csrf=False, website=True)
    def lanes(self, **kwargs):
        location_id = int(kwargs.get("location_id") or 0)
        booking_type = kwargs.get("booking_type") or "lane"
        lanes = request.env["cricket.lane"].sudo().search([
            ("location_id", "=", location_id),
            ("active", "=", True),
            ("website_published", "=", True),
        ], order="sequence, id")
        individual_lanes = lanes.filtered(lambda lane: lane.lane_type == "individual")
        box_lane = lanes.filtered(lambda lane: lane.lane_type == "box_bundle")[:1]
        if booking_type == "box_cricket" and box_lane:
            lane_payload = [lane._get_public_dict() for lane in lanes]
        else:
            lane_payload = [lane._get_public_dict() for lane in individual_lanes]
        return self._json({
            "lanes": lane_payload,
            "box_cricket": box_lane._get_public_dict() if box_lane else False,
        })

    @http.route("/cricket/api/slots", type="http", auth="public", methods=["GET"], csrf=False, website=True)
    def slots(self, **kwargs):
        lane_id = int(kwargs.get("lane_id") or 0)
        booking_type = kwargs.get("booking_type") or "lane"
        location_id = int(kwargs.get("location_id") or 0)
        target_date = kwargs.get("date")
        people_count = int(kwargs.get("people_count") or 1)
        lane_ids = [lane_id] if lane_id else []
        if booking_type == "box_cricket" and not lane_ids:
            box_lane = request.env["cricket.lane"].sudo().search([
                ("location_id", "=", location_id),
                ("lane_type", "=", "box_bundle"),
                ("active", "=", True),
            ], limit=1)
            lane_ids = box_lane.ids
        result = request.env["cricket.booking"].sudo().generate_slots(
            location_id,
            booking_type,
            lane_ids,
            target_date,
            people_count=people_count,
        )
        return self._json(result)

    @http.route("/cricket/api/quote", type="http", auth="public", methods=["POST"], csrf=False, website=True)
    def quote(self, **kwargs):
        try:
            payload = self._payload()
            payload["session_token"] = self._session_token()
            request.env["cricket.traffic.metric"].sudo().track({
                **payload,
                "event_type": "quote_requested",
            }, request=request)
            return self._json(request.env["cricket.booking.hold"].sudo().quote_from_payload(payload))
        except (UserError, ValidationError) as error:
            return self._json({"available": False, "error": str(error)}, status=400)

    @http.route("/cricket/api/hold", type="http", auth="public", methods=["POST"], csrf=False, website=True)
    def hold(self, **kwargs):
        try:
            payload = self._payload()
            hold = request.env["cricket.booking.hold"].sudo().create_hold_from_payload(
                payload,
                session_token=self._session_token(),
            )
            return self._json({
                "hold_id": hold.id,
                "expires_at": hold.expires_at.isoformat(),
                "price_total": hold.price_total,
                "currency": hold.currency_id.name,
            })
        except (UserError, ValidationError) as error:
            return self._json({"error": str(error)}, status=400)

    @http.route("/cricket/api/checkout", type="http", auth="public", methods=["POST"], csrf=False, website=True)
    def checkout(self, **kwargs):
        try:
            payload = self._payload()
            hold = request.env["cricket.booking.hold"].sudo().browse(
                int(payload.get("hold_id") or 0)
            ).exists()
            if not hold:
                raise UserError("Invalid hold.")
            request.env["cricket.traffic.metric"].sudo().track({
                "event_type": "checkout_started",
                "location_id": hold.location_id.id,
                "booking_type": hold.booking_type_id.code,
                "session_token": self._session_token(),
            }, request=request)
            order = hold.action_create_sale_order()
            request.session["sale_order_id"] = order.id
            return self._json({
                "sale_order_id": order.id,
                "redirect_url": "/shop/payment",
            })
        except (UserError, ValidationError) as error:
            return self._json({"error": str(error)}, status=400)

    @http.route("/cricket/api/traffic", type="http", auth="public", methods=["POST"], csrf=False, website=True)
    def traffic(self, **kwargs):
        payload = self._payload()
        payload["session_token"] = self._session_token()
        request.env["cricket.traffic.metric"].sudo().track(payload, request=request)
        return self._json({"ok": True})
