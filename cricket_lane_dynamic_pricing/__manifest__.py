{
    "name": "Cricket Lane Dynamic Pricing",
    "summary": "Dynamic cricket lane pricing from time, occupancy, traffic, competitors, people, and add-ons",
    "version": "19.0.1.0.0",
    "category": "Appointments",
    "author": "cricketpickleball7-design",
    "license": "LGPL-3",
    "depends": [
        "cricket_lane_booking",
        "sale_management",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/default_pricing.xml",
        "data/cron.xml",
        "views/cricket_pricing_menu.xml",
        "views/cricket_price_rule_views.xml",
        "views/cricket_competitor_rate_views.xml",
        "views/cricket_traffic_metric_views.xml",
    ],
    "installable": True,
    "application": False,
}
