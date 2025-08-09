"""sara URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib.auth import views as auth_views
from django.conf import settings


urlpatterns = [
    path('', include('metrics.urls', namespace='metrics')),
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    path('user/', include('users.urls', namespace='user')),
    path('calendar/', include('agenda.urls', namespace='agenda')),
    path('oauth/', include('social_django.urls', namespace='social')),
    path('strategy', include('strategy.urls', namespace='strategy')),
    path('report/', include('report.urls', namespace='report')),
    path('bug/', include('bug.urls', namespace='bug')),
]

urlpatterns += staticfiles_urlpatterns()
