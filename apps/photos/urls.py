from django.urls import path

from . import views

app_name = "photos"

urlpatterns = [
    # FR-001, FR-010, FR-017
    path("photos", views.upload, name="upload"),
    path("photos/<int:photo_id>", views.detail, name="detail"),
]
