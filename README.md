# Cricket Lane Booking for Odoo

Custom Odoo module suite for cricket lane, box cricket, and event inquiry booking.

## Confirmed Local Target

This repository was validated against the local Odoo tree at `C:\Odoo\odoo`.

- Odoo version: `19.0`
- Appointment model available locally: `appointment.type`
- Local environment has a lightweight appointment stub, not the full appointment resource model.
- Full Odoo Appointments databases may also expose `appointment.resource`; this suite keeps the resource link optional through `cricket.lane.appointment_resource_id`.
- Payment model confirmed: `payment.transaction`
- Sale/payment success hook confirmed through `sale.order.action_confirm()` after `payment.transaction._post_process()`.

No Odoo core code is modified.

## Modules

In Odoo, each folder with a `__manifest__.py` file is an addon/module. The cricket booking flow is split into smaller modules so each part has one clear job.

### Cricket Booking Suite

Install these modules in this order:

1. `cricket_lane_booking`
2. `cricket_lane_dynamic_pricing`
3. `cricket_lane_website_booking`
4. `cricket_lane_event_crm`

| Module | Why It Is Used | Beginner Notes |
| --- | --- | --- |
| `cricket_lane_booking` | Core backend for locations, lanes, booking types, slot rules, add-ons, temporary holds, sale orders, bookings, and calendar events. | This is the foundation. Install it first. It creates the cricket booking menu, the lane data, service products, and the sale order link used for payment. |
| `cricket_lane_dynamic_pricing` | Adds dynamic price calculation on top of the core booking module. | It extends `cricket.booking.hold._calculate_price()` so prices can change by time/day rules, occupancy, website traffic, competitor rates, people count, and add-ons. |
| `cricket_lane_website_booking` | Public website page and APIs for customers to book online. | It creates `/book-cricket-lane`, loads lanes/slots/prices with JavaScript, creates a hold, then sends the customer to Odoo checkout/payment. |
| `cricket_lane_event_crm` | Event inquiry flow for larger box cricket events. | This is for requests that should become CRM opportunities instead of instant online payment. Example: corporate event, birthday, private party. |

### Other Addons In This Repo

These are separate dynamic pricing examples and are not required for the cricket lane website booking flow.

| Module | Why It Is Used |
| --- | --- |
| `dynamic_pricing` | Adds day/night dynamic pricing to normal Odoo website shop products and shows a countdown timer on the product page. |
| `appointment_dynamic_pricing` | Adds dynamic pricing models for Odoo appointment slots. This is more general appointment pricing, separate from the cricket lane suite. |

## How To Use The Cricket Booking Modules

For a beginner developer, think of the flow in three layers:

1. Backend setup: use `cricket_lane_booking`.
   - Go to `Cricket Booking > Locations` and configure the cricket center.
   - Go to `Cricket Booking > Lanes` and configure Lane 1 to Lane 6 and Box Cricket.
   - Go to `Cricket Booking > Slot Rules` and configure open/close times.
   - Go to `Cricket Booking > Add-ons` and configure extra services like Bola Bowling Machine.

2. Pricing setup: use `cricket_lane_dynamic_pricing`.
   - Go to `Cricket Booking > Dynamic Pricing`.
   - Add price rules for peak hours, weekends, high occupancy, traffic, or competitor pricing.
   - If no special rule applies, the system uses the lane base price from the lane record.

3. Website booking: use `cricket_lane_website_booking`.
   - Open `/book-cricket-lane` on the website.
   - Customer selects location, lane/box cricket, date, time, people count, add-ons, and contact details.
   - Customer clicks `BOOK A LANE` or `BOOK BOX CRICKET`.

Payment must also be configured in standard Odoo. Go to the Odoo payment provider settings and enable at least one provider for website checkout.

## What Happens When Clicking Book A Lane

`Book a Lane` is treated as a service booking, not a stockable product. The service products are defined in `cricket_lane_booking/data/products.xml`, and the booking types are linked to those products in `cricket_lane_booking/data/default_data.xml`.

When the customer clicks `BOOK A LANE`:

1. The browser calls `POST /cricket/api/hold`.
2. Odoo creates a `cricket.booking.hold`.
   - This temporarily blocks the selected lane and time.
   - The hold expires after the location hold time, for example 10 minutes.
   - No confirmed booking exists yet.
3. The browser calls `POST /cricket/api/checkout`.
4. Odoo creates a `sale.order`.
   - The main order line uses the service product `Cricket Lane Booking`.
   - Add-ons use their own service products.
   - The calculated price is locked onto the sale order line.
   - The sale order is stored in the website session.
5. The website redirects the customer to `/shop/payment`.
6. The customer pays using Odoo Website Sale payment checkout.
7. After payment confirms the sale order, `sale.order.action_confirm()` converts the hold into a real `cricket.booking`.
8. The confirmed booking creates a calendar event, links back to the sale order, and sends the confirmation email.

If the customer does not pay before the hold expires, the slot is released and no confirmed booking is created.

## What Is Included

- Six individual lanes:
  - Lane 1: 140 FT
  - Lane 2: 140 FT
  - Lane 3: 100 FT
  - Lane 4: 80 FT
  - Lane 5: 80 FT
  - Lane 6: 80 FT
- Box Cricket bundle using Lane 4 + Lane 5 + Lane 6.
- 55-minute customer play time with 5-minute cleaning/setup gap.
- 60-minute internal blocking.
- Location opening hours, slot rules, minimum notice, and max booking window.
- Temporary checkout holds with expiry.
- Admin resource dashboard with lane status, today bookings, active holds, active blocks, and next booking.
- Admin slot blocks for maintenance, private events, training, and manual holds.
- Double-booking prevention across active holds and confirmed bookings.
- Double-booking prevention also checks admin slot blocks.
- Multi-slot selection for continuous adjacent slots.
- Sale order checkout with locked price.
- Booking confirmation only when the sale order is confirmed after payment.
- Dynamic pricing from lane, time/day rules, occupancy, traffic, competitor rates, people, and add-ons.
- Public website booking page at `/book-cricket-lane`.
- Event inquiry API that creates CRM opportunities.
- Event inquiries are available under `Cricket Booking > Event Inquiries`.

## Admin Checks

Use these backend menus:

- `Cricket Booking > Resource Dashboard`
- `Cricket Booking > Booking Calendar`
- `Cricket Booking > Slot Blocks`
- `Cricket Booking > Bookings`
- `Cricket Booking > Event Inquiries`

To manually close a lane or Box Cricket slot, create a `Slot Block` with the location, lanes, start/end time, and reason. The website slot API and checkout hold logic will treat it as unavailable.

## Main Website APIs

- `GET /cricket/api/config`
- `GET /cricket/api/lanes`
- `GET /cricket/api/slots`
- `POST /cricket/api/quote`
- `POST /cricket/api/hold`
- `POST /cricket/api/checkout`
- `POST /cricket/api/traffic`
- `POST /cricket/api/event-request`

## Validation

The modules were installed and updated locally with:

```powershell
C:\Odoo\venv312\Scripts\python.exe C:\Odoo\odoo\odoo-bin -c C:\Odoo\odoo.conf -d odoo_local -u cricket_lane_booking,cricket_lane_dynamic_pricing,cricket_lane_website_booking,cricket_lane_event_crm --stop-after-init --log-level=warn
```

Server-side tests passed for:

```powershell
C:\Odoo\venv312\Scripts\python.exe C:\Odoo\odoo\odoo-bin -c C:\Odoo\odoo.conf -d odoo_local -u cricket_lane_booking,cricket_lane_dynamic_pricing,cricket_lane_event_crm --test-enable --test-tags /cricket_lane_booking,/cricket_lane_dynamic_pricing,/cricket_lane_event_crm --stop-after-init --log-level=warn
```

The website `HttpCase` smoke test was added, but the local Windows test run timed out while starting the HTTP test server. The website module itself installs successfully.
