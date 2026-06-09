/** @odoo-module **/

export function pricingSummaryHtml(state) {
    const quote = state.quote || {};
    const breakdown = quote.breakdown || {};
    const addons = breakdown.addons || [];
    const slotCount = breakdown.slot_count || state.slotStarts?.length || 1;
    const addonRows = addons.map((addon) => `
        <div class="o_price_row"><span>${addon.name}</span><strong>${state.currency} ${Number(addon.price || 0).toFixed(2)}</strong></div>
    `).join("");
    const total = Number(quote.price_total || breakdown.final_price || 0).toFixed(2);
    return `
        <div class="o_cricket_price_summary">
            <div class="o_price_row"><span>Slots</span><strong>${slotCount}</strong></div>
            <div class="o_price_row"><span>Base</span><strong>${state.currency} ${Number(breakdown.base_price || 0).toFixed(2)}</strong></div>
            <div class="o_price_row"><span>People</span><strong>${state.currency} ${Number(breakdown.people_fee || 0).toFixed(2)}</strong></div>
            ${addonRows}
            <div class="o_price_total"><span>Total</span><strong>${state.currency} ${total}</strong></div>
        </div>
    `;
}
