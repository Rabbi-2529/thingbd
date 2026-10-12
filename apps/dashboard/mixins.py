from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from .navigation import build_navigation


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Only active staff users may use the dashboard; others are sent to the login page."""

    page_title = ""
    active_nav = ""

    def test_func(self):
        user = self.request.user
        return user.is_active and user.is_staff

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            # Logged in but not staff: show 403 instead of a login loop.
            self.raise_exception = True
        return super().handle_no_permission()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = self.page_title
        context["navigation"] = build_navigation(self.active_nav)
        return context
