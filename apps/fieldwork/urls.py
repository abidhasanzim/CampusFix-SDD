from django.urls import path

from . import views

app_name = "fieldwork"

urlpatterns = [
    # FR-009; AC-033
    path("technician/assignments", views.my_assignments, name="my_assignments"),
    # FR-010 (T5)
    path("work-orders/<str:work_order_number>/start", views.start, name="start"),
    # FR-004, FR-010, FR-011; AC-035
    path("work-orders/<str:work_order_number>/entries", views.record_entry, name="record_entry"),
    # FR-010; AC-004, AC-017, AC-047
    path("work-orders/<str:work_order_number>/complete", views.complete, name="complete"),
    # FR-011; AC-005
    path("work-orders/<str:work_order_number>/hold", views.hold, name="hold"),
    # FR-011; AC-020, AC-035
    path("work-orders/<str:work_order_number>/no-access", views.no_access, name="no_access"),
    # FR-011; AC-016
    path("work-orders/<str:work_order_number>/transfer", views.transfer, name="transfer"),
    # FR-016; AC-021, AC-022
    path("work-orders/<str:work_order_number>/clear-hold", views.clear_hold, name="clear_hold"),
    # FR-013 (link)
    path("work-orders/<str:work_order_number>/equipment", views.link_equipment, name="link_equipment"),
]
