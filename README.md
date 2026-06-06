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

