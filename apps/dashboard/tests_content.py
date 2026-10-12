import json
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.website.models import FAQ, HomePage, Page, Project, Service

from .viewsets import VIEWSETS

TEMP_MEDIA = tempfile.mkdtemp(prefix="thingbd-test-media-")
GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,"
    b"\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class ContentScreensTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_content", verbosity=0)
        cls.user = get_user_model().objects.create_user("editor", "e@example.com", "Str0ng-pass!", is_staff=True)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.client.force_login(self.user)

    def test_every_screen_renders(self):
        for vs in VIEWSETS:
            obj = vs.get_queryset().first()
            urls = [vs.url("list"), vs.url("add"), vs.url("list") + "?q=a&status=on"]
            if obj:
                urls += [vs.url("edit", obj.pk), vs.url("delete", obj.pk)]
            for url in urls:
                with self.subTest(url=url):
                    self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get(reverse("dashboard:home_page")).status_code, 200)

    def test_screens_require_staff(self):
        self.client.logout()
        response = self.client.get(reverse("dashboard:services_list"))
        self.assertEqual(response.status_code, 302)
        response = self.client.post(reverse("dashboard:services_reorder"), "{}", content_type="application/json")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Service.objects.count(), 6)

    def test_create_service_goes_to_end_and_shows_on_site(self):
        response = self.client.post(reverse("dashboard:services_add"), {
            "title": "Mobile Apps", "slug": "mobile-apps", "short_description": "iOS and Android apps.",
            "body": "<p>We build <strong>apps</strong>.</p>", "is_active": "on",
            "image": SimpleUploadedFile("app.gif", GIF, content_type="image/gif"),
        })
        self.assertRedirects(response, reverse("dashboard:services_list"))
        service = Service.objects.get(slug="mobile-apps")
        self.assertEqual(service.order, Service.objects.exclude(pk=service.pk).order_by("-order").first().order + 1)
        self.assertTrue(service.image)
        self.assertContains(self.client.get("/"), "Mobile Apps")
        self.assertContains(self.client.get("/services/mobile-apps/"), "<strong>apps</strong>", html=False)

    def test_invalid_form_shows_errors(self):
        response = self.client.post(reverse("dashboard:services_add"), {"title": "", "slug": "web-development"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "error-text")
        self.assertContains(response, "already exists")

    def test_save_and_continue(self):
        service = Service.objects.first()
        response = self.client.post(reverse("dashboard:services_edit", args=[service.pk]), {
            "title": "Web Dev", "slug": service.slug, "short_description": "x", "_continue": "1",
        })
        self.assertRedirects(response, reverse("dashboard:services_edit", args=[service.pk]))
        service.refresh_from_db()
        self.assertEqual(service.title, "Web Dev")
        self.assertFalse(service.is_active)  # unchecked switch = hidden

    def test_project_with_gallery_and_services(self):
        services = list(Service.objects.values_list("pk", flat=True)[:2])
        response = self.client.post(reverse("dashboard:projects_add"), {
            "title": "ERP", "slug": "erp", "services": services, "is_active": "on", "is_featured": "on",
            "images-TOTAL_FORMS": "1", "images-INITIAL_FORMS": "0", "images-MIN_NUM_FORMS": "0", "images-MAX_NUM_FORMS": "1000",
            "images-0-image": SimpleUploadedFile("shot.gif", GIF, content_type="image/gif"),
            "images-0-caption": "Dashboard", "images-0-order": "1",
        })
        self.assertRedirects(response, reverse("dashboard:projects_list"))
        project = Project.objects.get(slug="erp")
        self.assertEqual(project.services.count(), 2)
        self.assertEqual(project.images.get().caption, "Dashboard")

    def test_toggle_visibility(self):
        faq = FAQ.objects.first()
        response = self.client.post(reverse("dashboard:faqs_toggle", args=[faq.pk]), HTTP_ACCEPT="application/json")
        self.assertEqual(response.json(), {"ok": True, "active": False})
        faq.refresh_from_db()
        self.assertFalse(faq.is_active)
        self.assertNotContains(self.client.get("/"), faq.question)

    def test_toggle_uses_published_field_for_pages(self):
        page = Page.objects.first()
        self.client.post(reverse("dashboard:pages_toggle", args=[page.pk]), HTTP_ACCEPT="application/json")
        page.refresh_from_db()
        self.assertFalse(page.is_published)
        self.assertEqual(self.client.get(page.get_absolute_url()).status_code, 404)

    def test_reorder(self):
        ids = list(Service.objects.values_list("pk", flat=True))[::-1]
        response = self.client.post(reverse("dashboard:services_reorder"), json.dumps({"ids": ids}), content_type="application/json")
        self.assertEqual(response.json()["count"], len(ids))
        self.assertEqual(list(Service.objects.values_list("pk", flat=True)), ids)

    def test_reorder_rejects_bad_payload(self):
        response = self.client.post(reverse("dashboard:services_reorder"), "nope", content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_bulk_hide_and_delete(self):
        ids = list(FAQ.objects.values_list("pk", flat=True)[:2])
        self.client.post(reverse("dashboard:faqs_bulk"), {"action": "hide", "ids": ids})
        self.assertEqual(FAQ.objects.filter(pk__in=ids, is_active=False).count(), 2)
        self.client.post(reverse("dashboard:faqs_bulk"), {"action": "delete", "ids": ids})
        self.assertFalse(FAQ.objects.filter(pk__in=ids).exists())

    def test_bulk_redirect_ignores_external_next(self):
        response = self.client.post(reverse("dashboard:faqs_bulk"), {"action": "hide", "ids": [], "next": "https://evil.example/"})
        self.assertRedirects(response, reverse("dashboard:faqs_list"), fetch_redirect_response=False)

    def test_delete_confirmation(self):
        faq = FAQ.objects.first()
        url = reverse("dashboard:faqs_delete", args=[faq.pk])
        self.assertContains(self.client.get(url), "cannot be undone")
        self.assertRedirects(self.client.post(url), reverse("dashboard:faqs_list"))
        self.assertFalse(FAQ.objects.filter(pk=faq.pk).exists())

    def test_search_and_filter(self):
        FAQ.objects.filter(question__icontains="long").update(is_active=False)
        response = self.client.get(reverse("dashboard:faqs_list"), {"q": "launch"})
        self.assertContains(response, "What happens after launch?")
        self.assertNotContains(response, "How long does a typical project take?")
        response = self.client.get(reverse("dashboard:faqs_list"), {"status": "off"})
        self.assertContains(response, "How long does a typical project take?")
        self.assertNotContains(response, "data-sortable")  # no dragging while filtered

    def test_home_page_editor(self):
        data = {f.name: getattr(HomePage.load(), f.name) for f in HomePage._meta.fields
                if f.name != "id" and f.get_internal_type() != "FileField" and not f.name.endswith("image")}
        data["hero_title"] = "Build faster,"
        response = self.client.post(reverse("dashboard:home_page"), data)
        self.assertRedirects(response, reverse("dashboard:home_page"))
        self.assertContains(self.client.get("/"), "Build faster,")
