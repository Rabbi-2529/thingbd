from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class OrderedModel(models.Model):
    order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField("Visible on site", default=True)

    class Meta:
        abstract = True
        ordering = ["order", "id"]


def split_keywords(value):
    """'django, SEO ,Django' -> ['django', 'SEO'] (trimmed, de-duplicated case-insensitively)."""
    seen, result = set(), []
    for word in (value or "").replace(";", ",").split(","):
        word = " ".join(word.split())
        if word and word.lower() not in seen:
            seen.add(word.lower())
            result.append(word)
    return result


class SeoModel(models.Model):
    """SEO meta tags. Empty fields fall back to the page's own content, then to Site settings."""

    meta_title = models.CharField("SEO title", max_length=70, blank=True,
                                  help_text="Shown in the browser tab and Google results. Best under 60 characters.")
    meta_description = models.CharField("SEO description", max_length=160, blank=True,
                                        help_text="Summary shown under the title in Google results. Best 120–155 characters.")
    meta_keywords = models.CharField("SEO keywords", max_length=255, blank=True,
                                     help_text="Several keywords, separated by commas.")
    meta_image = models.ImageField("Share image", upload_to="seo/", blank=True,
                                   help_text="Shown when the page is shared on Facebook, LinkedIn, WhatsApp, X. Ideal size 1200×630.")

    class Meta:
        abstract = True

    @property
    def keyword_list(self):
        return split_keywords(self.meta_keywords)


class SingletonModel(models.Model):
    """A model with exactly one row (pk=1), edited as a settings page in admin."""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class SiteSettings(SingletonModel):
    site_name = models.CharField(max_length=80, default="Thingbd")
    tagline = models.CharField(max_length=120, default="YOUR VISION, OUR CODE")
    logo = models.ImageField(upload_to="site/", blank=True, help_text="Shown in the header and footer. Leave empty to use the text logo.")
    favicon = models.ImageField(upload_to="site/", blank=True)

    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    whatsapp = models.CharField(max_length=40, blank=True, help_text="Number in international format, e.g. 8801XXXXXXXXX")
    address = models.CharField(max_length=255, blank=True)

    facebook_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    x_url = models.URLField("X / Twitter URL", blank=True)
    youtube_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)

    contact_eyebrow = models.CharField(max_length=80, default="Work with us")
    contact_title = models.CharField(max_length=120, default="Let’s level up")
    contact_highlight = models.CharField(max_length=120, default="your business.")
    contact_text = models.TextField(blank=True)
    lead_notification_email = models.CharField(
        max_length=500, blank=True,
        help_text="New leads are emailed here. Separate several addresses with commas. Defaults to the contact email.",
    )
    send_lead_autoreply = models.BooleanField(
        "Send an automatic reply", default=False,
        help_text="Email the visitor a confirmation after they submit the contact form.",
    )
    autoreply_subject = models.CharField(max_length=150, blank=True, default="Thanks for contacting Thingbd")
    autoreply_message = models.TextField(
        blank=True,
        default="Hi {name},\n\nThanks for telling us about your project. We have received your message "
                "and will get back to you within one business day.\n\nBest regards,\nThe Thingbd team",
        help_text="You can use {name} and {service} in the message.",
    )

    footer_text = models.CharField(max_length=255, blank=True)

    meta_title = models.CharField("Default SEO title", max_length=70, blank=True)
    meta_description = models.CharField("Default SEO description", max_length=160, blank=True)
    meta_keywords = models.CharField("Default SEO keywords", max_length=255, blank=True,
                                     help_text="Used on pages that have no keywords of their own. Separate with commas.")
    og_image = models.ImageField("Default share image", upload_to="site/", blank=True,
                                 help_text="Used when a page has no share image of its own. Ideal size 1200×630.")
    google_analytics_id = models.CharField(max_length=30, blank=True, help_text="e.g. G-XXXXXXXXXX")

    class Meta:
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"

    def __str__(self):
        return "Site settings"

