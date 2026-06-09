from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    cricket_booking_id = fields.Many2one(
        "cricket.booking",
        string="Cricket Booking",
        copy=False,
    )
    cricket_hold_id = fields.Many2one(
        "cricket.booking.hold",
        string="Cricket Booking Hold",
        copy=False,
    )

    def action_confirm(self):
        result = super().action_confirm()
        for order in self:
            hold = order.cricket_hold_id
            if hold and hold.state == "active" and not order.cricket_booking_id:
                transaction = order.transaction_ids.filtered(
                    lambda tx: tx.state in ("authorized", "done")
                )[:1]
                booking = hold.action_convert_to_booking(payment_transaction=transaction)
                order.cricket_booking_id = booking.id
        return result


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    cricket_booking_id = fields.Many2one(
        "cricket.booking",
        string="Cricket Booking",
        copy=False,
    )
    cricket_lane_ids = fields.Many2many(
        "cricket.lane",
        "sale_order_line_cricket_lane_rel",
        "line_id",
        "lane_id",
        string="Cricket Lanes",
        copy=False,
    )
    cricket_slot_start = fields.Datetime(copy=False)
    cricket_slot_end = fields.Datetime(copy=False)
    cricket_price_breakdown_json = fields.Text(copy=False)
