import json
import uuid
from datetime import datetime, time, timedelta

import pytz
from dateutil import parser

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round


class CricketBookingHold(models.Model):
    _name = "cricket.booking.hold"
    _description = "Cricket Booking Hold"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(default="/", copy=False, readonly=True)
    session_token = fields.Char(index=True, copy=False)
    partner_id = fields.Many2one("res.partner", copy=False)
    customer_first_name = fields.Char(copy=False)
    customer_last_name = fields.Char(copy=False)
    customer_phone = fields.Char(copy=False)
    customer_email = fields.Char(copy=False)
    location_id = fields.Many2one("cricket.location", required=True, ondelete="restrict")
    booking_type_id = fields.Many2one(
        "cricket.booking.type",
        required=True,
        ondelete="restrict",
    )
    lane_ids = fields.Many2many(
        "cricket.lane",
        "cricket_booking_hold_lane_rel",
        "hold_id",
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
        "cricket_booking_hold_addon_rel",
        "hold_id",
        "addon_id",
        string="Add-ons",
    )
    price_total = fields.Monetary(currency_field="currency_id")
    price_breakdown_json = fields.Text(copy=False)
    expires_at = fields.Datetime(required=True, index=True)
    state = fields.Selection(
        [
            ("active", "Active"),
            ("expired", "Expired"),
            ("converted", "Converted"),
            ("cancelled", "Cancelled"),
        ],
        default="active",
        required=True,
        index=True,
        tracking=True,
    )
    sale_order_id = fields.Many2one("sale.order", copy=False)
    booking_id = fields.Many2one("cricket.booking", copy=False)
    currency_id = fields.Many2one(
        "res.currency",
        related="location_id.currency_id",
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="location_id.company_id",
        store=True,
        readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"].sudo()
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = sequence.next_by_code("cricket.booking.hold") or "/"
            vals.setdefault("session_token", uuid.uuid4().hex)
        return super().create(vals_list)

    @api.constrains("people_count", "slot_count", "slot_start", "play_end", "slot_end")
    def _check_hold_values(self):
        for hold in self:
            if hold.slot_count < 1:
                raise ValidationError(_("Slot count must be at least 1."))
            if hold.people_count < 1:
                raise ValidationError(_("People count must be at least 1."))
            if hold.slot_start >= hold.play_end:
                raise ValidationError(_("Play end must be after slot start."))
            if hold.play_end > hold.slot_end:
                raise ValidationError(_("Play end cannot be after internal slot end."))

    @api.model
    def _lock_booking_tables(self):
        self.env.cr.execute(
            "LOCK TABLE cricket_booking_hold, cricket_booking, cricket_slot_block "
            "IN SHARE ROW EXCLUSIVE MODE"
        )

    @api.model
    def _parse_datetime_in_location_tz(self, value, location):
        if isinstance(value, datetime):
            parsed = value
        else:
            parsed = parser.isoparse(str(value))
        if parsed.tzinfo:
            return parsed.astimezone(pytz.UTC).replace(tzinfo=None)
        timezone = pytz.timezone(location.timezone or "UTC")
        return timezone.localize(parsed, is_dst=False).astimezone(pytz.UTC).replace(
            tzinfo=None
        )

    @api.model
    def _get_slot_bounds(self, booking_type, slot_start):
        play_end = slot_start + timedelta(minutes=booking_type.play_minutes)
        slot_end = slot_start + timedelta(minutes=booking_type.default_duration_minutes)
        return play_end, slot_end

    @api.model
    def _get_slot_bounds_for_location(self, location, booking_type, slot_start):
        timezone = pytz.timezone(location.timezone or "UTC")
        slot_local = pytz.UTC.localize(slot_start).astimezone(timezone)
        rule = self.env["cricket.slot.rule"].sudo()._find_rule(
            location,
            booking_type,
            slot_local.date(),
        )
        play_minutes = rule.play_minutes if rule else booking_type.play_minutes
        cleaning_minutes = rule.cleaning_minutes if rule else booking_type.cleaning_minutes
        play_end = slot_start + timedelta(minutes=play_minutes)
        slot_end = slot_start + timedelta(minutes=play_minutes + cleaning_minutes)
        return play_end, slot_end

    @api.model
    def _get_slot_starts_from_payload(self, payload, location):
        values = payload.get("slot_starts") or []
        if not values and payload.get("slot_start"):
            values = [payload.get("slot_start")]
        if not values:
            raise UserError(_("Please select at least one time slot."))
        starts = [
            self._parse_datetime_in_location_tz(value, location)
            for value in values
        ]
        starts = sorted(set(starts))
        return starts

    @api.model
    def _get_multi_slot_bounds(self, location, booking_type, slot_starts):
        bounds = []
        previous_end = False
        for slot_start in slot_starts:
            play_end, slot_end = self._get_slot_bounds_for_location(
                location,
                booking_type,
                slot_start,
            )
            if previous_end and slot_start != previous_end:
                raise UserError(_("Please select continuous adjacent slots."))
            bounds.append((slot_start, play_end, slot_end))
            previous_end = slot_end
        return bounds[0][0], bounds[-1][1], bounds[-1][2], bounds

    @api.model
    def _expand_lanes(self, lanes):
        return lanes._get_physical_lanes()

    @api.model
    def _get_active_overlap_domain(self, lane_ids, slot_start, slot_end, exclude_hold=None):
        domain = [
            ("state", "=", "active"),
            ("expires_at", ">", fields.Datetime.now()),
            ("lane_ids", "in", lane_ids),
            ("slot_start", "<", slot_end),
            ("slot_end", ">", slot_start),
        ]
        if exclude_hold:
            domain.append(("id", "!=", exclude_hold.id))
        return domain

    @api.model
    def _get_confirmed_overlap_domain(self, lane_ids, slot_start, slot_end, exclude_booking=None):
        domain = [
            ("state", "in", ["confirmed", "checked_in"]),
            ("lane_ids", "in", lane_ids),
            ("slot_start", "<", slot_end),
            ("slot_end", ">", slot_start),
        ]
        if exclude_booking:
            domain.append(("id", "!=", exclude_booking.id))
        return domain

    @api.model
    def _get_block_overlap_domain(self, lane_ids, slot_start, slot_end, exclude_block=None):
        domain = [
            ("active", "=", True),
            ("lane_ids", "in", lane_ids),
            ("slot_start", "<", slot_end),
            ("slot_end", ">", slot_start),
        ]
        if exclude_block:
            domain.append(("id", "!=", exclude_block.id))
        return domain

    @api.model
    def _check_lanes_available(
        self,
        lanes,
        slot_start,
        slot_end,
        exclude_hold=None,
        exclude_booking=None,
        exclude_block=None,
        raise_error=True,
    ):
        lane_ids = lanes.ids
        hold = self.search(
            self._get_active_overlap_domain(lane_ids, slot_start, slot_end, exclude_hold),
            limit=1,
        )
        booking = self.env["cricket.booking"].search(
            self._get_confirmed_overlap_domain(
                lane_ids,
                slot_start,
                slot_end,
                exclude_booking,
            ),
            limit=1,
        )
        block = self.env["cricket.slot.block"].search(
            self._get_block_overlap_domain(lane_ids, slot_start, slot_end, exclude_block),
            limit=1,
        )
        available = not hold and not booking and not block
        if not available and raise_error:
            raise UserError(_("Selected lane is no longer available for this time."))
        return available

    @api.model
    def _validate_slot_policy(self, location, slot_start, slot_end):
        now = fields.Datetime.now()
        if slot_start < now + timedelta(minutes=location.minimum_notice_minutes):
            raise UserError(_("This slot does not satisfy the minimum booking notice."))
        max_start = now + timedelta(days=location.max_booking_days_ahead)
        if slot_start > max_start:
            raise UserError(_("This slot is outside the maximum booking window."))
        timezone = pytz.timezone(location.timezone or "UTC")
        local_start = pytz.UTC.localize(slot_start).astimezone(timezone)
        local_end = pytz.UTC.localize(slot_end).astimezone(timezone)
        if local_start.date() != local_end.date():
            raise UserError(_("Slots cannot cross location business days."))
        return True

    @api.model
    def _validate_slot_window(self, location, booking_type, slot_start, slot_end):
        timezone = pytz.timezone(location.timezone or "UTC")
        local_start = pytz.UTC.localize(slot_start).astimezone(timezone)
        local_end = pytz.UTC.localize(slot_end).astimezone(timezone)
        rule = self.env["cricket.slot.rule"].sudo()._find_rule(
            location,
            booking_type,
            local_start.date(),
        )
        open_float = rule.open_time_float if rule else location.default_open_time
        close_float = rule.close_time_float if rule else location.default_close_time
        start_float = local_start.hour + local_start.minute / 60.0
        end_float = local_end.hour + local_end.minute / 60.0
        if start_float < open_float or end_float > close_float:
            raise UserError(_("Selected slot is outside location opening hours."))
        return True

    @api.model
    def _calculate_price(
        self,
        location,
        booking_type,
        lanes,
        slot_start,
        people_count,
        addons,
    ):
        priced_lane = lanes.sorted(lambda lane: lane.base_price, reverse=True)[:1]
        base_price = priced_lane.base_price if priced_lane else 0.0
        included_people = max(lanes.mapped("included_people") or [0])
        extra_fee = max(lanes.mapped("extra_person_fee") or [0.0])
        people_fee = max(people_count - included_people, 0) * extra_fee
        addon_total = sum(addons.mapped("price"))
        final_price = base_price + people_fee + addon_total
        final_price = float_round(
            final_price,
            precision_rounding=location.currency_id.rounding,
        )
        return {
            "base_price": base_price,
            "lane_factor": 1.0,
            "time_factor": 1.0,
            "occupancy_factor": 1.0,
            "traffic_factor": 1.0,
            "competitor_factor": 1.0,
            "people_fee": people_fee,
            "addons": [
                {"id": addon.id, "name": addon.name, "price": addon.price}
                for addon in addons
            ],
            "subtotal_before_addons": base_price + people_fee,
            "addon_total": addon_total,
            "final_price": final_price,
            "currency": location.currency_id.name,
        }

    @api.model
    def _calculate_multi_slot_price(
        self,
        location,
        booking_type,
        lanes,
        slot_starts,
        people_count,
        addons,
    ):
        slot_breakdowns = []
        total = 0.0
        base_total = 0.0
        people_total = 0.0
        addon_total = 0.0
        max_time_factor = 1.0
        max_occupancy_factor = 1.0
        max_traffic_factor = 1.0
        max_competitor_factor = 1.0
        competitor_adjustment_total = 0.0
        competitor_price = False
        for slot_start in slot_starts:
            breakdown = self._calculate_price(
                location,
                booking_type,
                lanes,
                slot_start,
                people_count,
                addons,
            )
            slot_breakdowns.append({
                "slot_start": fields.Datetime.to_string(slot_start),
                "final_price": breakdown["final_price"],
                "base_price": breakdown["base_price"],
                "time_factor": breakdown.get("time_factor", 1.0),
                "occupancy_factor": breakdown.get("occupancy_factor", 1.0),
                "traffic_factor": breakdown.get("traffic_factor", 1.0),
                "competitor_factor": breakdown.get("competitor_factor", 1.0),
            })
            total += breakdown["final_price"]
            base_total += breakdown.get("base_price", 0.0)
            people_total += breakdown.get("people_fee", 0.0)
            addon_total += breakdown.get("addon_total", 0.0)
            max_time_factor = max(max_time_factor, breakdown.get("time_factor", 1.0))
            max_occupancy_factor = max(max_occupancy_factor, breakdown.get("occupancy_factor", 1.0))
            max_traffic_factor = max(max_traffic_factor, breakdown.get("traffic_factor", 1.0))
            max_competitor_factor = max(max_competitor_factor, breakdown.get("competitor_factor", 1.0))
            competitor_adjustment_total += breakdown.get("competitor_adjustment", 0.0)
            competitor_price = breakdown.get("competitor_price") or competitor_price
        final_price = float_round(
            total,
            precision_rounding=location.currency_id.rounding,
        )
        return {
            "slot_count": len(slot_starts),
            "base_price": base_total,
            "lane_factor": 1.0,
            "time_factor": max_time_factor,
            "occupancy_factor": max_occupancy_factor,
            "traffic_factor": max_traffic_factor,
            "competitor_factor": max_competitor_factor,
            "competitor_adjustment": competitor_adjustment_total,
            "competitor_price": competitor_price,
            "people_fee": people_total,
            "addons": [
                {"id": addon.id, "name": addon.name, "price": addon.price}
                for addon in addons
            ],
            "slots": slot_breakdowns,
            "subtotal_before_addons": final_price - addon_total,
            "addon_total": addon_total,
            "final_price": final_price,
            "currency": location.currency_id.name,
        }

    @api.model
    def _validate_people_and_addons(self, booking_type, lanes, people_count, addons):
        if people_count < 1:
            raise UserError(_("People count must be at least 1."))
        max_people = min(lanes.mapped("max_people") or [1])
        if people_count > max_people:
            raise UserError(_("This selection allows a maximum of %s people.") % max_people)
        for addon in addons:
            if not addon._is_selectable_for(booking_type, lanes):
                raise UserError(_("%s is not available for this booking.") % addon.name)

    @api.model
    def create_hold_from_payload(self, payload, session_token=None):
        location = self.env["cricket.location"].sudo().browse(
            int(payload.get("location_id") or 0)
        ).exists()
        if not location or not location.active or not location.website_published:
            raise UserError(_("Invalid location."))

        booking_type = self.env["cricket.booking.type"].sudo().search([
            ("code", "=", payload.get("booking_type")),
            ("active", "=", True),
            ("website_published", "=", True),
        ], limit=1)
        if not booking_type:
            raise UserError(_("Invalid booking type."))
        if not booking_type.allow_instant_payment:
            raise UserError(_("This booking type requires an inquiry."))

        selected_lanes = self.env["cricket.lane"].sudo().browse(
            [int(lane_id) for lane_id in payload.get("lane_ids", [])]
        ).exists()
        if not selected_lanes:
            raise UserError(_("Please select a lane."))
        if any(lane.location_id != location for lane in selected_lanes):
            raise UserError(_("Selected lanes do not belong to this location."))
        lanes = self._expand_lanes(selected_lanes)
        if any(lane.website_status != "available" for lane in lanes):
            raise UserError(_("Selected lane is unavailable."))

        slot_starts = self._get_slot_starts_from_payload(payload, location)
        slot_start, play_end, slot_end, bounds = self._get_multi_slot_bounds(
            location,
            booking_type,
            slot_starts,
        )
        for current_start, _current_play_end, current_end in bounds:
            self._validate_slot_policy(location, current_start, current_end)
            self._validate_slot_window(location, booking_type, current_start, current_end)

        people_count = int(payload.get("people_count") or 1)
        addons = self.env["cricket.addon"].sudo().browse(
            [int(addon_id) for addon_id in payload.get("addon_ids", [])]
        ).exists()
        self._validate_people_and_addons(booking_type, lanes, people_count, addons)

        self._lock_booking_tables()
        self._check_lanes_available(lanes, slot_start, slot_end)

        price_breakdown = self._calculate_multi_slot_price(
            location,
            booking_type,
            lanes,
            slot_starts,
            people_count,
            addons,
        )
        customer = payload.get("customer") or {}
        hold = self.sudo().create({
            "session_token": session_token or uuid.uuid4().hex,
            "customer_first_name": customer.get("first_name"),
            "customer_last_name": customer.get("last_name"),
            "customer_phone": customer.get("phone"),
            "customer_email": customer.get("email"),
            "location_id": location.id,
            "booking_type_id": booking_type.id,
            "lane_ids": [Command.set(lanes.ids)],
            "slot_start": slot_start,
            "play_end": play_end,
            "slot_end": slot_end,
            "slot_count": len(slot_starts),
            "people_count": people_count,
            "addon_ids": [Command.set(addons.ids)],
            "price_total": price_breakdown["final_price"],
            "price_breakdown_json": json.dumps(price_breakdown, default=str),
            "expires_at": fields.Datetime.now() + timedelta(minutes=location.hold_minutes),
        })
        return hold

    def _get_price_breakdown(self):
        self.ensure_one()
        if not self.price_breakdown_json:
            return {}
        return json.loads(self.price_breakdown_json)

    def _get_or_create_partner(self):
        self.ensure_one()
        if self.partner_id:
            return self.partner_id
        email = self.customer_email
        partner = self.env["res.partner"].sudo().search([("email", "=", email)], limit=1) if email else False
        if not partner:
            name = " ".join(
                part for part in [self.customer_first_name, self.customer_last_name] if part
            ) or email or self.customer_phone or _("Cricket Customer")
            partner = self.env["res.partner"].sudo().create({
                "name": name,
                "email": email,
                "phone": self.customer_phone,
            })
        self.partner_id = partner.id
        return partner

    def action_create_sale_order(self):
        self.ensure_one()
        if self.state != "active":
            raise UserError(_("Only active holds can be checked out."))
        if self.expires_at <= fields.Datetime.now():
            self.action_expire()
            raise UserError(_("This hold has expired. Please choose the slot again."))

        self._lock_booking_tables()
        self._check_lanes_available(
            self.lane_ids,
            self.slot_start,
            self.slot_end,
            exclude_hold=self,
        )

        if self.sale_order_id:
            return self.sale_order_id
        if not self.booking_type_id.product_id:
            raise UserError(_("Please configure a booking product on the booking type."))

        partner = self._get_or_create_partner()
        breakdown = self._get_price_breakdown()
        addon_total = breakdown.get("addon_total", sum(self.addon_ids.mapped("price")) * self.slot_count)
        booking_line_total = max(self.price_total - addon_total, 0.0)
        order_lines = [
            Command.create({
                "product_id": self.booking_type_id.product_id.id,
                "name": self._get_sale_line_name(),
                "product_uom_qty": 1.0,
                "price_unit": booking_line_total,
                "cricket_lane_ids": [Command.set(self.lane_ids.ids)],
                "cricket_slot_start": self.slot_start,
                "cricket_slot_end": self.slot_end,
                "cricket_price_breakdown_json": self.price_breakdown_json,
            })
        ]
        for addon in self.addon_ids:
            if not addon.product_id:
                raise UserError(_("Please configure a product for add-on %s.") % addon.name)
            order_lines.append(Command.create({
                "product_id": addon.product_id.id,
                "name": addon.name,
                "product_uom_qty": self.slot_count,
                "price_unit": addon.price,
                "cricket_lane_ids": [Command.set(self.lane_ids.ids)],
                "cricket_slot_start": self.slot_start,
                "cricket_slot_end": self.slot_end,
            }))
        order = self.env["sale.order"].sudo().create({
            "partner_id": partner.id,
            "cricket_hold_id": self.id,
            "order_line": order_lines,
        })
        self.sale_order_id = order.id
        return order

    def _get_sale_line_name(self):
        self.ensure_one()
        timezone = pytz.timezone(self.location_id.timezone or "UTC")
        local_start = pytz.UTC.localize(self.slot_start).astimezone(timezone)
        local_play_end = pytz.UTC.localize(self.play_end).astimezone(timezone)
        lane_names = ", ".join(self.lane_ids.mapped("name"))
        return _("%s - %s - %s to %s") % (
            self.booking_type_id.name,
            lane_names,
            local_start.strftime("%Y-%m-%d %I:%M %p"),
            local_play_end.strftime("%I:%M %p"),
        )

    def action_convert_to_booking(self, payment_transaction=None):
        self.ensure_one()
        if self.booking_id:
            return self.booking_id
        if self.state != "active":
            raise UserError(_("Only active holds can be converted."))
        if self.expires_at <= fields.Datetime.now():
            self.action_expire()
            raise UserError(_("This hold expired before payment confirmation."))
        self._lock_booking_tables()
        self._check_lanes_available(
            self.lane_ids,
            self.slot_start,
            self.slot_end,
            exclude_hold=self,
        )
        booking = self.env["cricket.booking"].sudo().create({
            "partner_id": self.partner_id.id,
            "customer_first_name": self.customer_first_name,
            "customer_last_name": self.customer_last_name,
            "customer_phone": self.customer_phone,
            "customer_email": self.customer_email,
            "location_id": self.location_id.id,
            "booking_type_id": self.booking_type_id.id,
            "lane_ids": [Command.set(self.lane_ids.ids)],
            "slot_start": self.slot_start,
            "play_end": self.play_end,
            "slot_end": self.slot_end,
            "slot_count": self.slot_count,
            "people_count": self.people_count,
            "addon_ids": [Command.set(self.addon_ids.ids)],
            "price_total": self.price_total,
            "price_breakdown_json": self.price_breakdown_json,
            "hold_id": self.id,
            "sale_order_id": self.sale_order_id.id,
            "payment_transaction_id": payment_transaction.id if payment_transaction else False,
            "appointment_type_id": self.lane_ids[:1].appointment_type_id.id,
            "state": "confirmed",
        })
        booking._create_calendar_event()
        self.write({
            "state": "converted",
            "booking_id": booking.id,
        })
        if self.sale_order_id:
            self.sale_order_id.write({"cricket_booking_id": booking.id})
            self.sale_order_id.order_line.write({"cricket_booking_id": booking.id})
        booking._send_confirmation_email()
        return booking

    def action_expire(self):
        self.filtered(lambda hold: hold.state == "active").write({"state": "expired"})

    def action_cancel(self):
        self.filtered(lambda hold: hold.state == "active").write({"state": "cancelled"})

    @api.model
    def _cron_expire_holds(self):
        expired = self.search([
            ("state", "=", "active"),
            ("expires_at", "<", fields.Datetime.now()),
        ])
        expired.action_expire()

    @api.model
    def quote_from_payload(self, payload):
        location = self.env["cricket.location"].sudo().browse(
            int(payload.get("location_id") or 0)
        ).exists()
        booking_type = self.env["cricket.booking.type"].sudo().search([
            ("code", "=", payload.get("booking_type")),
        ], limit=1)
        selected_lanes = self.env["cricket.lane"].sudo().browse(
            [int(lane_id) for lane_id in payload.get("lane_ids", [])]
        ).exists()
        if not location or not booking_type or not selected_lanes:
            raise UserError(_("Invalid quote request."))
        lanes = self._expand_lanes(selected_lanes)
        slot_starts = self._get_slot_starts_from_payload(payload, location)
        slot_start, play_end, slot_end, bounds = self._get_multi_slot_bounds(
            location,
            booking_type,
            slot_starts,
        )
        for current_start, _current_play_end, current_end in bounds:
            self._validate_slot_policy(location, current_start, current_end)
            self._validate_slot_window(location, booking_type, current_start, current_end)
        people_count = int(payload.get("people_count") or 1)
        addons = self.env["cricket.addon"].sudo().browse(
            [int(addon_id) for addon_id in payload.get("addon_ids", [])]
        ).exists()
        self._validate_people_and_addons(booking_type, lanes, people_count, addons)
        available = self._check_lanes_available(
            lanes,
            slot_start,
            slot_end,
            raise_error=False,
        )
        breakdown = self._calculate_multi_slot_price(
            location,
            booking_type,
            lanes,
            slot_starts,
            people_count,
            addons,
        )
        return {
            "available": available,
            "price_total": breakdown["final_price"],
            "currency": location.currency_id.name,
            "breakdown": breakdown,
            "slot_count": len(slot_starts),
            "play_end": fields.Datetime.to_string(play_end),
            "slot_end": fields.Datetime.to_string(slot_end),
        }
