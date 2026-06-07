# Dynamic Pricing

Odoo addon for day/night product pricing on eCommerce product pages.

## What It Does

- Adds day and night prices to each product template.
- Lets each product define day start time, night start time, and timezone.
- Applies the active price through Odoo's pricelist engine.
- Shows a countdown timer on the product detail page for the next price change.

## Local Install

Add this repository root to `addons_path`, restart Odoo, update the Apps list, then install
the `Dynamic Pricing` module.

Example:

```ini
addons_path = C:\Odoo\odoo\addons,C:\Odoo\odoo\odoo\addons,C:\Odoo\Dynamic-pricing
```

## Odoo.sh

Connect this GitHub repository to an Odoo.sh project or add it as a custom addon repository.
Push changes to a development branch first, test, then merge to staging/production.

## Appointment Dynamic Pricing

The `appointment_dynamic_pricing` addon calculates real-time prices for appointment slots without
changing `product.template.list_price` or `product.product.lst_price`.

Plain JSON endpoint:

```text
POST /appointment_dynamic_pricing/get_price
Content-Type: application/json
```

Example payload:

```json
{
  "appointment_type_id": 5,
  "product_id": 20,
  "slot_datetime": "2026-06-07 19:00:00"
}
```

Optional confirmation payload keys:

```json
{
  "confirm": true,
  "sale_order_line_id": 42,
  "calendar_event_id": 99
}
```

When confirmation IDs are supplied, the module stores the calculated price on the order line and/or
calendar event and links them to the price calculation log.
