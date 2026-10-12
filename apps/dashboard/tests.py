import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.core.models import SiteSettings

User = get_user_model()
TEMP_MEDIA = tempfile.mkdtemp(prefix="thingbd-test-media-")

# 1x1 transparent GIF
GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,"
    b"\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


class DashboardAccessTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user("editor", "editor@example.com", "Str0ng-pass!", is_staff=True)
        self.customer = User.objects.create_user("visitor", "v@example.com", "Str0ng-pass!")

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(reverse("dashboard:index"))
        self.assertRedirects(response, f"{reverse('dashboard:login')}?next={reverse('dashboard:index')}")

    def test_login_page_renders(self):
        response = self.client.get(reverse("dashboard:login"))
        self.assertContains(response, "Welcome back")

    def test_staff_can_log_in(self):
        response = self.client.post(reverse("dashboard:login"), {"username": "editor", "password": "Str0ng-pass!"})
        self.assertRedirects(response, reverse("dashboard:index"))

    def test_non_staff_cannot_log_in(self):
        response = self.client.post(reverse("dashboard:login"), {"username": "visitor", "password": "Str0ng-pass!"})
        self.assertContains(response, "does not have dashboard access")

    def test_non_staff_session_gets_403(self):
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(reverse("dashboard:index")).status_code, 403)

    def test_logout_requires_post(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("dashboard:logout")).status_code, 405)
        response = self.client.post(reverse("dashboard:logout"))
        self.assertRedirects(response, reverse("dashboard:login"))


class DashboardPagesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("editor", "editor@example.com", "Str0ng-pass!", is_staff=True)
        self.client.force_login(self.user)

    def test_pages_render(self):
        for name in ("index", "site_settings", "profile", "password_change"):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(f"dashboard:{name}")).status_code, 200)

    def test_sidebar_links_every_section(self):
        response = self.client.get(reverse("dashboard:index"))
        self.assertNotContains(response, "Coming in a later phase")  # all phases built
        for name in ("site_settings", "home_page", "services_list", "posts_list", "leads_list"):
            self.assertContains(response, reverse(f"dashboard:{name}"))

    @override_settings(MEDIA_ROOT=TEMP_MEDIA)
    def test_save_site_settings_with_logo(self):
        data = {
            "site_name": "Thingbd", "tagline": "YOUR VISION, OUR CODE", "email": "hello@thingbd.com",
            "contact_eyebrow": "Work with us", "contact_title": "Let’s talk", "contact_highlight": "today.",
            "logo": SimpleUploadedFile("logo.gif", GIF, content_type="image/gif"),
        }
        response = self.client.post(reverse("dashboard:site_settings"), data)
        self.assertRedirects(response, reverse("dashboard:site_settings"))
        site = SiteSettings.load()
        self.assertEqual(site.email, "hello@thingbd.com")
        self.assertTrue(site.logo.name.startswith("site/logo"))
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def test_invalid_site_settings_shows_errors(self):
        response = self.client.post(reverse("dashboard:site_settings"), {"site_name": "", "email": "not-an-email"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "tab-error")

    def test_update_profile(self):
        self.client.post(reverse("dashboard:profile"), {"first_name": "Fazle", "last_name": "Rabbi", "email": "f@example.com"})
        self.user.refresh_from_db()
        self.assertEqual(self.user.get_full_name(), "Fazle Rabbi")

    def test_change_password(self):
        response = self.client.post(reverse("dashboard:password_change"), {
            "old_password": "Str0ng-pass!", "new_password1": "An0ther-str0ng!", "new_password2": "An0ther-str0ng!",
        })
        self.assertRedirects(response, reverse("dashboard:index"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("An0ther-str0ng!"))
