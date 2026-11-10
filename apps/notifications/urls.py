from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    # FR-002
    path("notifications", views.my_notifications, name="my_notifications"),
]
