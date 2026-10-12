from django.shortcuts import get_object_or_404, render

from apps.core.seo import build_seo

from .models import FAQ, HomePage, MarqueeItem, Page, ProcessStep, Project, Service, Stat, TeamMember, Testimonial


def home(request):
    services = Service.objects.filter(is_active=True)
    home_page = HomePage.load()
    return render(request, "website/pages/home.html", {
        "home": home_page,
        "seo": build_seo(request, home_page, description=home_page.hero_text, image=home_page.hero_image),
        "stats": Stat.objects.filter(is_active=True),
        "marquee": MarqueeItem.objects.filter(is_active=True),
        "services": services,
        "steps": ProcessStep.objects.filter(is_active=True),
        "projects": Project.objects.filter(is_active=True, is_featured=True)[:3],
        "testimonials": Testimonial.objects.filter(is_active=True),
        "faqs": FAQ.objects.filter(is_active=True),
        "service_choices": services,
    })


def service_detail(request, slug):
    service = get_object_or_404(Service, slug=slug, is_active=True)
    return render(request, "website/pages/service_detail.html", {
        "service": service,
        "seo": build_seo(request, service, title=service.title,
                         description=service.short_description or service.body, image=service.image),
        "projects": service.projects.filter(is_active=True),
        "other_services": Service.objects.filter(is_active=True).exclude(pk=service.pk),
    })


def project_list(request):
    return render(request, "website/pages/project_list.html", {
        "projects": Project.objects.filter(is_active=True),
        "seo": build_seo(request, title="Our work",
                         description="A selection of products, platforms and brands we have shipped."),
    })


def project_detail(request, slug):
    project = get_object_or_404(Project.objects.prefetch_related("images", "services"), slug=slug, is_active=True)
    return render(request, "website/pages/project_detail.html", {
        "project": project,
        "more_projects": Project.objects.filter(is_active=True).exclude(pk=project.pk)[:3],
        "seo": build_seo(request, project, title=project.title,
                         description=project.summary or project.body, image=project.cover_image, og_type="article"),
    })


def about(request):
    return render(request, "website/pages/about.html", {
        "team": TeamMember.objects.filter(is_active=True),
        "steps": ProcessStep.objects.filter(is_active=True),
        "stats": Stat.objects.filter(is_active=True),
        "seo": build_seo(request, title="About us"),
    })


def page_detail(request, slug):
    page = get_object_or_404(Page, slug=slug, is_published=True)
    return render(request, "website/pages/page_detail.html", {
        "page": page,
        "seo": build_seo(request, page, title=page.title, description=page.body),
    })
