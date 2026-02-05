from django.urls import path

from . import views

app_name = "bug"

urlpatterns = [
    path("add", views.add_bug, name="create_bug"),
    path("list", views.list_bugs, name="list_bugs"),
    path("export", views.export_bugs, name="export_bugs"),
    path("<int:bug_id>/view", views.detail_bug, name="detail_bug"),
    path("<int:bug_id>/edit", views.update_bug, name="edit_bug"),
    path("<int:bug_id>/add_obs", views.add_observation, name="add_obs"),
    path("<int:bug_id>/edit_obs", views.edit_observation, name="edit_obs"),
]
