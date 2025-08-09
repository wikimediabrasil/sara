from django.urls import path, include
from . import views

app_name = "users"

urlpatterns = [
    path("<int:user_id>/profile", views.update_profile, name="profile"),
    path("register", views.register, name="register"),
    path('accounts/login', views.login_oauth, name='login'),
    path('oauth/', include('social_django.urls', namespace='social')),
    path('logout', views.logout_oauth, name='logout'),
]
