/** @odoo-module **/

export function laneMapHtml(state, lanes, boxCricket) {
    const selectedIds = new Set(state.laneIds || []);
    const isBox = state.bookingType === "box_cricket";
    const visibleLanes = isBox
        ? lanes.filter((lane) => lane.lane_type === "individual")
        : lanes;
    const cards = visibleLanes.map((lane) => {
        const selected = selectedIds.has(lane.id);
        const laneNumber = Number(String(lane.code || "").replace("L", ""));
        const inBoxBundle = [4, 5, 6].includes(laneNumber);
        const ghost = isBox && !inBoxBundle;
        const boxSelected = isBox && inBoxBundle && boxCricket && selectedIds.has(boxCricket.id);
        const dataLaneId = isBox && inBoxBundle && boxCricket ? boxCricket.id : lane.id;
        const disabled = isBox ? ghost || !boxCricket?.available : !lane.available;
        const classes = [
            "o_cricket_lane_strip",
            lane.available ? "is-available" : "is-unavailable",
            selected || boxSelected ? "is-selected" : "",
            ghost ? "is-ghosted" : "",
        ].join(" ");
        return `
            <button type="button" class="${classes}" data-lane-id="${dataLaneId}" ${disabled ? "disabled" : ""}>
                <span class="o_lane_heading">
                    <strong>${lane.name.replace(" ", "").toUpperCase()}</strong>
                    <em>${lane.length_ft} FT</em>
                </span>
                <span class="o_lane_pitch o_lane_pitch_top"></span>
                <span class="o_lane_marker"></span>
                <span class="o_lane_pitch o_lane_pitch_bottom"></span>
            </button>
        `;
    }).join("");
    const box = boxCricket && isBox ? `
        <button type="button" class="o_lane_bundle_summary ${selectedIds.has(boxCricket.id) ? "is-selected" : ""}" data-lane-id="${boxCricket.id}">
            <span class="o_square_check"></span>
            <strong>80 FT PRECISION LANES (X3)</strong>
            <span>from ${state.currency || ""} ${Number(boxCricket.base_price || 0).toFixed(2)}</span>
        </button>
    ` : "";
    const selectedLane = lanes.find((lane) => selectedIds.has(lane.id));
    const selectedCategory = selectedLane?.length_ft === 140
        ? "POWER"
        : selectedLane?.length_ft === 100
            ? "VERSATILITY"
            : "PRECISION";
    const summary = !isBox && selectedLane ? `
        <div class="o_lane_bundle_summary is-selected" data-lane-id="${selectedLane.id}">
            <span class="o_square_check"></span>
            <strong>${selectedLane.length_ft} FT ${selectedCategory} LANE</strong>
            <span>from ${state.currency || ""} ${Number(selectedLane.base_price || 0).toFixed(2)}</span>
        </div>
    ` : "";
    return `<div class="o_lane_map_panel"><div class="o_cricket_lane_map">${cards}</div>${box || summary}</div>`;
}
