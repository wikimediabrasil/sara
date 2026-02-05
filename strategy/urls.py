from django.urls import path

from . import views

app_name = "strategy"

urlpatterns = [
    path("", views.show_strategy, name="show_strategy"),
]
