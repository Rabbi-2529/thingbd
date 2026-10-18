from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.core.models import SiteSettings
from apps.website.management.commands import seed_seo
from apps.website.models import HomePage, Service


class SeedSeoTests(TestCase):
    def setUp(self):
        call_command("seed_content", verbosity=0)

    def run_cmd(self, *args):
        out = StringIO()
        call_command("seed_seo", *args, stdout=out)
        return out.getvalue()

    def test_all_texts_fit_their_fields(self):
        groups = [{"site": seed_seo.SITE}, {"home": seed_seo.HOME}, seed_seo.SERVICES,
                  seed_seo.PROJECTS, seed_seo.PAGES, seed_seo.POSTS]
        for group in groups:
            for key, values in group.items():
                with self.subTest(key=key):
                    self.assertLessEqual(len(values["meta_title"]), 60)
                    self.assertLessEqual(len(values["meta_description"]), 160)
                    self.assertLessEqual(len(values["meta_keywords"]), 255)

    def test_fills_empty_fields_only(self):
        service = Service.objects.get(slug="seo-growth")
        service.meta_title = "My own title"
        service.save()
        self.run_cmd()
        service.refresh_from_db()
        self.assertEqual(service.meta_title, "My own title")  # kept
        self.assertIn("organic traffic", service.meta_description)  # filled
        self.assertIn("technical SEO", service.meta_keywords)
        self.assertEqual(HomePage.load().meta_title, seed_seo.HOME["meta_title"])

    def test_overwrite_replaces_existing(self):
        site = SiteSettings.load()
        site.meta_title = "Old title"
        site.save()
        self.run_cmd("--overwrite")
        self.assertEqual(SiteSettings.load().meta_title, seed_seo.SITE["meta_title"])

    def test_dry_run_saves_nothing(self):
        output = self.run_cmd("--dry-run")
        self.assertIn("DRY RUN", output)
        self.assertEqual(Service.objects.get(slug="web-development").meta_title, "")

    def test_never_touches_images_and_is_idempotent(self):
        self.run_cmd()
        output = self.run_cmd()
        self.assertIn("0 field(s) updated", output)

    def test_live_page_uses_new_seo(self):
        self.run_cmd()
        response = self.client.get("/services/web-development/")
        self.assertContains(response, "<title>Web Development Company in Bangladesh | Thingbd</title>", html=False)
        self.assertContains(response, "web development Bangladesh, website design Dhaka", html=False)
