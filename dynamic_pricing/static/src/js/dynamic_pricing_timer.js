/** @odoo-module **/

function formatRemaining(milliseconds) {
    const totalSeconds = Math.max(0, Math.floor(milliseconds / 1000));
    const hours = String(Math.floor(totalSeconds / 3600)).padStart(2, "0");
    const minutes = String(Math.floor((totalSeconds % 3600) / 60)).padStart(2, "0");
    const seconds = String(totalSeconds % 60).padStart(2, "0");
    return `${hours}:${minutes}:${seconds}`;
}

function bindDynamicPricingTimer(timer) {
    if (timer.dataset.dynamicPricingBound) {
        return;
    }
    timer.dataset.dynamicPricingBound = "1";

    const countdown = timer.querySelector(".o_dynamic_pricing_timer_countdown");
    const nextChange = Number(timer.dataset.nextChangeMs);
    if (!countdown || !nextChange) {
        return;
    }

    const refreshTimer = () => {
        const remaining = nextChange - Date.now();
        countdown.textContent = formatRemaining(remaining);
        if (remaining <= 0) {
            window.setTimeout(() => window.location.reload(), 500);
            return;
        }
        window.setTimeout(refreshTimer, 1000);
    };

    refreshTimer();
}

function bindDynamicPricingTimers(root = document) {
    root
        .querySelectorAll(".o_dynamic_pricing_timer[data-next-change-ms]")
        .forEach(bindDynamicPricingTimer);
}

function startDynamicPricingTimers() {
    bindDynamicPricingTimers();
    if (document.body) {
        new MutationObserver(() => bindDynamicPricingTimers()).observe(document.body, {
            childList: true,
            subtree: true,
        });
    }
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startDynamicPricingTimers);
} else {
    startDynamicPricingTimers();
}
