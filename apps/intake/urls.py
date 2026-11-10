from django.urls import path

from . import views

app_name = "intake"

urlpatterns = [
    # FR-001; NFR-11; AC-039
    path("requests/draft", views.draft, name="draft"),
    # FR-001; AC-001, AC-012, AC-015, AC-019
    path("requests", views.submit, name="submit"),
    # FR-019; AC-030
    path("requests/phone-intake", views.phone_intake, name="phone_intake"),
    # FR-003; AC-003(track), AC-010
    path("requests/<str:tracking_number>", views.request_detail, name="request_detail"),
    # FR-004; AC-014
    path("requests/<str:tracking_number>/entry-preference", views.entry_preference, name="entry_preference"),
    # FR-005; AC-007, AC-045
    path("requests/<str:tracking_number>/reopen", views.reopen, name="reopen"),
    # FR-017; AC-028
    path("requests/<str:tracking_number>/updates", views.add_information, name="add_information"),
    # FR-020; AC-031, AC-032
    path("requests/<str:tracking_number>/confirm-closure", views.confirm_closure, name="confirm_closure"),
]
