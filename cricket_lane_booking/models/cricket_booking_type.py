from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class CricketBookingType(models.Model):
    _name = "cricket.booking.type"
    _description = "Cricket Booking Type"
    _order = "sequence, name"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    code = fields.Selection(
        [
            ("lane", "Book a Lane"),
            ("box_cricket", "Box Cricket"),
            ("event", "Box Cricket for Events"),
        ],
        required=True,
        default="lane",
    )
    description = fields.Text()
    product_id = fields.Many2one("product.product", string="Booking Product")
    default_duration_minutes = fields.Integer(default=60, required=True)
    play_minutes = fields.Integer(default=55, required=True)
    cleaning_minutes = fields.Integer(default=5, required=True)
    allow_instant_payment = fields.Boolean(default=True)
    create_crm_lead = fields.Boolean()
    active = fields.Boolean(default=True)
    website_published = fields.Boolean(default=True)
    image_1920 = fields.Image(max_width=1920, max_height=1920)
    addon_ids = fields.Many2many(
        "cricket.addon",
        "cricket_booking_type_addon_rel",
        "booking_type_id",
        "addon_id",
        string="Available Add-ons",
    )

    _code_unique = models.Constraint(
        "UNIQUE (code)",
        "Each booking type code must be unique.",
    )

    @api.constrains("default_duration_minutes", "play_minutes", "cleaning_minutes")
    def _check_durations(self):
        for booking_type in self:
            if booking_type.default_duration_minutes < 1:
                raise ValidationError(_("Slot duration must be positive."))
            if booking_type.play_minutes < 1:
                raise ValidationError(_("Play minutes must be positive."))
            if booking_type.cleaning_minutes < 0:
                raise ValidationError(_("Cleaning minutes cannot be negative."))
            expected = booking_type.play_minutes + booking_type.cleaning_minutes
            if expected > booking_type.default_duration_minutes:
                raise ValidationError(
                    _("Play time plus cleaning time cannot exceed slot duration.")
                )

    @api.onchange("code")
    def _onchange_code(self):
        for booking_type in self:
            if booking_type.code == "event":
                booking_type.allow_instant_payment = False
                booking_type.create_crm_lead = True
