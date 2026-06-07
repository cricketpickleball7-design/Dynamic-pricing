from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    appointment_dynamic_price_log_id = fields.Many2one(
        "appointment.dynamic.price.log",
        string="Appointment Dynamic Price Log",
        copy=False,
    )
    appointment_dynamic_price_locked = fields.Boolean(copy=False)
    appointment_dynamic_base_price = fields.Monetary(
        currency_field="currency_id",
        copy=False,
    )
    appointment_dynamic_final_price = fields.Monetary(
        currency_field="currency_id",
        copy=False,
    )
    appointment_dynamic_pricing_reason = fields.Text(copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        log_id = self.env.context.get("appointment_dynamic_price_log_id")
        if log_id:
            log = self.env["appointment.dynamic.price.log"].browse(log_id).exists()
            if log:
                for line in lines.filtered(lambda line: line.product_id == log.product_id):
                    line._apply_appointment_dynamic_price_log(log)
        return lines

    @api.depends(
        "product_id",
        "product_uom_id",
        "product_uom_qty",
        "appointment_dynamic_price_locked",
        "appointment_dynamic_final_price",
    )
    def _compute_price_unit(self):
        super()._compute_price_unit()
        for line in self.filtered("appointment_dynamic_price_locked"):
            line.price_unit = line.appointment_dynamic_final_price
            line.technical_price_unit = line.appointment_dynamic_final_price

    def _apply_appointment_dynamic_price_log(self, log):
        for line in self:
            line.update({
                "appointment_dynamic_price_log_id": log.id,
                "appointment_dynamic_price_locked": True,
                "appointment_dynamic_base_price": log.base_price,
                "appointment_dynamic_final_price": log.final_price,
                "appointment_dynamic_pricing_reason": log.reason,
                "price_unit": log.final_price,
                "technical_price_unit": log.final_price,
            })
            log.write({
                "sale_order_line_id": line.id,
                "confirmed": True,
            })
