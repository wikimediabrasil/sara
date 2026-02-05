from django.urls import include, path

from . import views

app_name = "users"

urlpatterns = [
    path("accounts/login", views.login_oauth, name="login"),
    path("oauth", include("social_django.urls", namespace="social")),
    path("logout", views.logout_oauth, name="logout"),
    path("<su:username>/edit", views.update_profile, name="update_profile"),
    path("list", views.list_profiles, name="list_profiles"),
    path("<su:username>", views.detail_profile, name="view_profile"),
]
