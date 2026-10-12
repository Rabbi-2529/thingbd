from django.urls import path

from . import views
from .leads import LEADS, LeadDetailView, LeadExportView
from .uploads import EditorImageUploadView
from .viewsets import VIEWSETS

app_name = "dashboard"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="index"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("home-page/", views.HomePageView.as_view(), name="home_page"),
    path("settings/", views.SiteSettingsView.as_view(), name="site_settings"),
    path("account/profile/", views.ProfileView.as_view(), name="profile"),
    path("account/password/", views.PasswordChangeView.as_view(), name="password_change"),
    path("uploads/image/", EditorImageUploadView.as_view(), name="upload_image"),
    path("leads/export/", LeadExportView.as_view(), name="leads_export"),
    path("leads/<int:pk>/", LeadDetailView.as_view(), name="lead_detail"),
]

# Content screens: <key>/, <key>/add/, <key>/<pk>/edit/, <key>/<pk>/delete/, ...
for viewset in [*VIEWSETS, LEADS]:
    urlpatterns += viewset.get_urls()
