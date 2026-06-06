from datetime import datetime, time, timedelta

import pytz

from odoo import _, api, fields, models
from odoo.addons.base.models.res_partner import _tz_get
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    dynamic_pricing_enabled = fields.Boolean(string="Dynamic Pricing")
    dynamic_pricing_day_price = fields.Monetary(
        string="Day Price",
        currency_field="currency_id",
        help="Product sale price during the day period.",
    )
    dynamic_pricing_night_price = fields.Monetary(
        string="Night Price",
        currency_field="currency_id",
        help="Product sale price during the night period.",
    )
    dynamic_pricing_day_start = fields.Float(
        string="Day Starts",
        default=6.0,
        help="Start time in 24-hour format. Example: 6.5 means 06:30.",
    )
    dynamic_pricing_night_start = fields.Float(
        string="Night Starts",
        default=18.0,
        help="Start time in 24-hour format. Example: 18.5 means 18:30.",
    )
    dynamic_pricing_tz = fields.Selection(
        _tz_get,
        string="Pricing Timezone",
        default=lambda self: self.env.user.tz or "UTC",
        help="Timezone used to decide whether the product is in day or night pricing.",
    )

    @api.onchange("dynamic_pricing_enabled", "list_price")
    def _onchange_dynamic_pricing_enabled(self):
        for product in self:
            if not product.dynamic_pricing_enabled:
                continue
            if not product.dynamic_pricing_day_price:
                product.dynamic_pricing_day_price = product.list_price
            if not product.dynamic_pricing_night_price:
                product.dynamic_pricing_night_price = product.list_price

    @api.constrains(
        "dynamic_pricing_enabled",
        "dynamic_pricing_day_price",
        "dynamic_pricing_night_price",
        "dynamic_pricing_day_start",
        "dynamic_pricing_night_start",
    )
    def _check_dynamic_pricing_values(self):
        for product in self:
            if not product.dynamic_pricing_enabled:
                continue
            if (
                product.dynamic_pricing_day_price <= 0
                or product.dynamic_pricing_night_price <= 0
            ):
                raise ValidationError(_("Day and night prices must be greater than zero."))
            if not 0 <= product.dynamic_pricing_day_start < 24:
                raise ValidationError(_("Day start time must be between 0 and 24."))
            if not 0 <= product.dynamic_pricing_night_start < 24:
                raise ValidationError(_("Night start time must be between 0 and 24."))
            if round(product.dynamic_pricing_day_start, 4) == round(
                product.dynamic_pricing_night_start, 4
            ):
                raise ValidationError(_("Day and night start times must be different."))

    def _get_additionnal_combination_info(self, product_or_template, quantity, uom, date, website):
        combination_info = super()._get_additionnal_combination_info(
            product_or_template,
            quantity,
            uom,
            date,
            website,
        )
        template = (
            product_or_template
            if product_or_template._name == "product.template"
            else product_or_template.product_tmpl_id
        )
        if template.dynamic_pricing_enabled:
            combination_info["dynamic_pricing"] = template._get_dynamic_pricing_period_info()
        return combination_info

    def _get_dynamic_pricing_price(self, product=None, currency=None, uom=None, date=False):
        self.ensure_one()
        period_info = self._get_dynamic_pricing_period_info()
        if not period_info["enabled"]:
            return False

        product = product or self
        price = period_info["active_price"] + product._get_attributes_extra_price()
        product_uom = product.uom_id
        if uom and product_uom != uom:
            price = product_uom._compute_price(price, uom)

        currency = currency or self.currency_id
        conversion_date = date or fields.Date.context_today(self)
        if self.currency_id != currency:
            price = self.currency_id._convert(
                price,
                currency,
                self.env.company,
                conversion_date,
                round=False,
            )
        return price

    def _get_dynamic_pricing_period_info(self):
        self.ensure_one()
        if not self.dynamic_pricing_enabled:
            return {"enabled": False}

        tz_name = self.dynamic_pricing_tz or self.env.user.tz or "UTC"
        timezone = pytz.timezone(tz_name)
        now = datetime.now(pytz.UTC).astimezone(timezone)

        day_start = self._dynamic_pricing_hour_to_minutes(self.dynamic_pricing_day_start)
        night_start = self._dynamic_pricing_hour_to_minutes(self.dynamic_pricing_night_start)
        current_minute = now.hour * 60 + now.minute + (now.second / 60)

        if day_start < night_start:
            is_day = day_start <= current_minute < night_start
        else:
            is_day = current_minute >= day_start or current_minute < night_start

        active_period = "day" if is_day else "night"
        next_period = "night" if is_day else "day"
        next_start = night_start if is_day else day_start
        next_change = self._get_next_dynamic_pricing_change(now, timezone, next_start)

        return {
            "enabled": True,
            "active_period": active_period,
            "active_label": _("Day") if is_day else _("Night"),
            "active_price": (
                self.dynamic_pricing_day_price
                if is_day
                else self.dynamic_pricing_night_price
            ),
            "next_period": next_period,
            "next_label": _("Night") if is_day else _("Day"),
            "next_price": (
                self.dynamic_pricing_night_price
                if is_day
                else self.dynamic_pricing_day_price
            ),
            "next_change_ms": int(next_change.timestamp() * 1000),
            "timezone": tz_name,
        }

    @api.model
    def _dynamic_pricing_hour_to_minutes(self, hour):
        return int(round((hour % 24) * 60)) % (24 * 60)

    @api.model
    def _get_next_dynamic_pricing_change(self, now, timezone, start_minutes):
        start_hour, start_minute = divmod(start_minutes, 60)
        next_change = timezone.localize(
            datetime.combine(now.date(), time(hour=start_hour, minute=start_minute)),
            is_dst=False,
        )
        if next_change <= now:
            next_change += timedelta(days=1)
        return next_change
