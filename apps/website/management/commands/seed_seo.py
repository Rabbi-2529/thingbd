"""Fill SEO titles, descriptions and keywords for Thingbd's pages.

    python manage.py seed_seo --dry-run      # show what would change
    python manage.py seed_seo                # fill only EMPTY SEO fields
    python manage.py seed_seo --overwrite    # replace existing SEO text too

Share images (meta_image / og_image) are never changed. Items are matched by slug;
anything not listed here is left alone.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.blog.models import Post
from apps.core.models import SiteSettings
from apps.website.models import HomePage, Page, Project, Service

BRAND_KEYWORDS = "software company in Bangladesh, software development company in Bangladesh, IT company in Dhaka"

SITE = {
    "meta_title": "Thingbd – Software Development Company in Bangladesh",
    "meta_description": "Thingbd is a Dhaka software company building websites, custom software, ERP, HRM, POS "
                        "and automation for businesses in Bangladesh and worldwide.",
    "meta_keywords": f"{BRAND_KEYWORDS}, custom software development, web development Bangladesh, "
                     "ERP software Bangladesh, business automation",
}

HOME = {
    "meta_title": "Thingbd – Software & Web Development Company in Dhaka",
    "meta_description": "Web platforms, custom software, ERP, HRM, POS and smart automation for B2B and B2C teams. "
                        "Thingbd designs, builds and supports software in Dhaka.",
    "meta_keywords": f"{BRAND_KEYWORDS}, best software company in Bangladesh, web development company, "
                     "custom software, ERP and HRM software",
}

SERVICES = {
    "web-development": {
        "meta_title": "Web Development Company in Bangladesh | Thingbd",
        "meta_description": "Fast, SEO-friendly websites and web applications built with Django, Laravel and React. "
                            "Thingbd designs, develops and maintains sites that convert.",
        "meta_keywords": "web development Bangladesh, website design Dhaka, web application development, "
                         "Django development, Laravel development, responsive website",
    },
    "custom-software": {
        "meta_title": "Custom Software Development in Bangladesh | Thingbd",
        "meta_description": "Purpose-built software for your exact workflows: ERP, HRM, POS, recruitment and telecom "
                            "platforms, designed, built and supported by Thingbd in Dhaka.",
        "meta_keywords": "custom software development, software development Bangladesh, bespoke software, "
                         "enterprise software, software company Dhaka",
    },
    "bot-automation": {
        "meta_title": "Bot & Business Process Automation | Thingbd",
        "meta_description": "Chatbots, scrapers and workflow automation that handle repetitive work 24/7, connecting "
                            "your tools, APIs and data so your team can focus on growth.",
        "meta_keywords": "business automation, chatbot development, workflow automation, RPA Bangladesh, "
                         "API integration, bot development",
    },
    "online-presence": {
        "meta_title": "Online Presence & Brand Building | Thingbd",
        "meta_description": "Brand identity, websites, content and social presence that make your business "
                            "recognizable and trusted online, planned and delivered by one team.",
        "meta_keywords": "online presence, brand building Bangladesh, digital branding, brand identity design, "
                         "social media presence, business website",
    },
    "seo-growth": {
        "meta_title": "SEO Services in Bangladesh – Technical SEO | Thingbd",
        "meta_description": "Technical SEO, on-page optimisation and content strategy that grow organic traffic "
                            "and turn search visitors into qualified leads for your business.",
        "meta_keywords": "SEO services Bangladesh, SEO company Dhaka, technical SEO, on-page SEO, "
                         "content marketing, Google ranking",
    },
    "business-software": {
        "meta_title": "Business Software, Dashboards & CRM | Thingbd",
        "meta_description": "Dashboards, CRMs, inventory and internal tools that replace spreadsheets and make "
                            "daily operations faster, clearer and easier to manage.",
        "meta_keywords": "business software Bangladesh, CRM software, inventory management software, "
                         "business dashboard, internal tools",
    },
}

PROJECTS = {
    "erp": {
        "meta_title": "ERP Software for Business Management | Thingbd",
        "meta_description": "Custom ERP software built with Laravel and MySQL to manage inventory, sales, accounts "
                            "and daily operations in one place. A Thingbd case study.",
        "meta_keywords": "ERP software Bangladesh, ERP system, business management software, Laravel ERP, "
                         "inventory management, accounting software",
    },
    "flexiload-recharge-platform": {
        "meta_title": "Flexiload & Mobile Recharge Platform | Thingbd",
        "meta_description": "Mobile recharge platform with Grameenphone, Banglalink, Robi and Airtel integration, "
                            "webhook processing and real-time transaction tracking.",
        "meta_keywords": "flexiload software, mobile recharge software, recharge API Bangladesh, "
                         "telecom API integration, webhook processing, Django FastAPI",
    },
    "employee-recruitment": {
        "meta_title": "Employee Recruitment & Interview Software | Thingbd",
        "meta_description": "Django recruitment system with candidate registration, interview scheduling, "
                            "evaluator scoring, role-based access and bulk SMS notifications.",
        "meta_keywords": "recruitment software, interview management system, applicant tracking system, "
                         "HR recruitment Bangladesh, Django recruitment",
    },
    "nomadly": {
        "meta_title": "Nomadly – eSIM B2B & B2C Marketplace | Thingbd",
        "meta_description": "Nomadly is an eSIM marketplace for travellers and resellers, offering data plans "
                            "worldwide with B2B and B2C ordering. Built by Thingbd.",
        "meta_keywords": "eSIM platform, eSIM marketplace, travel eSIM, B2B eSIM, eSIM reseller platform",
    },
    "pos-restaurant-software": {
        "meta_title": "POS & Restaurant Management Software | Thingbd",
        "meta_description": "Laravel POS for restaurants with order, menu and branch management, billing, "
                            "invoices and sales reports that simplify daily cashier work.",
        "meta_keywords": "POS software Bangladesh, restaurant management software, restaurant POS, "
                         "billing software, multi-branch POS, Laravel POS",
    },
    "hrm-software-with-attendance-device-integration": {
        "meta_title": "HRM Software with Biometric Attendance | Thingbd",
        "meta_description": "HRM software integrated with biometric attendance devices to automate attendance, "
                            "working hours, overtime, leave and HR reports.",
        "meta_keywords": "HRM software Bangladesh, HR management software, biometric attendance software, "
                         "attendance device integration, leave management",
    },
    "cctv-employee-tracking": {
        "meta_title": "AI CCTV Employee Tracking System | Thingbd",
        "meta_description": "AI-powered CCTV system that uses face recognition to track employee movement across "
                            "office cameras, with a central dashboard and history.",
        "meta_keywords": "CCTV employee tracking, face recognition system, AI CCTV monitoring, "
                         "computer vision, employee monitoring system",
    },
}

PAGES = {
    "privacy-policy": {
        "meta_title": "Privacy Policy | Thingbd",
        "meta_description": "How Thingbd collects, uses and protects the personal information you share through "
                            "our website, contact forms and services.",
        "meta_keywords": "Thingbd privacy policy, data protection, personal information",
    },
    "terms": {
        "meta_title": "Terms of Service | Thingbd",
        "meta_description": "The terms and conditions for using the Thingbd website and engaging our software "
                            "development, design and digital services.",
        "meta_keywords": "Thingbd terms of service, terms and conditions, software services agreement",
    },
}

POSTS = {
    "welcome": {
        "meta_title": "Thingbd Blog – Software, Automation & Growth Insights",
        "meta_description": "Practical articles on software development, business automation, SEO and digital "
                            "growth for businesses in Bangladesh, from the Thingbd team.",
        "meta_keywords": "software development blog, business automation tips, SEO tips Bangladesh, "
                         "technology insights, Thingbd blog",
    },
}

SEO_FIELDS = ("meta_title", "meta_description", "meta_keywords")


class Command(BaseCommand):
    help = "Fill SEO titles, descriptions and keywords for Thingbd's pages (images are never changed)."

    def add_arguments(self, parser):
        parser.add_argument("--overwrite", action="store_true", help="Replace SEO text that is already filled in.")
        parser.add_argument("--dry-run", action="store_true", help="Show the changes without saving them.")

    def handle(self, *args, overwrite=False, dry_run=False, **options):
        self.overwrite, self.dry_run = overwrite, dry_run
        self.changed = self.skipped = 0
        with transaction.atomic():
            self.apply("Site settings (defaults)", SiteSettings.load(), SITE)
            self.apply("Home page", HomePage.load(), HOME)
            for model, data, label in ((Service, SERVICES, "Service"), (Project, PROJECTS, "Project"),
                                       (Page, PAGES, "Page"), (Post, POSTS, "Post")):
                found = {obj.slug: obj for obj in model.objects.filter(slug__in=data)}
                for slug, values in data.items():
                    if slug in found:
                        self.apply(f"{label}: {found[slug]}", found[slug], values)
                    else:
                        self.stdout.write(self.style.WARNING(f"- {label} '{slug}' not found, skipped"))
            if dry_run:
                transaction.set_rollback(True)

        mode = "DRY RUN — nothing saved. " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"\n{mode}{self.changed} field(s) {'would be ' if dry_run else ''}updated, "
            f"{self.skipped} kept (already filled in; use --overwrite to replace)."
        ))

    def apply(self, label, obj, values):
        updates = {}
        for field in SEO_FIELDS:
            new = values.get(field, "")
            if not new:
                continue
            max_length = obj._meta.get_field(field).max_length
            if len(new) > max_length:
                raise ValueError(f"{label}: {field} is {len(new)} chars, limit {max_length}")
            current = getattr(obj, field) or ""
            if current == new:
                continue
            if current and not self.overwrite:
                self.skipped += 1
                continue
            updates[field] = new
        if not updates:
            return
        self.stdout.write(self.style.MIGRATE_HEADING(f"\n{label}"))
        for field, new in updates.items():
            old = getattr(obj, field) or "(empty)"
            self.stdout.write(f"  {field}:\n    - {old}\n    + {new}")
            setattr(obj, field, new)
        obj.save(update_fields=list(updates))
        self.changed += len(updates)
