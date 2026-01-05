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
from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns


urlpatterns = [
    path('', include('metrics.urls', namespace='metrics')),
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    path('user/', include('users.urls', namespace='user')),
    path('oauth/', include('social_django.urls', namespace='social')),
    path('report/', include('report.urls', namespace='report')),
]

if settings.ENABLE_BUG_APP:
    urlpatterns += [path('bug/', include('bug.urls', namespace='bug'))]

if settings.ENABLE_AGENDA_APP:
    urlpatterns += [path('calendar/', include('agenda.urls', namespace='agenda'))]

if settings.ENABLE_STRATEGY_APP:
    urlpatterns += [path('strategy', include('strategy.urls', namespace='strategy'))]

urlpatterns += staticfiles_urlpatterns()
