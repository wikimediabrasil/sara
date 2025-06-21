from django.urls import path
from . import views

app_name = "report"

urlpatterns = [
    path("add", views.add_report, name="add_report"),
    path("list", views.list_reports, name="list_reports"),
    path("list/<int:year>", views.list_reports_of_year, name="list_reports_of_year"),
    path("<int:report_id>/view", views.detail_report, name="detail_report"),
    path("<int:report_id>/export", views.export_report, name="export_report"),
    path("list/<int:year>/export", views.export_report, name="export_year_reports"),
    path("all/export", views.export_report, name="export_all_reports"),
    path("<int:report_id>/update", views.update_report, name="update_report"),
    path("<int:report_id>/delete", views.delete_report, name="delete_report"),
    path("get/metrics", views.get_metrics, name="get_metrics"),
]
