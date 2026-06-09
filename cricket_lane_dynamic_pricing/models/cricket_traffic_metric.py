import hashlib

import pytz
from dateutil import parser
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class CricketTrafficMetric(models.Model):
    _name = "cricket.traffic.metric"
    _description = "Cricket Website Traffic Metric"
    _order = "created_at desc, id desc"

    website_session_id = fields.Char()
    session_token = fields.Char(index=True)
    page_url = fields.Char()
    location_id = fields.Many2one("cricket.location", ondelete="cascade")
    event_type = fields.Selection(
        [
            ("page_view", "Page View"),
            ("lane_selected", "Lane Selected"),
            ("slot_selected", "Slot Selected"),
            ("quote_requested", "Quote Requested"),
            ("checkout_started", "Checkout Started"),
        ],
        required=True,
    )
    booking_type_id = fields.Many2one("cricket.booking.type", ondelete="cascade")
    lane_id = fields.Many2one("cricket.lane", ondelete="cascade")
    slot_start = fields.Datetime()
    created_at = fields.Datetime(default=fields.Datetime.now, required=True, index=True)
    ip_hash = fields.Char()
    user_agent_hash = fields.Char()

    @api.model
    def _hash_value(self, value):
        if not value:
            return False
        return hashlib.sha256(str(value).encode("utf-8")).hexdigest()

    @api.model
    def track(self, payload, request=None):
        booking_type = self.env["cricket.booking.type"].sudo().search([
            ("code", "=", payload.get("booking_type")),
        ], limit=1)
        ip = request.httprequest.remote_addr if request else payload.get("ip")
        user_agent = request.httprequest.user_agent.string if request else payload.get("user_agent")
        slot_start = self._normalize_datetime(payload.get("slot_start"))
        return self.sudo().create({
            "website_session_id": payload.get("website_session_id"),
            "session_token": payload.get("session_token"),
            "page_url": payload.get("page_url"),
            "location_id": int(payload.get("location_id") or 0) or False,
            "event_type": payload.get("event_type") or "page_view",
            "booking_type_id": booking_type.id,
            "lane_id": int(payload.get("lane_id") or 0) or False,
            "slot_start": slot_start,
            "ip_hash": self._hash_value(ip),
            "user_agent_hash": self._hash_value(user_agent),
        })

    @api.model
    def _normalize_datetime(self, value):
        if not value:
            return False
        parsed = parser.isoparse(str(value))
        if parsed.tzinfo:
            return parsed.astimezone(pytz.UTC).replace(tzinfo=None)
        return fields.Datetime.from_string(value)

    @api.model
    def count_recent(self, location, minutes=15):
        since = fields.Datetime.now() - relativedelta(minutes=minutes)
        return self.sudo().search_count([
            ("location_id", "=", location.id),
            ("created_at", ">=", since),
            ("event_type", "in", ["page_view", "lane_selected", "slot_selected", "quote_requested", "checkout_started"]),
        ])

    @api.model
    def _cron_clean_old_metrics(self):
        retention_days = int(
            self.env["ir.config_parameter"].sudo().get_param(
                "cricket_lane_dynamic_pricing.traffic_retention_days",
                30,
            )
        )
        cutoff = fields.Datetime.now() - relativedelta(days=retention_days)
        self.search([("created_at", "<", cutoff)]).unlink()
