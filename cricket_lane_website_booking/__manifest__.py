{
    "name": "Cricket Lane Website Booking",
    "summary": "Website booking flow for cricket lanes and box cricket",
    "version": "19.0.1.0.0",
    "category": "Website",
    "author": "cricketpickleball7-design",
    "license": "LGPL-3",
    "depends": [
        "cricket_lane_booking",
        "cricket_lane_dynamic_pricing",
        "website",
        "website_sale",
        "payment",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/website_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "cricket_lane_website_booking/static/src/js/cricket_lane_map.js",
            "cricket_lane_website_booking/static/src/js/cricket_date_picker.js",
            "cricket_lane_website_booking/static/src/js/cricket_pricing_summary.js",
            "cricket_lane_website_booking/static/src/js/cricket_booking_widget.js",
            "cricket_lane_website_booking/static/src/scss/cricket_booking.scss",
        ],
    },
    "installable": True,
    "application": False,
}
