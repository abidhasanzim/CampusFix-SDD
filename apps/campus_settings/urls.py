from django.urls import path

from . import views

app_name = "campus_settings"

urlpatterns = [
    # NFR-13; AC-040
    path("campus-settings/<str:campus_code>", views.config_detail, name="config_detail"),
]
