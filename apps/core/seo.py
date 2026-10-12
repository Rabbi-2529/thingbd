"""Builds the SEO meta tags for a page.

Each value is taken from the page's own SEO fields first, then from its content
(title, excerpt, cover image…), and finally from the defaults in Site settings.
"""

from django.utils.html import strip_tags
from django.utils.text import Truncator

from .models import SiteSettings, split_keywords


def _abs(request, url):
    return request.build_absolute_uri(url) if url else ""


def _file_url(field):
    try:
        return field.url if field else ""
    except ValueError:
        return ""


def build_seo(request, obj=None, *, title="", description="", image=None, og_type="website", site=None):
    """
    obj         — a model using SeoModel (Service, Project, Post, Page, HomePage) or None
    title       — fallback page title, e.g. the post title (gets " | Site name" appended)
    description — fallback description, e.g. the excerpt (HTML is stripped)
    image       — fallback image field, e.g. the cover image
    """
    site = site or SiteSettings.load()
    meta_title = getattr(obj, "meta_title", "") if obj else ""
    meta_description = getattr(obj, "meta_description", "") if obj else ""

    if meta_title:
        full_title = meta_title
    elif title:
        full_title = f"{title} | {site.site_name}"
    else:
        full_title = site.meta_title or site.site_name

    plain = " ".join(strip_tags(description or "").split())
    full_description = meta_description or Truncator(plain).chars(160) or site.meta_description

    keywords = obj.keyword_list if obj is not None and hasattr(obj, "keyword_list") else []
    keywords = keywords or split_keywords(site.meta_keywords)

    image_url = (
        _file_url(getattr(obj, "meta_image", None) if obj else None)
        or _file_url(image)
        or _file_url(site.og_image)
    )

    return {
        "title": full_title,
        "description": full_description,
        "keywords": keywords,
        "image": _abs(request, image_url),
        "url": request.build_absolute_uri(request.path),
        "type": og_type,
        "site_name": site.site_name,
    }
