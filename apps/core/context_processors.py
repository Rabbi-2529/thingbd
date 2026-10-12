from apps.website.models import Page

from .models import SiteSettings
from .seo import build_seo


def site(request):
    if request.path.startswith("/django-admin/"):
        return {}
    settings_obj = SiteSettings.load()
    context = {"site": settings_obj}
    if not request.path.startswith("/dashboard/"):
        pages = Page.objects.filter(is_published=True)
        context.update(
            header_pages=[p for p in pages if p.show_in_header],
            footer_pages=[p for p in pages if p.show_in_footer],
            # Site-wide defaults; views pass their own `seo` to override this.
            seo=build_seo(request, site=settings_obj),
        )
    return context
