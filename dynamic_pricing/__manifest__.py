{
    "name": "Dynamic Pricing",
    "summary": "Day and night product pricing with a PDP countdown timer",
    "version": "19.0.1.0.0",
    "category": "Website/eCommerce",
    "author": "cricketpickleball7-design",
    "license": "LGPL-3",
    "depends": ["website_sale"],
    "data": [
        "views/product_template_views.xml",
        "views/website_sale_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "dynamic_pricing/static/src/js/dynamic_pricing_timer.js",
            "dynamic_pricing/static/src/scss/dynamic_pricing.scss",
        ],
    },
    "installable": True,
    "application": False,
}

