{
    "name": "Appointment Dynamic Pricing",
    "summary": "Real-time dynamic pricing for appointment slots",
    "version": "19.0.1.0.0",
    "category": "Appointments",
    "author": "cricketpickleball7-design",
    "license": "LGPL-3",
    "depends": ["appointment", "calendar", "sale", "website"],
    "data": [
        "security/ir.model.access.csv",
        "views/appointment_dynamic_pricing_views.xml",
        "views/sale_order_line_views.xml",
        "views/calendar_event_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": False,
}
