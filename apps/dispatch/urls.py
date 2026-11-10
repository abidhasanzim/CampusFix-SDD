from django.urls import path

from . import views

app_name = "dispatch"

urlpatterns = [
    # FR-008; AC-003, AC-006, AC-020, AC-034, AC-048
    path("work-orders/<str:work_order_number>/assign", views.assign, name="assign"),
]
