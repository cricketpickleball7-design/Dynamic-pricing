{
    "name": "Cricket Lane Event CRM",
    "summary": "Box cricket event inquiry form and CRM lead creation",
    "version": "19.0.1.0.0",
    "category": "CRM",
    "author": "cricketpickleball7-design",
    "license": "LGPL-3",
    "depends": [
        "cricket_lane_booking",
        "crm",
        "website",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/crm_lead_views.xml",
        "views/event_request_templates.xml",
    ],
    "installable": True,
    "application": False,
}
