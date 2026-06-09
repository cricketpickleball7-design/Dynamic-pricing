/** @odoo-module **/

function localDateValue(date) {
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${date.getFullYear()}-${month}-${day}`;
}

function displayDateValue(value) {
    const [year, month, day] = String(value || "").split("-");
    return year && month && day ? `${day}/${month}/${year}` : value;
}

export function datePickerHtml(state) {
    const selectedDate = new Date(`${state.date}T12:00:00`);
    const year = selectedDate.getFullYear();
    const month = selectedDate.getMonth();
    const monthStart = new Date(year, month, 1);
    const firstDay = monthStart.getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const cells = [];
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const maxDate = new Date(today);
    maxDate.setDate(maxDate.getDate() + Number(state.location?.max_booking_days_ahead || 30));
    const minValue = localDateValue(today);
    const maxValue = localDateValue(maxDate);
    for (let index = 0; index < 42; index += 1) {
        const day = index - firstDay + 1;
        if (day < 1 || day > daysInMonth) {
            cells.push(`<span class="o_calendar_day is-muted"></span>`);
            continue;
        }
        const date = new Date(year, month, day);
        const value = localDateValue(date);
        const unavailable = date < today || date > maxDate;
        cells.push(`
            <button type="button" class="o_cricket_date ${state.date === value ? "is-selected" : ""} ${unavailable ? "is-unavailable" : ""}" data-date="${value}" ${unavailable ? "disabled" : ""}>
                ${day}
            </button>
        `);
    }
    const weekdays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        .map((day) => `<span>${day}</span>`)
        .join("");
    return `
        <div class="o_calendar_card">
            <label class="o_calendar_input">
                <span>${displayDateValue(state.date)}</span>
                <span class="o_calendar_icon" aria-hidden="true"></span>
                <input class="o_cricket_date_input" type="date" value="${state.date}" min="${minValue}" max="${maxValue}"/>
            </label>
            <div class="o_calendar_month">
                <strong>${selectedDate.toLocaleDateString(undefined, { month: "long" })}</strong>
                <span>${year}</span>
            </div>
            <div class="o_calendar_weekdays">${weekdays}</div>
            <div class="o_cricket_dates">${cells.join("")}</div>
            <div class="o_calendar_legend">
                <span><i class="is-selected"></i>Selected</span>
                <span><i></i>Available</span>
                <span><i class="is-unavailable"></i>Unavailable</span>
            </div>
        </div>
    `;
}
