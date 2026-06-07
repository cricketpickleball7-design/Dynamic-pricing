from odoo import fields, models


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    appointment_dynamic_price_log_id = fields.Many2one(
        "appointment.dynamic.price.log",
        string="Appointment Dynamic Price Log",
        copy=False,
    )
    appointment_dynamic_price_locked = fields.Boolean(copy=False)
    appointment_dynamic_base_price = fields.Monetary(
        currency_field="appointment_dynamic_currency_id",
        copy=False,
    )
    appointment_dynamic_final_price = fields.Monetary(
        currency_field="appointment_dynamic_currency_id",
        copy=False,
    )
    appointment_dynamic_currency_id = fields.Many2one("res.currency", copy=False)
    appointment_dynamic_pricing_reason = fields.Text(copy=False)

    def _apply_appointment_dynamic_price_log(self, log):
        for event in self:
            event.write({
                "appointment_dynamic_price_log_id": log.id,
                "appointment_dynamic_price_locked": True,
                "appointment_dynamic_base_price": log.base_price,
                "appointment_dynamic_final_price": log.final_price,
                "appointment_dynamic_currency_id": log.currency_id.id,
                "appointment_dynamic_pricing_reason": log.reason,
            })
            log.write({
                "calendar_event_id": event.id,
                "confirmed": True,
            })

