import json
from datetime import datetime

import pytz

from odoo import _, api, fields, models
from odoo.addons.base.models.res_partner import _tz_get
from odoo.exceptions import ValidationError
from odoo.tools import float_round


class AppointmentDynamicPricingConfig(models.Model):
    _name = "appointment.dynamic.pricing.config"
    _description = "Appointment Dynamic Pricing Configuration"
    _order = "sequence, name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    appointment_type_id = fields.Many2one(
        "appointment.type",
        string="Appointment Type",
        required=True,
        ondelete="cascade",
    )
    product_id = fields.Many2one(
        "product.product",
        required=True,
        ondelete="cascade",
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="product_id.currency_id",
        readonly=True,
    )
    pricing_tz = fields.Selection(
        _tz_get,
        string="Pricing Timezone",
        default=lambda self: self.env.user.tz or "UTC",
        required=True,
    )
    base_price = fields.Monetary(
        currency_field="currency_id",
        required=True,
    )
    minimum_price = fields.Monetary(
        currency_field="currency_id",
        required=True,
    )
    maximum_price = fields.Monetary(
        currency_field="currency_id",
        required=True,
    )
    maximum_adjustment_percent = fields.Float(
        default=30.0,
        required=True,
        help="Maximum positive or negative adjustment percentage.",
    )
    time_weight = fields.Float(default=0.25, required=True)
    traffic_weight = fields.Float(default=0.25, required=True)
    session_weight = fields.Float(default=0.20, required=True)
    behavior_weight = fields.Float(default=0.10, required=True)
    competitor_weight = fields.Float(default=0.20, required=True)
    rule_ids = fields.One2many(
        "appointment.dynamic.pricing.rule",
        "config_id",
        string="Time Rules",
    )
    signal_ids = fields.One2many(
        "appointment.pricing.signal",
        "config_id",
        string="Pricing Signals",
    )
    competitor_rate_ids = fields.One2many(
        "appointment.competitor.rate",
        "config_id",
        string="Competitor Rates",
    )
    log_ids = fields.One2many(
        "appointment.dynamic.price.log",
        "config_id",
        string="Price Logs",
    )

    @api.constrains(
        "base_price",
        "minimum_price",
        "maximum_price",
        "maximum_adjustment_percent",
        "time_weight",
        "traffic_weight",
        "session_weight",
        "behavior_weight",
        "competitor_weight",
    )
    def _check_pricing_config_values(self):
        for config in self:
            if config.base_price <= 0:
                raise ValidationError(_("Base price must be greater than zero."))
            if config.minimum_price <= 0:
                raise ValidationError(_("Minimum price must be greater than zero."))
            if config.maximum_price < config.minimum_price:
                raise ValidationError(_("Maximum price must be greater than minimum price."))
            if config.maximum_adjustment_percent < 0:
                raise ValidationError(_("Maximum adjustment percentage cannot be negative."))
            weights = [
                config.time_weight,
                config.traffic_weight,
                config.session_weight,
                config.behavior_weight,
                config.competitor_weight,
            ]
            if any(weight < 0 for weight in weights):
                raise ValidationError(_("Pricing weights cannot be negative."))

    @api.model
    def get_dynamic_price(self, payload):
        appointment_type_id = int(payload.get("appointment_type_id") or 0)
        product_id = int(payload.get("product_id") or 0)
        slot_datetime = payload.get("slot_datetime")
        if not appointment_type_id or not product_id or not slot_datetime:
            return {
                "success": False,
                "error": "appointment_type_id, product_id, and slot_datetime are required.",
            }

        config = self.search([
            ("active", "=", True),
            ("appointment_type_id", "=", appointment_type_id),
            ("product_id", "=", product_id),
            ("company_id", "=", self.env.company.id),
        ], limit=1)
        if not config:
            return {
                "success": False,
                "error": "No active dynamic pricing configuration found.",
            }

        result = config._calculate_price(slot_datetime, payload=payload)
        log = config._create_price_log(result, payload)
        result.update({
            "log_id": log.id,
            "currency": config.currency_id.name,
        })

        if payload.get("confirm"):
            config._apply_confirmed_price(log, payload)

        return result

    def _calculate_price(self, slot_datetime, payload=None):
        self.ensure_one()
        payload = payload or {}
        slot_utc = self._parse_slot_datetime(slot_datetime)
        slot_local = self._to_pricing_timezone(slot_utc)

        time_score, applied_rule = self._get_time_score(slot_local)
        signal = self._get_latest_signal()
        competitor_rate = self._get_latest_competitor_rate()

        traffic_score = signal.traffic_score if signal else 50.0
        session_score = signal.session_score if signal else 50.0
        behavior_score = signal.behavior_score if signal else 50.0
        competitor_score = competitor_rate.competitor_score if competitor_rate else 50.0

        final_score = (
            self.time_weight * time_score
            + self.traffic_weight * traffic_score
            + self.session_weight * session_score
            + self.behavior_weight * behavior_score
            + self.competitor_weight * competitor_score
        )
        adjustment_percent = (
            (final_score - 50.0) / 50.0
        ) * self.maximum_adjustment_percent
        raw_price = self.base_price * (1 + (adjustment_percent / 100.0))
        final_price = min(max(raw_price, self.minimum_price), self.maximum_price)
        final_price = float_round(
            final_price,
            precision_rounding=self.currency_id.rounding,
        )

        reason_parts = []
        if applied_rule:
            reason_parts.append(applied_rule.name)
        if signal and traffic_score > 65:
            reason_parts.append(_("High Traffic"))
        elif signal and traffic_score < 35:
            reason_parts.append(_("Low Traffic"))
        if signal and session_score > 65:
            reason_parts.append(_("High Active Sessions"))
        if signal and behavior_score > 65:
            reason_parts.append(_("Strong User Intent"))
        if competitor_rate and competitor_score > 65:
            reason_parts.append(_("Competitor Higher"))
        elif competitor_rate and competitor_score < 35:
            reason_parts.append(_("Competitor Lower"))
        if not reason_parts:
            reason_parts.append(_("Standard Demand"))

        return {
            "success": True,
            "config_id": self.id,
            "appointment_type_id": self.appointment_type_id.id,
            "product_id": self.product_id.id,
            "slot_datetime": fields.Datetime.to_string(slot_utc),
            "slot_datetime_local": slot_local.strftime("%Y-%m-%d %H:%M:%S"),
            "base_price": self.base_price,
            "minimum_price": self.minimum_price,
            "maximum_price": self.maximum_price,
            "final_price": final_price,
            "raw_price": raw_price,
            "final_score": final_score,
            "adjustment_percent": adjustment_percent,
            "time_score": time_score,
            "traffic_score": traffic_score,
            "session_score": session_score,
            "behavior_score": behavior_score,
            "competitor_score": competitor_score,
            "applied_rule": applied_rule.name if applied_rule else False,
            "applied_rule_id": applied_rule.id if applied_rule else False,
            "signal_id": signal.id if signal else False,
            "competitor_rate_id": competitor_rate.id if competitor_rate else False,
            "reason": " + ".join(reason_parts),
        }

    def _parse_slot_datetime(self, slot_datetime):
        if isinstance(slot_datetime, datetime):
            parsed = slot_datetime
        else:
            parsed = fields.Datetime.from_string(slot_datetime)
        if parsed.tzinfo:
            return parsed.astimezone(pytz.UTC).replace(tzinfo=None)
        return parsed

    def _to_pricing_timezone(self, slot_utc):
        self.ensure_one()
        timezone = pytz.timezone(self.pricing_tz or "UTC")
        return pytz.UTC.localize(slot_utc).astimezone(timezone)

    def _get_time_score(self, slot_local):
        self.ensure_one()
        for rule in self.rule_ids.filtered("active").sorted(lambda rule: rule.sequence):
            if rule._matches_slot(slot_local):
                return rule.score, rule
        return 50.0, self.env["appointment.dynamic.pricing.rule"]

    def _get_latest_signal(self):
        self.ensure_one()
        return self.env["appointment.pricing.signal"].search([
            ("config_id", "=", self.id),
        ], order="observed_at desc, id desc", limit=1)

    def _get_latest_competitor_rate(self):
        self.ensure_one()
        return self.env["appointment.competitor.rate"].search([
            ("config_id", "=", self.id),
        ], order="observed_at desc, id desc", limit=1)

    def _create_price_log(self, result, payload):
        self.ensure_one()
        return self.env["appointment.dynamic.price.log"].create({
            "config_id": self.id,
            "appointment_type_id": self.appointment_type_id.id,
            "product_id": self.product_id.id,
            "slot_datetime": result["slot_datetime"],
            "base_price": result["base_price"],
            "minimum_price": result["minimum_price"],
            "maximum_price": result["maximum_price"],
            "raw_price": result["raw_price"],
            "final_price": result["final_price"],
            "final_score": result["final_score"],
            "adjustment_percent": result["adjustment_percent"],
            "time_score": result["time_score"],
            "traffic_score": result["traffic_score"],
            "session_score": result["session_score"],
            "behavior_score": result["behavior_score"],
            "competitor_score": result["competitor_score"],
            "applied_rule_id": result["applied_rule_id"] or False,
            "signal_id": result["signal_id"] or False,
            "competitor_rate_id": result["competitor_rate_id"] or False,
            "currency_id": self.currency_id.id,
            "reason": result["reason"],
            "request_payload": json.dumps(payload, default=str),
            "response_payload": json.dumps(result, default=str),
        })

    def _apply_confirmed_price(self, log, payload):
        sale_line_id = int(payload.get("sale_order_line_id") or 0)
        calendar_event_id = int(payload.get("calendar_event_id") or 0)
        if sale_line_id:
            sale_line = self.env["sale.order.line"].browse(sale_line_id).exists()
            if sale_line:
                sale_line._apply_appointment_dynamic_price_log(log)
        if calendar_event_id:
            event = self.env["calendar.event"].browse(calendar_event_id).exists()
            if event:
                event._apply_appointment_dynamic_price_log(log)

