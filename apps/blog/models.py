from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags

from apps.core.models import SeoModel, TimeStampedModel


class Category(models.Model):
    name = models.CharField(max_length=80)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class PublishedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(
            status=Post.Status.PUBLISHED, published_at__lte=timezone.now()
        )


class Post(SeoModel, TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="posts")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    cover_image = models.ImageField(upload_to="blog/", blank=True)
    excerpt = models.CharField(max_length=300, blank=True)
    body = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(default=timezone.now)
    is_featured = models.BooleanField(default=False)

    objects = models.Manager()
    published = PublishedManager()

    class Meta:
        ordering = ["-published_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("post_detail", args=[self.slug])

    @property
    def state(self):
        """'draft', 'scheduled' (published but dated in the future) or 'published'."""
        if self.status == self.Status.DRAFT:
            return "draft"
        return "scheduled" if self.published_at > timezone.now() else "published"

    @property
    def state_badge(self):
        return self.state, self.state.capitalize()

    @property
    def is_live(self):
        return self.state == "published"

    @property
    def reading_time(self):
        """Estimated minutes to read, at ~200 words per minute."""
        words = len(strip_tags(self.body).split())
        return max(1, round(words / 200))
