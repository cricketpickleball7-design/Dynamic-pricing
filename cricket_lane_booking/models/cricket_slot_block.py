from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError


class CricketSlotBlock(models.Model):
    _name = "cricket.slot.block"
    _description = "Cricket Resource Slot Block"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "slot_start desc, id desc"

    name = fields.Char(required=True, default="Resource Block", tracking=True)
    location_id = fields.Many2one("cricket.location", required=True, ondelete="restrict")
    lane_ids = fields.Many2many(
        "cricket.lane",
        "cricket_slot_block_lane_rel",
        "block_id",
        "lane_id",
        string="Blocked Lanes",
        required=True,
    )
    slot_start = fields.Datetime(required=True, index=True, tracking=True)
    slot_end = fields.Datetime(required=True, index=True, tracking=True)
    reason = fields.Selection(
        [
            ("maintenance", "Maintenance"),
            ("private_event", "Private Event"),
            ("training", "Training"),
            ("admin_hold", "Admin Hold"),
            ("other", "Other"),
        ],
        default="admin_hold",
        required=True,
        tracking=True,
    )
    note = fields.Text()
    active = fields.Boolean(default=True, tracking=True)
    company_id = fields.Many2one(
        "res.company",
        related="location_id.company_id",
        store=True,
        readonly=True,
    )

    @api.constrains("location_id", "lane_ids", "slot_start", "slot_end", "active")
    def _check_slot_block_values(self):
        hold_model = self.env["cricket.booking.hold"]
        for block in self:
            if block.slot_start >= block.slot_end:
                raise ValidationError(_("Block end must be after block start."))
            if any(lane.location_id != block.location_id for lane in block.lane_ids):
                raise ValidationError(_("All blocked lanes must belong to the selected location."))
            if block.active:
                available = hold_model._check_lanes_available(
                    block.lane_ids._get_physical_lanes(),
                    block.slot_start,
                    block.slot_end,
                    exclude_block=block,
                    raise_error=False,
                )
                if not available:
                    raise ValidationError(_("This block overlaps an existing booking, hold, or block."))

    @api.onchange("lane_ids")
    def _onchange_lane_ids(self):
        for block in self:
            expanded_lanes = block.lane_ids._get_physical_lanes()
            if expanded_lanes and expanded_lanes != block.lane_ids:
                block.lane_ids = [Command.set(expanded_lanes.ids)]
