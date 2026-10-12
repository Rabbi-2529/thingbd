"""Forms for blog management in the dashboard (Phase 3)."""

from django import forms
from django.contrib.auth import get_user_model

from apps.blog.models import Category, Post

from .content_forms import SEO_FIELDS, SEO_SECTION, DashboardModelForm, SlugMixin


class PostForm(SlugMixin, DashboardModelForm):
    rich_text_fields = ("body",)
    fieldsets = [
        ("Post", "article", ["title", "slug", "excerpt", "body"]),
        SEO_SECTION,
    ]
    side_fieldsets = [
        ("Publishing", "event_available", ["status", "published_at", "is_featured"]),
        ("Organise", "label", ["category", "author"]),
        ("Cover image", "image", ["cover_image"]),
    ]

    class Meta:
        model = Post
        fields = ("title", "slug", "excerpt", "body", "status", "published_at", "is_featured",
                  "category", "author", "cover_image", *SEO_FIELDS)
        widgets = {
            "excerpt": forms.Textarea,
            "published_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }
        labels = {"published_at": "Publish date", "is_featured": "Featured post"}
        help_texts = {
            "excerpt": "Short summary for blog cards and search results.",
            "published_at": "Set a future date to schedule the post.",
            "meta_title": "Defaults to the post title.",
            "meta_description": "Defaults to the excerpt.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["author"].queryset = get_user_model().objects.filter(is_staff=True).order_by("first_name", "username")
        self.fields["author"].label_from_instance = lambda u: u.get_full_name() or u.username
        self.fields["category"].empty_label = "— No category —"
        self.fields["author"].empty_label = "— You —"
        self.fields["body"].required = True


class CategoryForm(SlugMixin, DashboardModelForm):
    slug_source = "name"

    class Meta:
        model = Category
        fields = ("name", "slug")
