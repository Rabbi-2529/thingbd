"""Dashboard screens for each content type. Adding a new type = one class here."""

from django.db.models import Count
from django.urls import reverse
from django.utils import timezone

from apps.blog.models import Category, Post
from apps.website.models import FAQ, MarqueeItem, Page, ProcessStep, Project, Service, Stat, TeamMember, Testimonial

from . import blog_forms as bf
from . import content_forms as f
from .crud import BulkAction, Column, CrudViewSet, ListFilter


class StatViewSet(CrudViewSet):
    model, form_class = Stat, f.StatForm
    key, icon = "stats", "monitoring"
    title, title_singular = "Hero stats", "Stat"
    description = "The numbers shown under the hero on the home page."
    columns = [Column("value", "Value", primary=True), Column("label", "Label")]
    search_fields = ["value", "label"]


class MarqueeViewSet(CrudViewSet):
    model, form_class = MarqueeItem, f.MarqueeItemForm
    key, icon = "marquee", "text_rotation_none"
    title, title_singular = "Marquee", "Marquee item"
    description = "Words that scroll across the home page under the hero."
    columns = [Column("text", "Text", primary=True)]
    search_fields = ["text"]


class ProcessStepViewSet(CrudViewSet):
    model, form_class = ProcessStep, f.ProcessStepForm
    key, icon = "process", "timeline"
    title, title_singular = "Process steps", "Process step"
    description = "How you work, shown on the home and About pages."
    columns = [Column("title", "Step", primary=True), Column("description", "Description", kind="muted")]
    search_fields = ["title", "description"]


class ServiceViewSet(CrudViewSet):
    model, form_class = Service, f.ServiceForm
    key, icon = "services", "design_services"
    public_path = "/services/__slug__/"
    title, title_singular = "Services", "Service"
    description = "Each service gets a card on the home page and its own details page."
    columns = [
        Column("image", "", kind="image"),
        Column("title", "Service", primary=True),
        Column("short_description", "Summary", kind="muted"),
        Column("updated_at", "Updated", kind="date"),
    ]
    search_fields = ["title", "short_description", "body"]


class ProjectViewSet(CrudViewSet):
    model, form_class = Project, f.ProjectForm
    key, icon = "projects", "work"
    public_path = "/work/__slug__/"
    title, title_singular = "Portfolio", "Project"
    description = "Case studies shown on the home page (when featured) and on /work/."
    columns = [
        Column("cover_image", "", kind="image"),
        Column("title", "Project", primary=True),
        Column("client", "Client", kind="muted"),
        Column("category", "Category", kind="muted"),
        Column("is_featured", "On home", kind="bool"),
    ]
    search_fields = ["title", "client", "category", "summary"]
    formsets = [("images", "Gallery", f.ProjectImageFormSet)]

    def get_queryset(self):
        return super().get_queryset().prefetch_related("services")


class TestimonialViewSet(CrudViewSet):
    model, form_class = Testimonial, f.TestimonialForm
    key, icon = "testimonials", "reviews"
    title, title_singular = "Testimonials", "Testimonial"
    description = "Client quotes shown on the home page."
    columns = [
        Column("photo", "", kind="image"),
        Column("name", "Name", primary=True),
        Column("company", "Company", kind="muted"),
        Column("rating", "Rating", kind="rating"),
    ]
    search_fields = ["name", "company", "quote"]


class FAQViewSet(CrudViewSet):
    model, form_class = FAQ, f.FAQForm
    key, icon = "faqs", "quiz"
    title, title_singular = "FAQs", "FAQ"
    description = "Questions and answers shown on the home page."
    columns = [Column("question", "Question", primary=True)]
    search_fields = ["question", "answer"]


class TeamViewSet(CrudViewSet):
    model, form_class = TeamMember, f.TeamMemberForm
    key, icon = "team", "groups"
    title, title_singular = "Team", "Team member"
    description = "People shown on the About page."
    columns = [
        Column("photo", "", kind="image"),
        Column("name", "Name", primary=True),
        Column("role", "Role", kind="muted"),
    ]
    search_fields = ["name", "role"]


class PageViewSet(CrudViewSet):
    model, form_class = Page, f.PageForm
    key, icon = "pages", "description"
    public_path = "/p/__slug__/"
    title, title_singular = "Pages", "Page"
    description = "Standalone pages such as Privacy Policy and Terms, at /p/<slug>/."
    active_field = "is_published"
    active_labels = ("Published", "Draft")
    columns = [
        Column("title", "Title", primary=True),
        Column("slug", "URL slug", kind="muted"),
        Column("show_in_header", "Header", kind="bool"),
        Column("show_in_footer", "Footer", kind="bool"),
        Column("updated_at", "Updated", kind="date"),
    ]
    search_fields = ["title", "body"]


def _filter_post_state(qs, value):
    now = timezone.now()
    if value == "draft":
        return qs.filter(status=Post.Status.DRAFT)
    if value == "scheduled":
        return qs.filter(status=Post.Status.PUBLISHED, published_at__gt=now)
    return qs.filter(status=Post.Status.PUBLISHED, published_at__lte=now)


def _publish(request, qs):
    count = qs.update(status=Post.Status.PUBLISHED)
    return f"{count} post(s) published. Posts dated in the future stay scheduled until then."


def _unpublish(request, qs):
    count = qs.update(status=Post.Status.DRAFT)
    return f"{count} post(s) moved to drafts."


class PostViewSet(CrudViewSet):
    model, form_class = Post, bf.PostForm
    key, icon = "posts", "article"
    public_path = "/blog/__slug__/"
    title, title_singular = "Posts", "Post"
    description = "Articles on the blog. Drafts and scheduled posts are only visible to dashboard users."
    active_field = None
    sortable = False
    paginate_by = 25
    site_link_label = "Preview on website"
    columns = [
        Column("cover_image", "", kind="image"),
        Column("title", "Title", primary=True),
        Column("category", "Category", kind="muted"),
        Column("state_badge", "Status", kind="status"),
        Column("published_at", "Publish date", kind="date"),
        Column("is_featured", "Featured", kind="bool"),
    ]
    search_fields = ["title", "excerpt", "body"]
    filters = [
        ListFilter("state", "Status", [("published", "Published"), ("scheduled", "Scheduled"), ("draft", "Draft")], _filter_post_state),
        ListFilter("category", "Category", lambda: Category.objects.values_list("pk", "name"),
                   lambda qs, value: qs.filter(category_id=value)),
    ]
    bulk_actions = [
        BulkAction("publish", "Publish", "publish", _publish),
        BulkAction("unpublish", "Move to drafts", "unpublished", _unpublish),
    ]

    def get_queryset(self):
        return Post.objects.select_related("category", "author")

    def before_save(self, request, obj, form, is_new):
        if not obj.author_id:
            obj.author = request.user


class CategoryViewSet(CrudViewSet):
    model, form_class = Category, bf.CategoryForm
    key, icon = "categories", "label"
    title, title_singular = "Categories", "Category"
    description = "Group blog posts by topic. Each category gets its own page at /blog/category/<slug>/."
    active_field = None
    sortable = False
    delete_note = "Posts in this category will not be deleted; they become uncategorised."
    columns = [
        Column("name", "Name", primary=True),
        Column("slug", "URL slug", kind="muted"),
        Column("post_count", "Posts"),
    ]
    search_fields = ["name"]

    def get_queryset(self):
        return Category.objects.annotate(post_count=Count("posts")).order_by("name")

    def build_row(self, obj):
        row = super().build_row(obj)
        row["site_url"] = reverse("post_category", args=[obj.slug])
        return row


VIEWSETS = [
    StatViewSet(), MarqueeViewSet(), ProcessStepViewSet(),
    ServiceViewSet(), ProjectViewSet(), TestimonialViewSet(), FAQViewSet(), TeamViewSet(), PageViewSet(),
    PostViewSet(), CategoryViewSet(),
]
