"""Root URL configuration for campusfix.

Every functional and nonfunctional requirement with a user-facing entry
point gets one REST route here, under /api/. See contracts.md section 2
for the full requirement -> route -> function table.
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.accounts.urls')),
    path('api/', include('apps.campus_settings.urls')),
    path('api/', include('apps.notifications.urls')),
    path('api/', include('apps.photos.urls')),
    path('api/', include('apps.intake.urls')),
    path('api/', include('apps.triage.urls')),
    path('api/', include('apps.dispatch.urls')),
    path('api/', include('apps.fieldwork.urls')),
    path('api/', include('apps.reports.urls')),
]
