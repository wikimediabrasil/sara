from django.urls import path

from . import views

app_name = 'metrics'

urlpatterns = [
    path('', views.index, name='index'),
    path('about', views.about, name='about'),
    path('activities_plan', views.show_activities_plan, name='show_activities'),
    path('metrics_per_project', views.show_metrics_per_project, name='per_project'),
    path('metrics_per_project/<int:project_id>', views.show_metrics_for_specific_project, name='specific_project'),
    path('detailed_metrics_per_project', views.show_detailed_metrics_per_project, name='detailed_per_project'),
    path('update_metrics', views.update_metrics_relations, name='update_metrics'),
    path('metrics_reports/<int:metric_id>', views.metrics_reports, name='metrics_reports'),
    path("trimester", views.export_trimester_report, name="export_reports_per_trimester"),
    path("trimester/per_area", views.export_trimester_report_by_by_area_responsible, name="export_reports_per_area"),
    path("report/per_area", views.view_semester_report_per_area, name="view_semester_report"),
    path("prepare_pdf", views.prepare_pdf, name="wmf_report"),
]
