/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { laneMapHtml } from "./cricket_lane_map";
import { datePickerHtml } from "./cricket_date_picker";
import { pricingSummaryHtml } from "./cricket_pricing_summary";

function localDateValue(date = new Date()) {
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${date.getFullYear()}-${month}-${day}`;
}

publicWidget.registry.CricketBookingWidget = publicWidget.Widget.extend({
    selector: ".o_cricket_booking_widget",
    events: {
        "click .o_booking_type": "_onBookingType",
        "change .o_location_select": "_onLocation",
        "click .o_cricket_lane_card": "_onLane",
        "click .o_cricket_box_area": "_onLane",
        "click .o_cricket_lane_strip": "_onLane",
        "click .o_lane_bundle_summary": "_onLane",
        "click .o_cricket_date": "_onDate",
        "change .o_cricket_date_input": "_onNativeDate",
        "click .o_slot": "_onSlot",
        "click .o_people_minus": "_onPeopleMinus",
        "click .o_people_plus": "_onPeoplePlus",
        "change .o_addon_input": "_onAddon",
        "input .o_customer_input": "_onCustomerInput",
        "click .o_checkout_button": "_onCheckout",
        "input .o_event_input": "_onEventInput",
        "click .o_event_submit": "_onEventSubmit",
    },

    async start() {
        this.state = {
            bookingType: "lane",
            locationId: false,
            laneIds: [],
            date: localDateValue(),
            slotStart: false,
            slotStarts: [],
            peopleCount: 1,
            addonIds: [],
            customer: {},
            currency: "",
        };
        await this._loadConfig();
        await this._loadLanes();
        this._render();
        this._track("page_view");
    },

    async _api(url, options = {}) {
        const response = await fetch(url, options);
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Request failed.");
        }
        return data;
    },

    async _post(url, payload) {
        return this._api(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
    },

    async _loadConfig() {
        this.config = await this._api("/cricket/api/config");
        const firstLocation = this.config.locations[0];
        if (firstLocation) {
            this.state.locationId = firstLocation.id;
            this.state.location = firstLocation;
            this.state.currency = firstLocation.currency;
        }
    },

    async _loadLanes() {
        if (this.state.bookingType === "event") {
            this.lanes = [];
            this.slots = [];
            this.state.quote = false;
            return;
        }
        if (!this.state.locationId) {
            this.lanes = [];
            return;
        }
        const data = await this._api(`/cricket/api/lanes?location_id=${this.state.locationId}&booking_type=${this.state.bookingType}&date=${this.state.date}`);
        this.lanes = data.lanes || [];
        this.boxCricket = data.box_cricket;
        if (this.state.bookingType === "box_cricket" && this.boxCricket) {
            this.state.laneIds = [this.boxCricket.id];
        } else if (!this.state.laneIds.length && this.lanes.length) {
            this.state.laneIds = [this.lanes[0].id];
        }
        await this._loadSlots();
    },

    async _loadSlots() {
        if (!this.state.locationId || !this.state.laneIds.length || !this.state.date) {
            this.slots = [];
            return;
        }
        const laneId = this.state.laneIds[0];
        const data = await this._api(`/cricket/api/slots?location_id=${this.state.locationId}&booking_type=${this.state.bookingType}&lane_id=${laneId}&date=${this.state.date}&people_count=${this.state.peopleCount}`);
        this.slots = data.slots || [];
        const availableValues = new Set(this.slots.filter((slot) => slot.available).map((slot) => slot.slot_start));
        this.state.slotStarts = (this.state.slotStarts || []).filter((value) => availableValues.has(value));
        if (!this.state.slotStarts.length) {
            const first = this.slots.find((slot) => slot.available);
            this.state.slotStarts = first ? [first.slot_start] : [];
        }
        this.state.slotStart = this.state.slotStarts[0] || false;
        await this._quote();
    },

    async _quote() {
        if (!this.state.locationId || !this.state.laneIds.length || !this.state.slotStarts.length) {
            this.state.quote = false;
            return;
        }
        try {
            this.state.quote = await this._post("/cricket/api/quote", this._payload());
        } catch (error) {
            this.state.quote = { available: false, error: error.message };
        }
    },

    _payload() {
        return {
            location_id: this.state.locationId,
            booking_type: this.state.bookingType,
            lane_ids: this.state.laneIds,
            slot_start: this.state.slotStart,
            slot_starts: this.state.slotStarts,
            people_count: this.state.peopleCount,
            addon_ids: this.state.addonIds,
            customer: this.state.customer,
        };
    },

    _render() {
        const typeCards = (this.config.booking_types || []).map((type) => `
            <button type="button" class="o_booking_type ${this.state.bookingType === type.code ? "is-selected" : ""}" data-code="${type.code}">
                <span class="o_radio_dot"></span>
                <span class="o_type_copy">
                    <strong>${this._typeTitle(type)}</strong>
                    <em>${this._typeDescription(type)}</em>
                </span>
            </button>
        `).join("");
        const locations = (this.config.locations || []).map((location) => `
            <option value="${location.id}" ${Number(this.state.locationId) === Number(location.id) ? "selected" : ""}>${location.name}</option>
        `).join("");
        const eventMode = this.state.bookingType === "event";
        const slots = (this.slots || []).map((slot) => `
            <button type="button" class="o_slot ${(this.state.slotStarts || []).includes(slot.slot_start) ? "is-selected" : ""}" data-slot="${slot.slot_start}" ${slot.available ? "" : "disabled"}>
                <span>${slot.label}</span>
                ${slot.estimated_price ? `<small>${this.state.currency} ${Number(slot.estimated_price).toFixed(2)}</small>` : ""}
            </button>
        `).join("");
        const addons = (this.config.addons || []).map((addon) => {
            const disabled = addon.state !== "available";
            const checked = this.state.addonIds.includes(addon.id);
            return `
                <label class="o_addon ${disabled ? "is-disabled" : ""}">
                    <input class="o_addon_input" type="checkbox" value="${addon.id}" ${checked ? "checked" : ""} ${disabled ? "disabled" : ""}/>
                    <span>${addon.name}</span>
                    ${disabled ? `<em class="o_coming_soon">COMING SOON</em>` : ""}
                    <strong>+ ${this.state.currency} ${Number(addon.price || 0).toFixed(2)}</strong>
                </label>
            `;
        }).join("");
        const total = Number(this.state.quote?.price_total || 0).toFixed(2);
        const hero = this._heroHtml(typeCards);
        const bookingBody = eventMode ? this._eventHtml(hero, locations, addons) : `
            <div class="o_cricket_booking_experience">
                ${hero}
                <main class="o_cricket_booking_main">
                    <div class="o_form_step o_form_step_full">
                        <label>1. LOCATION</label>
                        <select class="o_location_select">${locations}</select>
                    </div>
                    <div class="o_form_step o_form_step_full">
                        <label>2. SELECT LANE</label>
                        ${laneMapHtml(this.state, this.lanes || [], this.boxCricket)}
                    </div>
                    <div class="o_booking_columns">
                        <div class="o_form_step">
                            <label>3. DATE</label>
                            ${datePickerHtml(this.state)}
                        </div>
                        <div class="o_form_step">
                            <label>4. TIME</label>
                            <span class="o_lane_context">${this._selectedLaneLabel()}</span>
                            <div class="o_time_dropdown">
                                <div class="o_time_value">${this._selectedSlotLabel()}</div>
                                <div class="o_slot_count">${this.state.slotStarts.length || 0} selected</div>
                            </div>
                            <div class="o_slots">${slots || "<span>No slots available</span>"}</div>
                        </div>
                        <div class="o_form_step">
                            <label>5. NUMBER OF PEOPLE</label>
                            <span class="o_lane_context">${this._selectedLaneLabel()}</span>
                            <div class="o_people">
                                <button type="button" class="o_people_minus">-</button>
                                <strong>${this.state.peopleCount}</strong>
                                <button type="button" class="o_people_plus">+</button>
                            </div>
                        </div>
                    </div>
                    <div class="o_customer_grid">
                        <label class="o_field_group">6. FIRST NAME<input class="o_customer_input" data-field="first_name" placeholder="First name" value="${this.state.customer.first_name || ""}"/></label>
                        <label class="o_field_group">7. LAST NAME<input class="o_customer_input" data-field="last_name" placeholder="Last name" value="${this.state.customer.last_name || ""}"/></label>
                        <label class="o_field_group">8. PHONE NUMBER<input class="o_customer_input" data-field="phone" placeholder="Phone number" value="${this.state.customer.phone || ""}"/></label>
                        <label class="o_field_group">9. EMAIL<input class="o_customer_input" data-field="email" placeholder="Email" value="${this.state.customer.email || ""}"/></label>
                    </div>
                    <div class="o_form_step o_form_step_full">
                        <label>10. ADDITIONAL SERVICES</label>
                        <div class="o_addons">${addons}</div>
                    </div>
                    <div class="o_cancellation_note">* No cancellation for paid booking within 24 hrs of event time.</div>
                    <div class="o_cricket_booking_summary">
                    ${pricingSummaryHtml(this.state)}
                    ${this.state.quote?.error ? `<div class="o_booking_error">${this.state.quote.error}</div>` : ""}
                    <button type="button" class="o_checkout_button" ${this._canCheckout() ? "" : "disabled"}>
                        ${this.state.bookingType === "box_cricket" ? "BOOK BOX CRICKET" : "BOOK A LANE"} ${total} ${this.state.currency}
                    </button>
                    </div>
                </main>
            </div>
        `;
        this.el.innerHTML = bookingBody;
    },

    _heroHtml(typeCards) {
        return `
            <header class="o_booking_intro">
                <h1>Book Your Lane</h1>
                <p>Secure your practice spot effortlessly. Choose your location, lane type, and time slot in just a few clicks.</p>
            </header>
            <section class="o_booking_hero">
                <div class="o_hero_collage" aria-hidden="true">
                    <span class="o_collage_tile o_tile_one"></span>
                    <span class="o_collage_tile o_tile_two"></span>
                    <span class="o_collage_tile o_tile_three"></span>
                    <span class="o_collage_tile o_tile_four"></span>
                    <span class="o_collage_flash"></span>
                </div>
                <div class="o_booking_type_stack">${typeCards}</div>
            </section>
        `;
    },

    _typeTitle(type) {
        if (type.code === "event") {
            return "BOX CRICKET for Events";
        }
        return String(type.name || "").toUpperCase();
    },

    _typeDescription(type) {
        if (type.code === "box_cricket") {
            return "Experience the thrill of box cricket with our combined 80 Feet lanes.";
        }
        if (type.code === "event") {
            return "Host corporate events, birthdays, and celebrations. Request a custom quote.";
        }
        return "Individual cricket lane booking for personal practice and coaching sessions.";
    },

    _selectedLaneLabel() {
        if (this.state.bookingType === "box_cricket") {
            return "BOX CRICKET";
        }
        const selected = (this.lanes || []).find((lane) => this.state.laneIds.includes(lane.id));
        return selected ? selected.name.replace(" ", "").toUpperCase() : "LANE";
    },

    _selectedSlotLabel() {
        const selected = (this.slots || []).filter((slot) => (this.state.slotStarts || []).includes(slot.slot_start));
        if (!selected.length) {
            return "Select a time";
        }
        return selected.map((slot) => slot.label).join(", ");
    },

    _eventHtml(hero, locations, addons) {
        return `
            <div class="o_cricket_booking_experience">
                ${hero}
                <main class="o_cricket_booking_main">
                    <div class="o_form_step o_form_step_full">
                        <label>1. LOCATION</label>
                        <select class="o_location_select">${locations}</select>
                    </div>
                    <div class="o_customer_grid">
                        <label class="o_field_group">2. FIRST NAME<input class="o_customer_input" data-field="first_name" placeholder="First name" value="${this.state.customer.first_name || ""}"/></label>
                        <label class="o_field_group">3. LAST NAME<input class="o_customer_input" data-field="last_name" placeholder="Last name" value="${this.state.customer.last_name || ""}"/></label>
                        <label class="o_field_group">4. PHONE NUMBER<input class="o_customer_input" data-field="phone" placeholder="Phone number" value="${this.state.customer.phone || ""}"/></label>
                        <label class="o_field_group">5. EMAIL<input class="o_customer_input" data-field="email" placeholder="Email" value="${this.state.customer.email || ""}"/></label>
                    </div>
                    <div class="o_customer_grid">
                        <label class="o_field_group">6. EVENT TYPE<input class="o_event_input" data-field="event_type" placeholder="Birthday, corporate, team party" value="${this.state.event?.event_type || ""}"/></label>
                        <label class="o_field_group">7. PREFERRED DATE<input class="o_event_input" data-field="preferred_date" type="date" value="${this.state.event?.preferred_date || this.state.date}"/></label>
                        <label class="o_field_group">8. PREFERRED TIME<input class="o_event_input" data-field="preferred_time" type="time" value="${this.state.event?.preferred_time || "18:00"}"/></label>
                        <label class="o_field_group">9. NUMBER OF PEOPLE<input class="o_event_input" data-field="people_count" type="number" min="1" placeholder="People" value="${this.state.event?.people_count || this.state.peopleCount}"/></label>
                    </div>
                    <div class="o_form_step o_form_step_full">
                        <label>10. ADDITIONAL SERVICES</label>
                        <div class="o_addons">${addons}</div>
                    </div>
                    <textarea class="o_event_input o_event_notes" data-field="notes" placeholder="Notes">${this.state.event?.notes || ""}</textarea>
                    <button type="button" class="o_event_submit">
                        Submit Request
                    </button>
                    ${this.state.eventMessage ? `<div class="o_event_message">${this.state.eventMessage}</div>` : ""}
                </main>
            </div>
        `;
    },

    _canCheckout() {
        const customer = this.state.customer;
        return this.state.quote?.available && customer.first_name && customer.last_name && customer.phone && customer.email;
    },

    async _onBookingType(ev) {
        this.state.bookingType = ev.currentTarget.dataset.code;
        this.state.laneIds = [];
        this.state.slotStart = false;
        this.state.slotStarts = [];
        await this._loadLanes();
        this._render();
    },

    async _onLocation(ev) {
        this.state.locationId = Number(ev.currentTarget.value);
        this.state.location = this.config.locations.find((location) => location.id === this.state.locationId);
        this.state.currency = this.state.location?.currency || "";
        this.state.laneIds = [];
        this.state.slotStarts = [];
        await this._loadLanes();
        this._render();
    },

    async _onLane(ev) {
        if (this.state.bookingType === "box_cricket" && this.boxCricket) {
            this.state.laneIds = [this.boxCricket.id];
        } else {
            this.state.laneIds = [Number(ev.currentTarget.dataset.laneId)];
        }
        this.state.slotStart = false;
        this.state.slotStarts = [];
        this._track("lane_selected");
        await this._loadSlots();
        this._render();
    },

    async _onDate(ev) {
        this.state.date = ev.currentTarget.dataset.date;
        this.state.slotStart = false;
        this.state.slotStarts = [];
        await this._loadSlots();
        this._render();
    },

    async _onNativeDate(ev) {
        this.state.date = ev.currentTarget.value;
        this.state.slotStart = false;
        this.state.slotStarts = [];
        await this._loadSlots();
        this._render();
    },

    async _onSlot(ev) {
        this._toggleSlot(ev.currentTarget.dataset.slot);
        this._track("slot_selected");
        await this._quote();
        this._render();
    },

    _toggleSlot(value) {
        const availableSlots = (this.slots || []).filter((slot) => slot.available);
        const order = availableSlots.map((slot) => slot.slot_start);
        const selected = new Set(this.state.slotStarts || []);
        if (selected.has(value) && selected.size > 1) {
            selected.delete(value);
        } else if (selected.has(value)) {
            selected.clear();
        } else {
            selected.add(value);
        }
        const selectedIndexes = [...selected].map((slotValue) => order.indexOf(slotValue)).filter((index) => index >= 0);
        if (!selectedIndexes.length) {
            this.state.slotStarts = [];
            this.state.slotStart = false;
            return;
        }
        const min = Math.min(...selectedIndexes);
        const max = Math.max(...selectedIndexes);
        this.state.slotStarts = order.slice(min, max + 1);
        this.state.slotStart = this.state.slotStarts[0] || false;
    },

    async _onPeopleMinus() {
        this.state.peopleCount = Math.max(1, this.state.peopleCount - 1);
        await this._loadSlots();
        this._render();
    },

    async _onPeoplePlus() {
        this.state.peopleCount += 1;
        await this._loadSlots();
        this._render();
    },

    async _onAddon(ev) {
        const id = Number(ev.currentTarget.value);
        if (ev.currentTarget.checked) {
            this.state.addonIds.push(id);
        } else {
            this.state.addonIds = this.state.addonIds.filter((addonId) => addonId !== id);
        }
        await this._quote();
        this._render();
    },

    _onCustomerInput(ev) {
        this.state.customer[ev.currentTarget.dataset.field] = ev.currentTarget.value;
    },

    _onEventInput(ev) {
        this.state.event = this.state.event || {};
        this.state.event[ev.currentTarget.dataset.field] = ev.currentTarget.value;
    },

    async _onCheckout() {
        try {
            const hold = await this._post("/cricket/api/hold", this._payload());
            const checkout = await this._post("/cricket/api/checkout", { hold_id: hold.hold_id });
            window.location.href = checkout.redirect_url;
        } catch (error) {
            this.state.quote = { available: false, error: error.message };
            this._render();
        }
    },

    async _onEventSubmit() {
        try {
            const event = this.state.event || {};
            const customer = this.state.customer;
            const response = await this._post("/cricket/api/event-request", {
                first_name: customer.first_name,
                last_name: customer.last_name,
                phone: customer.phone,
                email: customer.email,
                location_id: this.state.locationId,
                event_type: event.event_type,
                preferred_date: event.preferred_date || this.state.date,
                preferred_time: event.preferred_time || "18:00",
                people_count: event.people_count || this.state.peopleCount,
                addon_ids: this.state.addonIds,
                notes: event.notes,
            });
            this.state.eventMessage = response.message;
        } catch (error) {
            this.state.eventMessage = error.message;
        }
        this._render();
    },

    _track(eventType) {
        this._post("/cricket/api/traffic", {
            event_type: eventType,
            location_id: this.state.locationId,
            booking_type: this.state.bookingType,
            lane_id: this.state.laneIds[0],
            slot_start: this.state.slotStart,
            page_url: window.location.pathname,
        }).catch(() => {});
    },
});
