import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.blog.models import Post
from apps.core.models import SiteSettings, split_keywords
from apps.website.models import HomePage, Service

TEMP_MEDIA = tempfile.mkdtemp(prefix="thingbd-test-media-")
GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,"
    b"\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class SeoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_content", verbosity=0)
        site = SiteSettings.load()
        site.meta_keywords = "software agency, Bangladesh"
        site.save()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def test_split_keywords(self):
        self.assertEqual(split_keywords(" Django,seo ; django ,, Web  Apps "), ["Django", "seo", "Web Apps"])

    def test_site_defaults_on_home(self):
        response = self.client.get("/")
        self.assertContains(response, "<title>Thingbd | Your Vision, Our Code</title>", html=False)
        self.assertContains(response, '<meta name="keywords" content="software agency, Bangladesh">', html=False)
        self.assertContains(response, 'property="og:url" content="http://testserver/"', html=False)

    def test_home_page_own_seo_overrides_defaults(self):
        home = HomePage.load()
        home.meta_title = "Thingbd — Software studio in Dhaka"
        home.meta_keywords = "web development, ERP"
        home.save()
        response = self.client.get("/")
        self.assertContains(response, "<title>Thingbd — Software studio in Dhaka</title>", html=False)
        self.assertContains(response, 'content="web development, ERP"', html=False)

    def test_fallbacks_for_a_service(self):
        response = self.client.get("/services/web-development/")
        self.assertContains(response, "<title>Web Development | Thingbd</title>", html=False)
        self.assertContains(response, 'name="description" content="Fast marketing sites', html=False)
        self.assertContains(response, 'content="software agency, Bangladesh"', html=False)  # site keywords

    def test_service_seo_fields(self):
        service = Service.objects.get(slug="web-development")
        service.meta_title = "Website development in Bangladesh"
        service.meta_description = "Custom websites built in Django."
        service.meta_keywords = "django, website"
        service.meta_image = SimpleUploadedFile("share.gif", GIF, content_type="image/gif")
        service.save()
        response = self.client.get("/services/web-development/")
        self.assertContains(response, "<title>Website development in Bangladesh</title>", html=False)
        self.assertContains(response, 'property="og:description" content="Custom websites built in Django."', html=False)
        self.assertContains(response, '<meta name="keywords" content="django, website">', html=False)
        self.assertContains(response, 'property="og:image" content="http://testserver/media/seo/share', html=False)
        self.assertContains(response, 'name="twitter:card" content="summary_large_image"', html=False)

    def test_blog_post_uses_excerpt_and_article_type(self):
        post = Post.objects.get(slug="welcome")
        response = self.client.get(post.get_absolute_url())
        self.assertContains(response, 'property="og:type" content="article"', html=False)
        self.assertContains(response, f'name="description" content="{post.excerpt}"', html=False)

    def test_dashboard_saves_keywords_cleanly(self):
        user = get_user_model().objects.create_user("ed", "ed@example.com", "Str0ng-pass!", is_staff=True)
        self.client.force_login(user)
        service = Service.objects.get(slug="web-development")
        response = self.client.post(reverse("dashboard:services_edit", args=[service.pk]), {
            "title": service.title, "slug": service.slug, "short_description": service.short_description,
            "is_active": "on", "meta_keywords": " django,SEO , Django, web apps ",
        })
        self.assertRedirects(response, reverse("dashboard:services_list"))
        service.refresh_from_db()
        self.assertEqual(service.meta_keywords, "django, SEO, web apps")

    def test_seo_fields_on_every_editor(self):
        user = get_user_model().objects.create_user("ed", "ed@example.com", "Str0ng-pass!", is_staff=True)
        self.client.force_login(user)
        service = Service.objects.first()
        for url in (reverse("dashboard:services_edit", args=[service.pk]), reverse("dashboard:projects_add"),
                    reverse("dashboard:posts_add"), reverse("dashboard:pages_add"), reverse("dashboard:home_page"),
                    reverse("dashboard:site_settings")):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, 'name="meta_keywords"')
                self.assertContains(response, "data-keywords")
