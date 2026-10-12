"""Sidebar menu for the custom dashboard.

Items with `url_name=None` are planned for a later phase and are shown disabled.
"""

from django.urls import reverse

NAVIGATION = [
    {
        "title": "Overview",
        "items": [
            {"key": "dashboard", "label": "Dashboard", "icon": "space_dashboard", "url_name": "dashboard:index"},
        ],
    },
    {
        "title": "Home page",
        "items": [
            {"key": "home", "label": "Home page content", "icon": "home", "url_name": "dashboard:home_page"},
            {"key": "stats", "label": "Hero stats", "icon": "monitoring", "url_name": "dashboard:stats_list"},
            {"key": "marquee", "label": "Marquee", "icon": "text_rotation_none", "url_name": "dashboard:marquee_list"},
            {"key": "process", "label": "Process steps", "icon": "timeline", "url_name": "dashboard:process_list"},
        ],
    },
    {
        "title": "Content",
        "items": [
            {"key": "services", "label": "Services", "icon": "design_services", "url_name": "dashboard:services_list"},
            {"key": "projects", "label": "Portfolio", "icon": "work", "url_name": "dashboard:projects_list"},
            {"key": "testimonials", "label": "Testimonials", "icon": "reviews", "url_name": "dashboard:testimonials_list"},
            {"key": "faqs", "label": "FAQs", "icon": "quiz", "url_name": "dashboard:faqs_list"},
            {"key": "team", "label": "Team", "icon": "groups", "url_name": "dashboard:team_list"},
            {"key": "pages", "label": "Pages", "icon": "description", "url_name": "dashboard:pages_list"},
        ],
    },
    {
        "title": "Blog",
        "items": [
            {"key": "posts", "label": "Posts", "icon": "article", "url_name": "dashboard:posts_list"},
            {"key": "categories", "label": "Categories", "icon": "label", "url_name": "dashboard:categories_list"},
        ],
    },
    {
        "title": "Sales",
        "items": [
            {"key": "leads", "label": "Leads", "icon": "inbox", "url_name": "dashboard:leads_list", "badge": "new_leads"},
        ],
    },
    {
        "title": "Settings",
        "items": [
            {"key": "site_settings", "label": "Site settings", "icon": "tune", "url_name": "dashboard:site_settings"},
            {"key": "profile", "label": "My profile", "icon": "person", "url_name": "dashboard:profile"},
            {"key": "password", "label": "Change password", "icon": "lock", "url_name": "dashboard:password_change"},
        ],
    },
]


def _badge_counts():
    from apps.leads.models import Lead

    return {"new_leads": Lead.objects.filter(status=Lead.Status.NEW).count()}


def build_navigation(active_key):
    badges = _badge_counts()
    groups = []
    for group in NAVIGATION:
        items = []
        for item in group["items"]:
            items.append({
                **item,
                "url": reverse(item["url_name"]) if item["url_name"] else None,
                "active": item["key"] == active_key,
                "badge_count": badges.get(item.get("badge"), 0),
            })
        groups.append({"title": group["title"], "items": items})
    return groups
