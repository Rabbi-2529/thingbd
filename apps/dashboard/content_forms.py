"""Forms for the website content managed in the dashboard (Phase 2)."""

from django import forms

from apps.website.models import FAQ, HomePage, MarqueeItem, Page, ProcessStep, Project, ProjectImage, Service, Stat, TeamMember, Testimonial

from .forms import FieldsetFormMixin, StyledFormMixin


SEO_FIELDS = ["meta_title", "meta_description", "meta_keywords", "meta_image"]
SEO_SECTION = ("SEO", "travel_explore", SEO_FIELDS)


class DashboardModelForm(StyledFormMixin, FieldsetFormMixin, forms.ModelForm):
    pass


class SlugMixin:
    """Fill the slug from the title in the browser while the user hasn't typed one."""

    slug_source = "title"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "slug" in self.fields:
            self.fields["slug"].widget.attrs["data-slug-from"] = f"id_{self.slug_source}"
            self.fields["slug"].help_text = self.fields["slug"].help_text or "Used in the page URL. Letters, numbers and hyphens only."


class HomePageForm(DashboardModelForm):
    fieldsets = [
        ("Hero", "web_asset", ["hero_eyebrow", "hero_title", "hero_highlight", "hero_text", "hero_image",
                               "primary_button_label", "primary_button_url", "secondary_button_label", "secondary_button_url"]),
        ("Services section", "design_services", ["services_eyebrow", "services_title", "services_text"]),
        ("Process section", "timeline", ["process_eyebrow", "process_title", "process_text"]),
        ("Work section", "work", ["work_eyebrow", "work_title", "work_text"]),
        ("Testimonials & FAQ", "reviews", ["testimonials_eyebrow", "testimonials_title", "faq_eyebrow", "faq_title"]),
        SEO_SECTION,
    ]

    class Meta:
        model = HomePage
        fields = "__all__"
        labels = {
            "hero_eyebrow": "Small text above the title",
            "hero_highlight": "Highlighted (purple) line",
            "services_eyebrow": "Label", "process_eyebrow": "Label", "work_eyebrow": "Label",
            "testimonials_eyebrow": "Testimonials label", "faq_eyebrow": "FAQ label",
            "services_title": "Title", "process_title": "Title", "work_title": "Title",
            "services_text": "Intro text", "process_text": "Intro text", "work_text": "Intro text",
        }


class StatForm(DashboardModelForm):
    side_fieldsets = [("Visibility", "visibility", ["is_active"])]

    class Meta:
        model = Stat
        fields = ("value", "label", "is_active")
        help_texts = {"value": "e.g. 50+, 12, 100%", "label": "e.g. Products shipped"}


class MarqueeItemForm(DashboardModelForm):
    side_fieldsets = [("Visibility", "visibility", ["is_active"])]

    class Meta:
        model = MarqueeItem
        fields = ("text", "is_active")


class ProcessStepForm(DashboardModelForm):
    side_fieldsets = [("Visibility", "visibility", ["is_active"])]

    class Meta:
        model = ProcessStep
        fields = ("title", "description", "is_active")
        widgets = {"description": forms.Textarea}


class ServiceForm(SlugMixin, DashboardModelForm):
    rich_text_fields = ("body",)
    fieldsets = [
        ("Service", "design_services", ["title", "slug", "short_description"]),
        ("Details page", "article", ["body"]),
        SEO_SECTION,
    ]
    side_fieldsets = [("Visibility", "visibility", ["is_active"]), ("Image", "image", ["image"])]

    class Meta:
        model = Service
        fields = ("title", "slug", "short_description", "body", "image", "is_active", *SEO_FIELDS)
        widgets = {"short_description": forms.Textarea}


class ProjectForm(SlugMixin, DashboardModelForm):
    rich_text_fields = ("body",)
    fieldsets = [
        ("Project", "work", ["title", "slug", "client", "category", "summary"]),
        ("Case study", "article", ["body", "tech_stack", "live_url"]),
        ("Services", "design_services", ["services"]),
        SEO_SECTION,
    ]
    side_fieldsets = [
        ("Visibility", "visibility", ["is_active", "is_featured"]),
        ("Cover", "image", ["cover_image", "cover_text"]),
    ]

    class Meta:
        model = Project
        fields = ("title", "slug", "client", "category", "summary", "body", "tech_stack", "live_url", "services",
                  "is_active", "is_featured", "cover_image", "cover_text", *SEO_FIELDS)
        widgets = {"services": forms.CheckboxSelectMultiple, "summary": forms.Textarea}


class ProjectImageForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ProjectImage
        fields = ("image", "caption", "order")


ProjectImageFormSet = forms.inlineformset_factory(
    Project, ProjectImage, form=ProjectImageForm, extra=0, can_delete=True,
)


class TestimonialForm(DashboardModelForm):
    side_fieldsets = [("Visibility", "visibility", ["is_active"]), ("Photo", "image", ["photo"])]

    class Meta:
        model = Testimonial
        fields = ("name", "role", "company", "quote", "rating", "is_active", "photo")


class FAQForm(DashboardModelForm):
    side_fieldsets = [("Visibility", "visibility", ["is_active"])]

    class Meta:
        model = FAQ
        fields = ("question", "answer", "is_active")


class TeamMemberForm(DashboardModelForm):
    side_fieldsets = [("Visibility", "visibility", ["is_active"]), ("Photo", "image", ["photo"])]

    class Meta:
        model = TeamMember
        fields = ("name", "role", "bio", "linkedin_url", "is_active", "photo")


class PageForm(SlugMixin, DashboardModelForm):
    rich_text_fields = ("body",)
    fieldsets = [
        ("Page", "description", ["title", "slug", "body"]),
        SEO_SECTION,
    ]
    side_fieldsets = [("Visibility", "visibility", ["is_published", "show_in_header", "show_in_footer"])]

    class Meta:
        model = Page
        fields = ("title", "slug", "body", "is_published", "show_in_header", "show_in_footer", *SEO_FIELDS)
        help_texts = {"slug": "The page will be available at /p/<slug>/"}
