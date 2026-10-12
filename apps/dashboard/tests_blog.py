import shutil
import tempfile
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.blog.models import Category, Post

TEMP_MEDIA = tempfile.mkdtemp(prefix="thingbd-test-media-")
GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,"
    b"\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


def make_post(title, status=Post.Status.PUBLISHED, days=-1, category=None):
    return Post.objects.create(
        title=title, slug=title.lower().replace(" ", "-"), body=f"<p>{title} body</p>",
        status=status, published_at=timezone.now() + timedelta(days=days), category=category,
    )


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class BlogDashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.editor = User.objects.create_user("editor", "e@example.com", "Str0ng-pass!", is_staff=True, first_name="Ed")
        cls.news = Category.objects.create(name="News", slug="news")
        cls.live = make_post("Live post", category=cls.news)
        cls.draft = make_post("Draft post", status=Post.Status.DRAFT)
        cls.future = make_post("Future post", days=3)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.client.force_login(self.editor)

    # --- model ---------------------------------------------------------------
    def test_post_states(self):
        self.assertEqual(self.live.state, "published")
        self.assertEqual(self.draft.state, "draft")
        self.assertEqual(self.future.state, "scheduled")

    def test_reading_time(self):
        post = Post(body="<p>" + "word " * 650 + "</p>")
        self.assertEqual(post.reading_time, 3)

    # --- dashboard screens ---------------------------------------------------
    def test_screens_render(self):
        for url in (reverse("dashboard:posts_list"), reverse("dashboard:posts_add"),
                    reverse("dashboard:posts_edit", args=[self.live.pk]), reverse("dashboard:categories_list"),
                    reverse("dashboard:categories_add"), reverse("dashboard:categories_edit", args=[self.news.pk]),
                    reverse("dashboard:categories_delete", args=[self.news.pk])):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_list_shows_status_badges(self):
        response = self.client.get(reverse("dashboard:posts_list"))
        for badge in ("badge-published", "badge-draft", "badge-scheduled"):
            self.assertContains(response, badge)

    def test_filter_by_state_and_category(self):
        url = reverse("dashboard:posts_list")
        response = self.client.get(url, {"state": "scheduled"})
        self.assertContains(response, "Future post")
        self.assertNotContains(response, "Live post")
        response = self.client.get(url, {"category": self.news.pk})
        self.assertContains(response, "Live post")
        self.assertNotContains(response, "Draft post")
        # Unknown values are ignored instead of erroring
        self.assertEqual(self.client.get(url, {"state": "bogus", "category": "x"}).status_code, 200)

    def test_create_post_sets_author_and_publishes(self):
        response = self.client.post(reverse("dashboard:posts_add"), {
            "title": "Hello world", "slug": "hello-world", "excerpt": "Hi", "body": "<p>Hi <em>there</em></p>",
            "status": "published", "published_at": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
            "category": self.news.pk, "author": "",
            "cover_image": SimpleUploadedFile("c.gif", GIF, content_type="image/gif"),
        })
        self.assertRedirects(response, reverse("dashboard:posts_list"))
        post = Post.objects.get(slug="hello-world")
        self.assertEqual(post.author, self.editor)
        self.assertEqual(post.state, "published")
        self.client.logout()
        self.assertContains(self.client.get("/blog/hello-world/"), "<em>there</em>", html=False)

    def test_body_is_required(self):
        response = self.client.post(reverse("dashboard:posts_add"), {
            "title": "Empty", "slug": "empty", "body": "", "status": "draft",
            "published_at": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Post.objects.filter(slug="empty").exists())

    def test_bulk_publish_and_unpublish(self):
        url = reverse("dashboard:posts_bulk")
        self.client.post(url, {"action": "publish", "ids": [self.draft.pk]})
        self.draft.refresh_from_db()
        self.assertEqual(self.draft.state, "published")
        self.client.post(url, {"action": "unpublish", "ids": [self.live.pk]})
        self.live.refresh_from_db()
        self.assertEqual(self.live.state, "draft")

    def test_deleting_category_keeps_posts(self):
        self.client.post(reverse("dashboard:categories_delete", args=[self.news.pk]))
        self.live.refresh_from_db()
        self.assertIsNone(self.live.category)

    def test_category_list_counts_posts(self):
        response = self.client.get(reverse("dashboard:categories_list"))
        self.assertContains(response, "News")
        self.assertEqual(response.context["rows"][0]["obj"].post_count, 1)

    # --- public blog -----------------------------------------------------------
    def test_public_blog_hides_drafts_and_scheduled(self):
        self.client.logout()
        listing = self.client.get("/blog/")
        self.assertContains(listing, "Live post")
        self.assertNotContains(listing, "Draft post")
        self.assertNotContains(listing, "Future post")
        self.assertEqual(self.client.get("/blog/draft-post/").status_code, 404)
        self.assertEqual(self.client.get("/blog/future-post/").status_code, 404)

    def test_staff_can_preview_drafts(self):
        response = self.client.get("/blog/draft-post/")
        self.assertContains(response, "preview-banner")
        self.assertContains(response, 'content="noindex, nofollow"')
        self.assertNotContains(self.client.get("/blog/live-post/"), "preview-banner")

    def test_category_chips_only_show_live_categories(self):
        Category.objects.create(name="Empty", slug="empty")
        response = self.client.get("/blog/")
        self.assertContains(response, "/blog/category/news/")
        self.assertNotContains(response, "/blog/category/empty/")

    # --- editor image uploads -------------------------------------------------
    def test_editor_image_upload(self):
        response = self.client.post(reverse("dashboard:upload_image"),
                                    {"image": SimpleUploadedFile("My Photo.JPG", GIF, content_type="image/jpeg")})
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertTrue(data["url"].endswith(".gif"))  # saved under a random name with the real format
        self.assertNotIn("Photo", data["url"])
        self.assertIn("/uploads/", data["url"])

    def test_editor_upload_rejects_script_extensions(self):
        response = self.client.post(reverse("dashboard:upload_image"),
                                    {"image": SimpleUploadedFile("evil.php", GIF, content_type="image/gif")})
        self.assertEqual(response.status_code, 400)

    def test_editor_upload_rejects_non_images(self):
        response = self.client.post(reverse("dashboard:upload_image"),
                                    {"image": SimpleUploadedFile("x.png", b"not an image", content_type="image/png")})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])

    def test_editor_upload_requires_staff(self):
        self.client.logout()
        response = self.client.post(reverse("dashboard:upload_image"),
                                    {"image": SimpleUploadedFile("a.gif", GIF, content_type="image/gif")})
        self.assertEqual(response.status_code, 302)
