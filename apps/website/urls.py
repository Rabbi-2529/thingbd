from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse
from django.urls import path

from apps.blog import views as blog_views
from apps.leads import views as lead_views

from . import views
from .sitemaps import sitemaps


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /dashboard/",
        "Disallow: /django-admin/",
        f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


urlpatterns = [
    path("", views.home, name="home"),
    path("services/<slug:slug>/", views.service_detail, name="service_detail"),
    path("work/", views.project_list, name="project_list"),
    path("work/<slug:slug>/", views.project_detail, name="project_detail"),
    path("about/", views.about, name="about"),
    path("blog/", blog_views.post_list, name="post_list"),
    path("blog/category/<slug:category_slug>/", blog_views.post_list, name="post_category"),
    path("blog/<slug:slug>/", blog_views.post_detail, name="post_detail"),
    path("p/<slug:slug>/", views.page_detail, name="page_detail"),
    path("contact/", lead_views.contact_submit, name="contact_submit"),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("robots.txt", robots_txt),
]
