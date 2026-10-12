from django.core.management.base import BaseCommand
from django.db import transaction

from apps.blog.models import Category, Post
from apps.core.models import SiteSettings
from apps.website.models import FAQ, HomePage, MarqueeItem, Page, ProcessStep, Project, Service, Stat, Testimonial

SERVICES = [
    ("Web Development", "web-development", "Fast marketing sites and reliable web applications designed to convert."),
    ("Custom Software", "custom-software", "Purpose-built products matched to your exact workflows and operations."),
    ("Bot Automation", "bot-automation", "Smart agents and workflow automation that handle repetitive work around the clock."),
    ("Online Presence", "online-presence", "Strategy, identity, content, and digital experiences that make brands recognizable."),
    ("SEO & Growth", "seo-growth", "Technical SEO and content systems that turn attention into qualified pipeline."),
    ("Business Software", "business-software", "Dashboards, CRMs, and internal tools that make daily operations easier."),
]

STEPS = [
    ("Discover", "We clarify the problem, audience, goals, and constraints."),
    ("Design", "We map the experience and validate the direction early."),
    ("Build", "We develop in focused iterations with visible progress."),
    ("Launch", "We test, deploy, measure, and keep improving."),
]

FAQS = [
    ("How long does a typical project take?", "A marketing website usually takes 2–4 weeks. Custom software and automation projects are planned in milestones, typically 6–12 weeks for a first release."),
    ("Do you work with startups and established businesses?", "Yes. We work with B2C and B2B teams, from founders shipping an MVP to operations teams replacing spreadsheets with proper software."),
    ("What happens after launch?", "We offer support and maintenance plans covering hosting, updates, monitoring and continuous improvements."),
    ("Can I update the website content myself?", "Yes. Every site we build comes with an easy admin panel so your team can edit text, images, projects and blog posts without a developer."),
]


class Command(BaseCommand):
    help = "Fill the database with Thingbd's starter content. Safe to run repeatedly: existing rows are left alone."

    @transaction.atomic
    def handle(self, *args, **options):
        site = SiteSettings.load()
        if not site.meta_description:
            site.meta_title = "Thingbd | Your Vision, Our Code"
            site.meta_description = "Thingbd builds websites, custom software, automation, and digital brands for ambitious B2B and B2C teams."
            site.contact_text = "Tell us what you are building. We will reply with useful next steps within one business day."
            site.email = site.email or "hello@thingbd.com"
            site.address = site.address or "Dhaka, Bangladesh"
            site.footer_text = "A software studio building web platforms, custom software, automation and digital brands."
            site.save()

        home = HomePage.load()
        if not home.hero_text:
            home.hero_text = "We craft web platforms, custom software, intelligent automation, and digital brands for ambitious B2B and B2C teams."
            home.services_text = "Everything a modern business needs to launch, operate, and grow, delivered by one focused team."
            home.process_text = "Clear milestones, direct communication, and useful software shipped without ceremony."
            home.work_text = "Products that combine thoughtful design with maintainable engineering."
            home.save()

        def seed(model, rows):
            if model.objects.exists():
                return 0
            model.objects.bulk_create([model(order=i, **row) for i, row in enumerate(rows)])
            return len(rows)

        created = {
            "stats": seed(Stat, [{"value": v, "label": l} for v, l in (("50+", "Products shipped"), ("12", "Industries served"), ("100%", "Built in-house"))]),
            "marquee": seed(MarqueeItem, [{"text": t} for t in ("Web development", "Custom software", "Automation", "SEO", "Brand systems", "Internal tools")]),
            "services": seed(Service, [{"title": t, "slug": s, "short_description": d} for t, s, d in SERVICES]),
            "steps": seed(ProcessStep, [{"title": t, "description": d} for t, d in STEPS]),
            "projects": seed(Project, [
                {"title": "Operations Platform", "slug": "operations-platform", "category": "Custom software · Analytics · Automation",
                 "cover_text": "SaaS dashboard", "summary": "A unified dashboard that replaced five spreadsheets and cut weekly reporting from days to minutes.",
                 "tech_stack": "Django, PostgreSQL, Celery"},
                {"title": "Customer App", "slug": "customer-app", "category": "Product design · Web application · Growth",
                 "cover_text": "Mobile experience", "summary": "A mobile-first customer experience that made ordering and support self-service.",
                 "tech_stack": "React, Django REST Framework"},
            ]),
            "testimonials": seed(Testimonial, [
                {"name": "Client name", "role": "Founder", "company": "Your company", "quote": "Thingbd understood our business quickly and shipped exactly what we needed. Replace this with a real testimonial from the admin panel."},
            ]),
            "faqs": seed(FAQ, [{"question": q, "answer": a} for q, a in FAQS]),
        }

        if not Page.objects.exists():
            Page.objects.create(title="Privacy Policy", slug="privacy-policy", order=1,
                                body="<p>Explain how you collect and use visitor data. Edit this page in the admin panel.</p>")
            Page.objects.create(title="Terms of Service", slug="terms", order=2,
                                body="<p>Your terms of service. Edit this page in the admin panel.</p>")
            created["pages"] = 2

        if not Post.objects.exists():
            category, _ = Category.objects.get_or_create(slug="insights", defaults={"name": "Insights"})
            Post.objects.create(
                title="Welcome to the Thingbd blog", slug="welcome", category=category, status=Post.Status.PUBLISHED,
                excerpt="Notes on building software, automating busy work and growing online.",
                body="<p>This is your first post. Edit or delete it from <strong>Dashboard → Blog → Posts</strong>.</p>",
            )
            created["posts"] = 1

        summary = ", ".join(f"{k}: {v}" for k, v in created.items() if v) or "nothing new (content already exists)"
        self.stdout.write(self.style.SUCCESS(f"Seeded {summary}"))
