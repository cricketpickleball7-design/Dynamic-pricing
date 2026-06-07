from odoo import fields, models


class AppointmentDynamicPriceLog(models.Model):
    _name = "appointment.dynamic.price.log"
    _description = "Appointment Dynamic Price Log"
    _order = "create_date desc, id desc"

    name = fields.Char(compute="_compute_name")
    config_id = fields.Many2one("appointment.dynamic.pricing.config", required=True)
    appointment_type_id = fields.Many2one("appointment.type", required=True)
    product_id = fields.Many2one("product.product", required=True)
    slot_datetime = fields.Datetime(required=True)
    currency_id = fields.Many2one("res.currency", required=True)
    base_price = fields.Monetary(currency_field="currency_id")
    minimum_price = fields.Monetary(currency_field="currency_id")
    maximum_price = fields.Monetary(currency_field="currency_id")
    raw_price = fields.Monetary(currency_field="currency_id")
    final_price = fields.Monetary(currency_field="currency_id")
    final_score = fields.Float()
    adjustment_percent = fields.Float()
    time_score = fields.Float()
    traffic_score = fields.Float()
    session_score = fields.Float()
    behavior_score = fields.Float()
    competitor_score = fields.Float()
    applied_rule_id = fields.Many2one("appointment.dynamic.pricing.rule")
    signal_id = fields.Many2one("appointment.pricing.signal")
    competitor_rate_id = fields.Many2one("appointment.competitor.rate")
    sale_order_line_id = fields.Many2one("sale.order.line")
    sale_order_id = fields.Many2one(related="sale_order_line_id.order_id", store=True)
    calendar_event_id = fields.Many2one("calendar.event")
    confirmed = fields.Boolean()
    reason = fields.Text()
    request_payload = fields.Text()
    response_payload = fields.Text()

    def _compute_name(self):
        for log in self:
            log.name = "%s - %s" % (
                log.appointment_type_id.display_name or "Appointment",
                log.slot_datetime or "",
            )

