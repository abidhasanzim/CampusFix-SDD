"""Decide whether a user may see or act on a request, work order, photo, or
report, and log each permitted view. A record the user may not see and one
that does not exist return the same not-found result (Decision 12).
"""
from __future__ import annotations

from datetime import datetime

from apps.accounts.models import Person, StaffRole
from apps.audit import services as audit_services
from apps.maintenance.models import MaintenanceRequest, WorkOrder
from apps.photos.models import Photograph


def get_viewable_request(actor: Person, tracking_number: str, now: datetime) -> MaintenanceRequest:
    """Return a request only if `actor` may see it, logging the view.

    Success: returns the MaintenanceRequest and records an audit "VIEW" entry.
    Failure: raises LookupError for both a nonexistent tracking number and
    one belonging to someone `actor` may not see (NFR-01) — the two cases
    are indistinguishable to the caller.
    Spec rule: NFR-01; AC-010, AC-033, AC-037; Decision 12.
    Injected: `now` for the audit entry's timestamp.
    """
    raise NotImplementedError


def get_viewable_work_order(actor: Person, work_order_number: str, now: datetime) -> WorkOrder:
    """Return a work order only if `actor` may see it (its assigned
    technician, or a supervisor of its campus), logging the view.

    Success: returns the WorkOrder and records an audit "VIEW" entry.
    Failure: raises LookupError for both a nonexistent number and one
    `actor` may not see.
    Spec rule: NFR-01; AC-033, AC-037; Decision 12.
    Injected: `now` for the audit entry's timestamp.
    """
    try:
        work_order = WorkOrder.objects.get(work_order_number=work_order_number)
    except WorkOrder.DoesNotExist:
        raise LookupError("not found")

    is_assigned_technician = work_order.assigned_technician_id == actor.id

    is_campus_supervisor = False
    if not is_assigned_technician:
        linked_request = work_order.requests.select_related("building__campus").first()
        campus = linked_request.building.campus if linked_request else None
        is_campus_supervisor = campus is not None and StaffRole.objects.filter(
            person=actor, role_type=StaffRole.SUPERVISOR, campus=campus
        ).exists()

    if not (is_assigned_technician or is_campus_supervisor):
        raise LookupError("not found")

    audit_services.record_view(actor, "WorkOrder", str(work_order.id), now)
    return work_order


def get_viewable_photo(actor: Person, photo_id: int, now: datetime) -> Photograph:
    """Return a photograph only if `actor` may see its linked record.

    Success: returns the Photograph and records an audit "VIEW" entry.
    Failure: raises LookupError for both a nonexistent id and one `actor`
    may not see; AC-033 (not accessible by direct URL to another technician).
    Spec rule: NFR-01.
    Injected: `now` for the audit entry's timestamp.
    """
    raise NotImplementedError


def can_administer(actor: Person, campus) -> bool:
    """Report whether `actor` may see campus-level aggregates (reports).

    Success: returns True or False; never raises for a valid `actor`.
    Failure: none defined.
    Spec rule: NFR-01 (administrators see aggregates only, never resident
    identity or photographs).
    Injected: none.
    """
    raise NotImplementedError
