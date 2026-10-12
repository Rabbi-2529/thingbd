# Django's built-in admin is kept only as a superuser fallback.
# Day-to-day content editing happens in the custom dashboard (apps.dashboard).
from django.contrib import admin

from .models import FAQ, HomePage, MarqueeItem, Page, ProcessStep, Project, ProjectImage, Service, Stat, TeamMember, Testimonial


class ProjectImageInline(admin.TabularInline):
    model = ProjectImage
    extra = 1


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "client", "is_featured", "is_active", "order")
    prepopulated_fields = {"slug": ("title",)}
    inlines = (ProjectImageInline,)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "order")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "is_published")
    prepopulated_fields = {"slug": ("title",)}


admin.site.register([HomePage, Stat, MarqueeItem, ProcessStep, Testimonial, FAQ, TeamMember])
