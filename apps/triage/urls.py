from django.urls import path

from . import views

app_name = "triage"

urlpatterns = [
    # FR-007; AC-008, AC-024 (literal path; must precede the tracking-number catch-all below)
    path("triage/merge", views.merge, name="merge"),
    # FR-015; AC-009, AC-027 (literal path; must precede the tracking-number catch-all below)
    path("triage/escalations", views.escalations, name="escalations"),
    # FR-006; AC-002, AC-015, AC-046
    path("triage/<str:tracking_number>/confirm", views.confirm, name="confirm"),
    # FR-007; AC-023
    path("triage/<str:tracking_number>/link", views.link, name="link"),
    # FR-018; AC-029
    path("triage/<str:tracking_number>/close", views.close, name="close"),
    # FR-014; AC-015, AC-018
    path("triage/<str:tracking_number>", views.triage_item, name="triage_item"),
]
