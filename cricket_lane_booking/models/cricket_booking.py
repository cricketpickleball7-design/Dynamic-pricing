import json
from datetime import date, datetime, time, timedelta

import pytz

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class CricketBooking(models.Model):
    _name = "cricket.booking"
    _description = "Cricket Booking"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "slot_start desc, id desc"

    name = fields.Char(default="/", copy=False, readonly=True)
    partner_id = fields.Many2one("res.partner", required=True)
    customer_first_name = fields.Char()
    customer_last_name = fields.Char()
    customer_phone = fields.Char()
    customer_email = fields.Char()
    location_id = fields.Many2one("cricket.location", required=True, ondelete="restrict")
    booking_type_id = fields.Many2one(
        "cricket.booking.type",
        required=True,
        ondelete="restrict",
    )
    lane_ids = fields.Many2many(
        "cricket.lane",
        "cricket_booking_lane_rel",
        "booking_id",
        "lane_id",
        string="Blocked Lanes",
        required=True,
    )
    slot_start = fields.Datetime(required=True, index=True)
    play_end = fields.Datetime(required=True)
    slot_end = fields.Datetime(required=True, index=True)
    slot_count = fields.Integer(default=1, required=True)
    people_count = fields.Integer(required=True)
    addon_ids = fields.Many2many(
        "cricket.addon",
        "cricket_booking_addon_rel",
        "booking_id",
        "addon_id",
        string="Add-ons",
    )
    price_total = fields.Monetary(currency_field="currency_id")
    price_breakdown_json = fields.Text(copy=False)
    hold_id = fields.Many2one("cricket.booking.hold", copy=False)
    sale_order_id = fields.Many2one("sale.order", copy=False)
    invoice_id = fields.Many2one("account.move", copy=False)
    payment_transaction_id = fields.Many2one("payment.transaction", copy=False)
    calendar_event_id = fields.Many2one("calendar.event", copy=False)
    appointment_type_id = fields.Many2one("appointment.type", copy=False)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("held", "Held"),
            ("payment_pending", "Payment Pending"),
            ("confirmed", "Confirmed"),
            ("checked_in", "Checked In"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
            ("no_show", "No Show"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    cancellation_deadline = fields.Datetime()
    cancellation_policy_text = fields.Text(
        default="No cancellation for paid booking within 24 hours of event time."
    )
    company_id = fields.Many2one(
        "res.company",
        related="location_id.company_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="location_id.currency_id",
        store=True,
        readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"].sudo()
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = sequence.next_by_code("cricket.booking") or "/"
        bookings = super().create(vals_list)
        for booking in bookings:
            if not booking.cancellation_deadline:
                booking.cancellation_deadline = booking.slot_start - timedelta(hours=24)
        return bookings

    @api.constrains("people_count", "slot_count", "slot_start", "play_end", "slot_end", "lane_ids", "state")
    def _check_booking_values(self):
        for booking in self:
            if booking.slot_count < 1:
                raise ValidationError(_("Slot count must be at least 1."))
            if booking.people_count < 1:
                raise ValidationError(_("People count must be at least 1."))
            if booking.slot_start >= booking.play_end:
                raise ValidationError(_("Play end must be after slot start."))
            if booking.play_end > booking.slot_end:
                raise ValidationError(_("Play end cannot be after internal slot end."))
            if booking.state in ("confirmed", "checked_in"):
                available = self.env["cricket.booking.hold"]._check_lanes_available(
                    booking.lane_ids,
                    booking.slot_start,
                    booking.slot_end,
                    exclude_hold=booking.hold_id,
                    exclude_booking=booking,
                    raise_error=False,
                )
                if not available:
                    raise ValidationError(_("Another booking already overlaps this slot."))

    def _create_calendar_event(self):
        for booking in self.filtered(lambda record: not record.calendar_event_id):
            event = self.env["calendar.event"].sudo().create({
                "name": booking.name,
                "start": booking.slot_start,
                "stop": booking.slot_end,
                "partner_ids": [Command.set(booking.partner_id.ids)],
                "cricket_booking_id": booking.id,
                "cricket_hold_id": booking.hold_id.id,
            })
            booking.calendar_event_id = event.id

    def _send_confirmation_email(self):
        template = self.env.ref(
            "cricket_lane_booking.mail_template_cricket_booking_confirmation",
            raise_if_not_found=False,
        )
        if template:
            for booking in self:
                template.sudo().send_mail(booking.id, force_send=False)

    def action_cancel(self):
        for booking in self:
            booking.state = "cancelled"
            if booking.calendar_event_id:
                booking.calendar_event_id.unlink()

    def action_checked_in(self):
        self.write({"state": "checked_in"})

    def action_completed(self):
        self.write({"state": "completed"})

    @api.model
    def _date_from_string(self, value):
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value))

    @api.model
    def _float_to_time(self, value):
        minutes = int(round((value % 24) * 60))
        return time(minutes // 60, minutes % 60)

    @api.model
    def _local_to_utc_naive(self, location, value):
        timezone = pytz.timezone(location.timezone or "UTC")
        return timezone.localize(value, is_dst=False).astimezone(pytz.UTC).replace(
            tzinfo=None
        )

    @api.model
    def _utc_to_local_iso(self, location, value):
        timezone = pytz.timezone(location.timezone or "UTC")
        return pytz.UTC.localize(value).astimezone(timezone).isoformat()

    @api.model
    def _slot_label(self, location, slot_start, play_end):
        timezone = pytz.timezone(location.timezone or "UTC")
        local_start = pytz.UTC.localize(slot_start).astimezone(timezone)
        local_play_end = pytz.UTC.localize(play_end).astimezone(timezone)
        return "%s - %s" % (
            local_start.strftime("%-I:%M %p") if hasattr(local_start, "strftime") else "",
            local_play_end.strftime("%-I:%M %p") if hasattr(local_play_end, "strftime") else "",
        )

    @api.model
    def _make_slot_label(self, location, slot_start, play_end):
        timezone = pytz.timezone(location.timezone or "UTC")
        local_start = pytz.UTC.localize(slot_start).astimezone(timezone)
        local_play_end = pytz.UTC.localize(play_end).astimezone(timezone)
        # Windows does not support %-I, so strip a leading zero manually.
        start_label = local_start.strftime("%I:%M %p").lstrip("0")
        end_label = local_play_end.strftime("%I:%M %p").lstrip("0")
        return "%s - %s" % (start_label, end_label)

    @api.model
    def generate_slots(
        self,
        location_id,
        booking_type_code,
        lane_ids,
        target_date,
        people_count=1,
        addon_ids=None,
    ):
        location = self.env["cricket.location"].sudo().browse(int(location_id)).exists()
        booking_type = self.env["cricket.booking.type"].sudo().search([
            ("code", "=", booking_type_code),
            ("active", "=", True),
            ("website_published", "=", True),
        ], limit=1)
        selected_lanes = self.env["cricket.lane"].sudo().browse(
            [int(lane_id) for lane_id in lane_ids]
        ).exists()
        if not location or not booking_type or not selected_lanes:
            return {"date": str(target_date), "slots": []}
        lanes = selected_lanes._get_physical_lanes()
        target = self._date_from_string(target_date)
        rule = self.env["cricket.slot.rule"].sudo()._find_rule(
            location,
            booking_type,
            target,
        )

        open_float = rule.open_time_float if rule else location.default_open_time
        close_float = rule.close_time_float if rule else location.default_close_time
        step_minutes = rule.slot_step_minutes if rule else booking_type.default_duration_minutes
        play_minutes = rule.play_minutes if rule else booking_type.play_minutes
        cleaning_minutes = rule.cleaning_minutes if rule else booking_type.cleaning_minutes
        slot_minutes = play_minutes + cleaning_minutes
        local_open = datetime.combine(target, self._float_to_time(open_float))
        local_close = datetime.combine(target, self._float_to_time(close_float))

        slots = []
        hold_model = self.env["cricket.booking.hold"].sudo()
        addons = self.env["cricket.addon"].sudo().browse(addon_ids or []).exists()
        current = local_open
        while current + timedelta(minutes=slot_minutes) <= local_close:
            slot_start = self._local_to_utc_naive(location, current)
            play_end = slot_start + timedelta(minutes=play_minutes)
            slot_end = slot_start + timedelta(minutes=slot_minutes)
            policy_ok = True
            try:
                hold_model._validate_slot_policy(location, slot_start, slot_end)
            except UserError:
                policy_ok = False
            available = policy_ok and hold_model._check_lanes_available(
                lanes,
                slot_start,
                slot_end,
                raise_error=False,
            )
            estimated_price = False
            if available:
                breakdown = hold_model._calculate_price(
                    location,
                    booking_type,
                    lanes,
                    slot_start,
                    int(people_count or 1),
                    addons,
                )
                estimated_price = breakdown["final_price"]
            slots.append({
                "slot_start": self._utc_to_local_iso(location, slot_start),
                "play_end": self._utc_to_local_iso(location, play_end),
                "slot_end": self._utc_to_local_iso(location, slot_end),
                "label": self._make_slot_label(location, slot_start, play_end),
                "available": available,
                "estimated_price": estimated_price,
            })
            current += timedelta(minutes=step_minutes)
        return {"date": str(target), "slots": slots}

    @api.model
    def occupancy_percent(self, location, lanes, slot_start, slot_end):
        all_physical_lanes = self.env["cricket.lane"].sudo().search([
            ("location_id", "=", location.id),
            ("lane_type", "=", "individual"),
            ("active", "=", True),
            ("website_published", "=", True),
        ])
        total = len(all_physical_lanes)
        if not total:
            return 0.0
        blocked_lane_ids = set()
        active_holds = self.env["cricket.booking.hold"].sudo().search([
            ("state", "=", "active"),
            ("expires_at", ">", fields.Datetime.now()),
            ("location_id", "=", location.id),
            ("slot_start", "<", slot_end),
            ("slot_end", ">", slot_start),
        ])
        confirmed_bookings = self.sudo().search([
            ("state", "in", ["confirmed", "checked_in"]),
            ("location_id", "=", location.id),
            ("slot_start", "<", slot_end),
            ("slot_end", ">", slot_start),
        ])
        for record in active_holds:
            blocked_lane_ids.update(record.lane_ids.ids)
        for record in confirmed_bookings:
            blocked_lane_ids.update(record.lane_ids.ids)
        blocked_lane_ids.update(lanes.ids)
        return min((len(blocked_lane_ids) / total) * 100.0, 100.0)

    def get_price_breakdown(self):
        self.ensure_one()
        if not self.price_breakdown_json:
            return {}
        return json.loads(self.price_breakdown_json)
