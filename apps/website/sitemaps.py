from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from apps.blog.models import Post
from apps.website.models import Page, Project, Service


class StaticSitemap(Sitemap):
    priority = 1.0

    def items(self):
        return ["home", "project_list", "about", "post_list"]

    def location(self, item):
        return reverse(item)


class ServiceSitemap(Sitemap):
    def items(self):
        return Service.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated_at


class ProjectSitemap(Sitemap):
    def items(self):
        return Project.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated_at


class PageSitemap(Sitemap):
    def items(self):
        return Page.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.updated_at


class PostSitemap(Sitemap):
    def items(self):
        return Post.published.all()

    def lastmod(self, obj):
        return obj.updated_at


sitemaps = {
    "static": StaticSitemap,
    "services": ServiceSitemap,
    "projects": ProjectSitemap,
    "pages": PageSitemap,
    "posts": PostSitemap,
}
