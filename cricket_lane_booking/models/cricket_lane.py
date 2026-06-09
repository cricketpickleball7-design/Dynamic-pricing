from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class CricketLane(models.Model):
    _name = "cricket.lane"
    _description = "Cricket Lane"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "location_id, sequence, name"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True)
    location_id = fields.Many2one(
        "cricket.location",
        required=True,
        ondelete="cascade",
        tracking=True,
    )
    sequence = fields.Integer(default=10)
    length_ft = fields.Integer(string="Length (FT)", required=True)
    lane_type = fields.Selection(
        [
            ("individual", "Individual Lane"),
            ("box_bundle", "Box Bundle"),
        ],
        default="individual",
        required=True,
    )
    lane_ids = fields.Many2many(
        "cricket.lane",
        "cricket_lane_bundle_rel",
        "bundle_id",
        "lane_id",
        string="Bundled Lanes",
        domain="[('location_id', '=', location_id), ('lane_type', '=', 'individual')]",
    )
    appointment_type_id = fields.Many2one(
        "appointment.type",
        string="Appointment Type",
        help="Optional link to Odoo's appointment type for reporting/integration.",
    )
    appointment_resource_id = fields.Integer(
        string="Appointment Resource ID",
        help=(
            "Optional numeric ID of appointment.resource on databases that have "
            "the full Appointments resource model installed."
        ),
    )
    calendar_resource_id = fields.Many2one("resource.resource", string="Calendar Resource")
    max_people = fields.Integer(default=8, required=True)
    included_people = fields.Integer(default=2, required=True)
    extra_person_fee = fields.Monetary(currency_field="currency_id", default=0.0)
    base_price = fields.Monetary(currency_field="currency_id", required=True)
    currency_id = fields.Many2one(
        "res.currency",
        related="location_id.currency_id",
        store=True,
        readonly=True,
    )
    active = fields.Boolean(default=True)
    website_published = fields.Boolean(default=True)
    color = fields.Integer(default=0)
    website_status = fields.Selection(
        [
            ("available", "Available"),
            ("unavailable", "Unavailable"),
            ("maintenance", "Maintenance"),
        ],
        default="available",
        required=True,
    )
    image_1920 = fields.Image(max_width=1920, max_height=1920)
    today_booking_count = fields.Integer(compute="_compute_dashboard_metrics")
    active_hold_count = fields.Integer(compute="_compute_dashboard_metrics")
    active_block_count = fields.Integer(compute="_compute_dashboard_metrics")
    next_booking_start = fields.Datetime(compute="_compute_dashboard_metrics")

    _code_location_unique = models.Constraint(
        "UNIQUE (code, location_id)",
        "Lane code must be unique per location.",
    )

    @api.constrains(
        "lane_type",
        "lane_ids",
        "max_people",
        "included_people",
        "extra_person_fee",
        "base_price",
    )
    def _check_lane_values(self):
        for lane in self:
            if lane.max_people < 1:
                raise ValidationError(_("Maximum people must be at least 1."))
            if lane.included_people < 0:
                raise ValidationError(_("Included people cannot be negative."))
            if lane.included_people > lane.max_people:
                raise ValidationError(_("Included people cannot exceed maximum people."))
            if lane.extra_person_fee < 0:
                raise ValidationError(_("Extra person fee cannot be negative."))
            if lane.base_price < 0:
                raise ValidationError(_("Base price cannot be negative."))
            if lane.lane_type == "box_bundle" and not lane.lane_ids:
                raise ValidationError(_("A box cricket bundle must contain child lanes."))
            if lane.lane_type == "individual" and lane.lane_ids:
                raise ValidationError(_("Only bundle lanes can contain child lanes."))
            if lane in lane.lane_ids:
                raise ValidationError(_("A lane cannot include itself in a bundle."))

    def _get_physical_lanes(self):
        lanes = self.env["cricket.lane"]
        for lane in self:
            if lane.lane_type == "box_bundle":
                lanes |= lane.lane_ids.filtered(lambda child: child.lane_type == "individual")
            else:
                lanes |= lane
        return lanes

    def _get_public_dict(self):
        self.ensure_one()
        physical_lanes = self._get_physical_lanes()
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "length_ft": self.length_ft,
            "lane_type": self.lane_type,
            "lane_ids": physical_lanes.ids,
            "max_people": self.max_people,
            "included_people": self.included_people,
            "extra_person_fee": self.extra_person_fee,
            "base_price": self.base_price,
            "available": self.website_status == "available",
        }

    def _compute_dashboard_metrics(self):
        now = fields.Datetime.now()
        today_start = fields.Datetime.to_datetime(fields.Date.today())
        today_end = today_start.replace(hour=23, minute=59, second=59)
        Booking = self.env["cricket.booking"].sudo()
        Hold = self.env["cricket.booking.hold"].sudo()
        Block = self.env["cricket.slot.block"].sudo()
        for lane in self:
            lane_ids = lane._get_physical_lanes().ids
            lane.today_booking_count = Booking.search_count([
                ("lane_ids", "in", lane_ids),
                ("state", "in", ["confirmed", "checked_in"]),
                ("slot_start", ">=", today_start),
                ("slot_start", "<=", today_end),
            ])
            lane.active_hold_count = Hold.search_count([
                ("lane_ids", "in", lane_ids),
                ("state", "=", "active"),
                ("expires_at", ">", now),
            ])
            lane.active_block_count = Block.search_count([
                ("lane_ids", "in", lane_ids),
                ("active", "=", True),
                ("slot_end", ">", now),
            ])
            next_booking = Booking.search([
                ("lane_ids", "in", lane_ids),
                ("state", "in", ["confirmed", "checked_in"]),
                ("slot_start", ">=", now),
            ], order="slot_start asc", limit=1)
            lane.next_booking_start = next_booking.slot_start
