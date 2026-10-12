from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from django.views.generic import TemplateView, UpdateView

from apps.blog.models import Post
from apps.core.models import SiteSettings
from apps.leads.models import Lead
from apps.website.models import FAQ, HomePage, MarqueeItem, Page, ProcessStep, Project, Service, Stat, TeamMember, Testimonial

from .content_forms import HomePageForm
from .leads import lead_pipeline_summary
from .forms import LoginForm, ProfileForm, SiteSettingsForm, StyledPasswordChangeForm
from .mixins import StaffRequiredMixin


class LoginView(auth_views.LoginView):
    template_name = "dashboard/auth/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Django's LoginView puts its own `site` in the context; use our SiteSettings instead.
        context["site"] = SiteSettings.load()
        return context


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy("dashboard:login")


class DashboardView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/index.html"
    page_title = "Dashboard"
    active_nav = "dashboard"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["kpis"] = [
            {"label": "New leads", "value": Lead.objects.filter(status=Lead.Status.NEW).count(), "icon": "mark_email_unread", "tone": "violet"},
            {"label": "Total leads", "value": Lead.objects.count(), "icon": "inbox", "tone": "blue"},
            {"label": "Published posts", "value": Post.published.count(), "icon": "article", "tone": "green"},
            {"label": "Portfolio projects", "value": Project.objects.filter(is_active=True).count(), "icon": "work", "tone": "amber"},
        ]
        context["content_counts"] = [
            ("Services", Service.objects.count(), "design_services", reverse_lazy("dashboard:services_list")),
            ("Portfolio projects", Project.objects.count(), "work", reverse_lazy("dashboard:projects_list")),
            ("Testimonials", Testimonial.objects.count(), "reviews", reverse_lazy("dashboard:testimonials_list")),
            ("FAQs", FAQ.objects.count(), "quiz", reverse_lazy("dashboard:faqs_list")),
            ("Team members", TeamMember.objects.count(), "groups", reverse_lazy("dashboard:team_list")),
            ("Pages", Page.objects.count(), "description", reverse_lazy("dashboard:pages_list")),
            ("Blog posts", Post.objects.count(), "article", reverse_lazy("dashboard:posts_list")),
        ]
        context["recent_leads"] = Lead.objects.all()[:6]
        context["pipeline"] = lead_pipeline_summary()
        return context


class SiteSettingsView(StaffRequiredMixin, UpdateView):
    template_name = "dashboard/settings/site_settings.html"
    form_class = SiteSettingsForm
    page_title = "Site settings"
    active_nav = "site_settings"
    success_url = reverse_lazy("dashboard:site_settings")

    def get_object(self, queryset=None):
        return SiteSettings.load()

    def form_valid(self, form):
        messages.success(self.request, "Site settings saved.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please fix the highlighted fields.")
        return super().form_invalid(form)


class HomePageView(StaffRequiredMixin, UpdateView):
    template_name = "dashboard/content/home_page.html"
    form_class = HomePageForm
    page_title = "Home page"
    active_nav = "home"
    success_url = reverse_lazy("dashboard:home_page")

    def get_object(self, queryset=None):
        return HomePage.load()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["related"] = [
            ("Hero stats", "monitoring", reverse_lazy("dashboard:stats_list"), Stat.objects.filter(is_active=True).count()),
            ("Marquee", "text_rotation_none", reverse_lazy("dashboard:marquee_list"), MarqueeItem.objects.filter(is_active=True).count()),
            ("Process steps", "timeline", reverse_lazy("dashboard:process_list"), ProcessStep.objects.filter(is_active=True).count()),
            ("Services", "design_services", reverse_lazy("dashboard:services_list"), Service.objects.filter(is_active=True).count()),
            ("Testimonials", "reviews", reverse_lazy("dashboard:testimonials_list"), Testimonial.objects.filter(is_active=True).count()),
            ("FAQs", "quiz", reverse_lazy("dashboard:faqs_list"), FAQ.objects.filter(is_active=True).count()),
        ]
        return context

    def form_valid(self, form):
        messages.success(self.request, "Home page saved.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please fix the highlighted fields.")
        return super().form_invalid(form)


class ProfileView(StaffRequiredMixin, UpdateView):
    template_name = "dashboard/account/profile.html"
    form_class = ProfileForm
    page_title = "My profile"
    active_nav = "profile"
    success_url = reverse_lazy("dashboard:profile")

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Profile updated.")
        return super().form_valid(form)


class PasswordChangeView(StaffRequiredMixin, auth_views.PasswordChangeView):
    template_name = "dashboard/account/password_change.html"
    form_class = StyledPasswordChangeForm
    page_title = "Change password"
    active_nav = "password"
    success_url = reverse_lazy("dashboard:index")

    def form_valid(self, form):
        messages.success(self.request, "Password changed.")
        return super().form_valid(form)
