from odoo import _, fields, models


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

    def _cart_update_line_quantity(self, line_id, quantity, **kwargs):
        if self:
            self.ensure_one()
        order_line = self.order_line.filtered(lambda line: line.id == line_id)[:1]
        if order_line and order_line._is_cricket_booking_cart_line():
            warning = _(
                "Cricket booking cart lines are locked. "
                "Please start a new booking to change lane, time, people, or add-ons."
            )
            order_line.shop_warning = warning
            return {
                "added_qty": 0,
                "line_id": order_line.id,
                "quantity": order_line.product_uom_qty,
                "warning": warning,
            }
        return super()._cart_update_line_quantity(line_id, quantity, **kwargs)


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

    def _is_cricket_booking_cart_line(self):
        self.ensure_one()
        return bool(
            self.order_id.cricket_hold_id
            and self.cricket_lane_ids
            and self.cricket_slot_start
        )

    def _is_sellable(self):
        self.ensure_one()
        if self._is_cricket_booking_cart_line():
            return False
        return super()._is_sellable()
