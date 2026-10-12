from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase

from apps.blog.models import Post
from apps.core.models import SiteSettings
from apps.website.models import HomePage, Project, Service
from apps.leads.models import Lead


class SeededSiteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_content", verbosity=0)

    def test_home_renders_database_content(self):
        home = HomePage.load()
        home.hero_title = "Edited from admin"
        home.save()
        response = self.client.get("/")
        self.assertContains(response, "Edited from admin")
        self.assertContains(response, "Web Development")
        self.assertContains(response, "Operations Platform")
        self.assertContains(response, 'id="lead-form"')

    def test_hidden_service_not_shown(self):
        Service.objects.filter(slug="seo-growth").update(is_active=False)
        self.assertNotContains(self.client.get("/"), "SEO &amp; Growth</h3>")
        self.assertEqual(self.client.get("/services/seo-growth/").status_code, 404)

    def test_detail_pages(self):
        for url in ("/services/web-development/", "/work/", "/work/operations-platform/", "/about/",
                    "/blog/", "/blog/welcome/", "/p/privacy-policy/", "/sitemap.xml", "/robots.txt"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_draft_post_hidden(self):
        Post.objects.update(status=Post.Status.DRAFT)
        self.assertEqual(self.client.get("/blog/welcome/").status_code, 404)

    def test_seed_is_idempotent(self):
        call_command("seed_content", verbosity=0)
        self.assertEqual(Service.objects.count(), 6)
        self.assertEqual(Project.objects.count(), 2)

    def test_singleton_stays_single(self):
        SiteSettings(site_name="Other").save()
        self.assertEqual(SiteSettings.objects.count(), 1)
        self.assertEqual(SiteSettings.load().site_name, "Other")


class LeadFormTests(TestCase):
    url = "/contact/"
    valid = {"name": "John Doe", "email": "john@example.com", "message": "Build a site", "service": "Web Development"}

    def setUp(self):
        cache.clear()  # reset the per-IP rate limit between tests

    def test_rate_limit(self):
        for _ in range(5):
            self.client.post(self.url, self.valid, HTTP_ACCEPT="application/json")
        response = self.client.post(self.url, self.valid, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(Lead.objects.count(), 5)

    def test_json_submission_creates_lead(self):
        response = self.client.post(self.url, self.valid, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 200)
        lead = Lead.objects.get()
        self.assertEqual(lead.status, Lead.Status.NEW)
        self.assertEqual(lead.ip_address, "127.0.0.1")

    def test_invalid_submission_rejected(self):
        response = self.client.post(self.url, {"name": "", "email": "bad", "message": ""}, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 422)
        self.assertIn("email", response.json()["errors"])
        self.assertFalse(Lead.objects.exists())

    def test_honeypot_blocks_bots(self):
        response = self.client.post(self.url, {**self.valid, "website": "spam.example"}, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 422)
        self.assertFalse(Lead.objects.exists())

    def test_non_js_submission_redirects(self):
        response = self.client.post(self.url, self.valid)
        self.assertRedirects(response, "/#contact", fetch_redirect_response=False)
        self.assertEqual(Lead.objects.count(), 1)

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

