from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    # FR-012; AC-011
    path("reports/operational", views.operational, name="operational"),
    # FR-013; AC-025, AC-026
    path("reports/replacement-candidates", views.replacement_candidates, name="replacement_candidates"),
]
