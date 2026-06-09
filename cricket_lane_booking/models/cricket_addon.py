from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class CricketAddon(models.Model):
    _name = "cricket.addon"
    _description = "Cricket Booking Add-on"
    _order = "sequence, name"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    product_id = fields.Many2one("product.product", string="Service Product")
    price = fields.Monetary(currency_field="currency_id", required=True)
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    active = fields.Boolean(default=True)
    website_published = fields.Boolean(default=True)
    booking_type_ids = fields.Many2many(
        "cricket.booking.type",
        "cricket_booking_type_addon_rel",
        "addon_id",
        "booking_type_id",
        string="Booking Types",
    )
    lane_ids = fields.Many2many(
        "cricket.lane",
        "cricket_addon_lane_rel",
        "addon_id",
        "lane_id",
        string="Allowed Lanes",
    )
    state = fields.Selection(
        [
            ("available", "Available"),
            ("coming_soon", "Coming Soon"),
            ("disabled", "Disabled"),
        ],
        default="available",
        required=True,
    )
    max_quantity = fields.Integer(default=1, required=True)
    description = fields.Text()

    @api.constrains("price", "max_quantity")
    def _check_addon_values(self):
        for addon in self:
            if addon.price < 0:
                raise ValidationError(_("Add-on price cannot be negative."))
            if addon.max_quantity < 1:
                raise ValidationError(_("Maximum quantity must be at least 1."))

    def _is_selectable_for(self, booking_type, lanes):
        self.ensure_one()
        if not self.active or not self.website_published or self.state != "available":
            return False
        if self.booking_type_ids and booking_type not in self.booking_type_ids:
            return False
        if self.lane_ids and not (self.lane_ids & lanes):
            return False
        return True
