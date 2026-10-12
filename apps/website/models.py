from django.db import models
from django.urls import reverse

from apps.core.models import OrderedModel, SeoModel, SingletonModel, TimeStampedModel


class HomePage(SeoModel, SingletonModel):
    hero_eyebrow = models.CharField(max_length=120, default="Software studio · Dhaka, Bangladesh")
    hero_title = models.CharField(max_length=120, default="Your vision,")
    hero_highlight = models.CharField(max_length=120, default="our code.")
    hero_text = models.TextField(blank=True)
    hero_image = models.ImageField(upload_to="home/", blank=True)
    primary_button_label = models.CharField(max_length=60, default="Start your project")
    primary_button_url = models.CharField(max_length=255, default="#contact")
    secondary_button_label = models.CharField(max_length=60, blank=True, default="Explore services")
    secondary_button_url = models.CharField(max_length=255, blank=True, default="#services")

    services_eyebrow = models.CharField(max_length=80, default="Services")
    services_title = models.CharField(max_length=120, default="Six disciplines. One studio.")
    services_text = models.TextField(blank=True)

    process_eyebrow = models.CharField(max_length=80, default="Process")
    process_title = models.CharField(max_length=120, default="From idea to impact.")
    process_text = models.TextField(blank=True)

    work_eyebrow = models.CharField(max_length=80, default="Selected work")
    work_title = models.CharField(max_length=120, default="Built for real business.")
    work_text = models.TextField(blank=True)

    testimonials_eyebrow = models.CharField(max_length=80, default="Testimonials")
    testimonials_title = models.CharField(max_length=120, default="Trusted by teams.")

    faq_eyebrow = models.CharField(max_length=80, default="FAQ")
    faq_title = models.CharField(max_length=120, default="Questions, answered.")

    class Meta:
        verbose_name = "Home page"
        verbose_name_plural = "Home page"

    def __str__(self):
        return "Home page"


class Stat(OrderedModel):
    value = models.CharField(max_length=20)
    label = models.CharField(max_length=60)

    class Meta(OrderedModel.Meta):
        verbose_name = "Hero stat"

    def __str__(self):
        return f"{self.value} {self.label}"


class MarqueeItem(OrderedModel):
    text = models.CharField(max_length=60)

    class Meta(OrderedModel.Meta):
        verbose_name = "Marquee item"

    def __str__(self):
        return self.text


class Service(SeoModel, OrderedModel, TimeStampedModel):
    title = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    short_description = models.CharField(max_length=255)
    body = models.TextField("Details", blank=True)
    image = models.ImageField(upload_to="services/", blank=True)

    class Meta(OrderedModel.Meta):
        pass

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("service_detail", args=[self.slug])


class ProcessStep(OrderedModel):
    title = models.CharField(max_length=80)
    description = models.CharField(max_length=255)

    class Meta(OrderedModel.Meta):
        verbose_name = "Process step"

    def __str__(self):
        return self.title


class Project(SeoModel, OrderedModel, TimeStampedModel):
    title = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)
    client = models.CharField(max_length=120, blank=True)
    category = models.CharField(max_length=150, blank=True, help_text="e.g. Custom software · Analytics · Automation")
    cover_image = models.ImageField(upload_to="projects/", blank=True)
    cover_text = models.CharField(max_length=60, blank=True, help_text="Large text shown on the card when there is no cover image.")
    summary = models.CharField(max_length=255, blank=True)
    body = models.TextField("Case study", blank=True)
    tech_stack = models.CharField(max_length=255, blank=True, help_text="Comma-separated, e.g. Django, React, PostgreSQL")
    live_url = models.URLField(blank=True)
    services = models.ManyToManyField(Service, blank=True, related_name="projects")
    is_featured = models.BooleanField("Show on home page", default=True)

    class Meta(OrderedModel.Meta):
        verbose_name = "Portfolio project"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("project_detail", args=[self.slug])

    @property
    def tech_list(self):
        return [t.strip() for t in self.tech_stack.split(",") if t.strip()]


class ProjectImage(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="projects/gallery/")
    caption = models.CharField(max_length=150, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.caption or self.image.name


class Testimonial(OrderedModel):
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=100, blank=True)
    company = models.CharField(max_length=100, blank=True)
    photo = models.ImageField(upload_to="testimonials/", blank=True)
    quote = models.TextField()
    rating = models.PositiveSmallIntegerField(default=5, choices=[(i, f"{i} ★") for i in range(1, 6)])

    class Meta(OrderedModel.Meta):
        pass

    def __str__(self):
        return f"{self.name} — {self.company}" if self.company else self.name


class FAQ(OrderedModel):
    question = models.CharField(max_length=255)
    answer = models.TextField()

    class Meta(OrderedModel.Meta):
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return self.question


class TeamMember(OrderedModel):
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=100)
    photo = models.ImageField(upload_to="team/", blank=True)
    bio = models.TextField(blank=True)
    linkedin_url = models.URLField(blank=True)

    class Meta(OrderedModel.Meta):
        verbose_name = "Team member"

    def __str__(self):
        return self.name


class Page(SeoModel, TimeStampedModel):
    title = models.CharField(max_length=150)
    slug = models.SlugField(unique=True, help_text="URL: /p/<slug>/")
    body = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)
    show_in_header = models.BooleanField(default=False)
    show_in_footer = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "title"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("page_detail", args=[self.slug])
