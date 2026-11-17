"""Carry out supervisor decisions before dispatch: confirm category and
priority, link or merge duplicates, close without a work order, and
re-categorize transferred work orders. Raise and show escalations.
"""
from __future__ import annotations

from datetime import datetime

from django.db import transaction as db_transaction

from apps.accounts import services as accounts_services
from apps.accounts.models import Person, StaffRole
from apps.housing.models import Campus
from apps.maintenance import services as maintenance_services
from apps.maintenance.models import MaintenanceRequest, WorkOrder
from apps.notifications import services as notifications_services
from apps.notifications.models import Notification
from apps.triage.models import Escalation

_TRIAGE_ELIGIBLE_STATES = {MaintenanceRequest.STATE_SUBMITTED, MaintenanceRequest.STATE_REOPENED}


def _require_supervisor(supervisor: Person, campus: Campus) -> None:
    is_supervisor = any(
        role.role_type == StaffRole.SUPERVISOR and role.campus_id == campus.id
        for role in accounts_services.get_staff_roles(supervisor)
    )
    if not is_supervisor:
        raise PermissionError("supervisor role required for this campus")


def get_triage_item(supervisor: Person, tracking_number: str, now: datetime) -> dict:
    """Return a submitted/reopened request's triage screen data: the
    request, its advisory suggestion (if any), and duplicate candidates,
    clearly labeled as suggestions rather than final values.

    Success: returns a dict with the request and its stored Suggestion
    (suggested_* fields only; final_* fields are null until confirmed).
    Failure: raises LookupError if `tracking_number` does not exist or is
    not in a triage-eligible state (delegates to `access`).
    Spec rule: FR-014 (labeled as suggestions, not final values; no
    automatic merge or final priority); NFR-03; AC-015, AC-018.
    Injected: `now` for the audit "VIEW" entry (via `access`).
    """
    try:
        request = MaintenanceRequest.objects.select_related("suggestion").get(tracking_number=tracking_number)
    except MaintenanceRequest.DoesNotExist:
        raise LookupError("not found")

    if request.request_state not in _TRIAGE_ELIGIBLE_STATES:
        raise LookupError("not found")

    suggestion = getattr(request, "suggestion", None)

    return {
        "tracking_number": request.tracking_number,
        "status": request.request_state,
        "version": request.version,
        "resident_urgency": request.resident_urgency,
        "suggestion": {
            "suggested_category": suggestion.suggested_category if suggestion else "",
            "suggested_priority": suggestion.suggested_priority if suggestion else "",
            "duplicate_candidate_tracking_numbers": (
                suggestion.duplicate_candidate_tracking_numbers if suggestion else []
            ),
            "final_category": (suggestion.final_category or None) if suggestion else None,
            "final_priority": (suggestion.final_priority or None) if suggestion else None,
        },
    }


def confirm_triage(supervisor: Person, tracking_number: str, category: str, priority: str, now: datetime, expected_version: int) -> WorkOrder:
    """Confirm or override category and final priority for a
    submitted/reopened request, creating or linking its work order (T2/T14).

    Success: returns the WorkOrder the request is now linked to, status="ACKNOWLEDGED".
    Failure: raises ValueError if `category` or `priority` is blank;
    raises ConcurrencyError if the request's version has changed since it
    was opened (two supervisors triaging at once — exactly one succeeds).
    Spec rule: FR-006 (manual triage works if suggestions are off or
    fail); NFR-15; AC-002, AC-015, AC-046.
    Injected: `now` for the T2/T14 history and the triage decision timestamp.
    """
    if not category or not priority:
        raise ValueError("category and priority are required")

    valid_priorities = {choice[0] for choice in WorkOrder.PRIORITY_CHOICES}
    if priority not in valid_priorities:
        raise ValueError(f"priority must be one of {sorted(valid_priorities)}")

    try:
        request = MaintenanceRequest.objects.select_related("suggestion").get(tracking_number=tracking_number)
    except MaintenanceRequest.DoesNotExist:
        raise LookupError("not found")

    _require_supervisor(supervisor, request.building.campus)

    is_reopened = request.request_state == MaintenanceRequest.STATE_REOPENED
    transition_id = "T14" if is_reopened else "T2"
    prior_work_order = request.work_orders.order_by("-created_at").first() if is_reopened else None

    with db_transaction.atomic():
        request = maintenance_services.transition(
            record=request,
            transition_id=transition_id,
            to_status=MaintenanceRequest.STATE_ACKNOWLEDGED,
            trigger="supervisor_confirms_triage",
            actor=supervisor,
            now=now,
            expected_version=expected_version,
        )

        work_order = maintenance_services.create_work_order(
            requests=[request], category=category, priority=priority, prior_work_order=prior_work_order, now=now
        )

        suggestion = getattr(request, "suggestion", None)
        if suggestion is not None:
            maintenance_services.confirm_triage_decision(suggestion, category, priority, supervisor, now)

        notifications_services.record_notification(
            recipient=request.owner,
            event="ACKNOWLEDGED",
            tracking_number=request.tracking_number,
            channel=Notification.CHANNEL_EMAIL,
            content=f"Your request {request.tracking_number} has been acknowledged.",
            now=now,
        )

    return work_order


def merge_duplicates(supervisor: Person, tracking_numbers: list[str], category: str, priority: str, now: datetime) -> WorkOrder:
    """Combine multiple Submitted reports of the same problem into one work order.

    Success: returns one new WorkOrder linked to every request in
    `tracking_numbers`; each original tracking number, owner, and history
    is retained.
    Failure: raises ValueError if the requests are not all in the same
    building, or if any named request already has an active dispatched
    work order (Non-goal 7: cannot merge two dispatched work orders).
    Spec rule: FR-007; AC-008, AC-024.
    Injected: `now` for the T2 history timestamp on each request.
    """
    raise NotImplementedError


def link_to_active_work_order(supervisor: Person, tracking_number: str, work_order_number: str, now: datetime) -> WorkOrder:
    """Link one newly submitted request to an existing active (not yet
    completed) work order instead of dispatching a second visit.

    Success: returns the WorkOrder with the request added to its linked requests.
    Failure: raises ValueError if the request's building differs from the
    work order's, or the work order is already "Completed".
    Spec rule: FR-007; AC-023.
    Injected: `now` for the request's T2 history timestamp.
    """
    raise NotImplementedError


def close_before_dispatch(supervisor: Person, tracking_number: str, reason: str, now: datetime) -> MaintenanceRequest:
    """Close an invalid Submitted or Reopened request without dispatching
    maintenance (T3).

    Success: returns the request with request_state="CLOSED" and
    `closed_reason` set; notifies the owner with the reason.
    Failure: raises ValueError if the request already has active
    dispatched work, or `reason` is blank.
    Spec rule: FR-018; AC-029; T3.
    Injected: `now` as the T3 history timestamp.
    """
    raise NotImplementedError


def run_escalation_check(campus: Campus, now: datetime) -> list[Escalation]:
    """Evaluate overdue urgent-Submitted requests and overdue On-Hold work
    orders for one campus, raising at most one escalation per overdue period.

    Success: returns the Escalation rows created by this run (empty if none
    are newly overdue); a uniqueness constraint makes a repeated call for
    the same period a no-op.
    Failure: none defined; a campus with no configured `urgentResponseLimit`
    or `holdLimit` raises nothing for that rule.
    Spec rule: FR-015 (one escalation per overdue period; does not alter
    state or priority); AC-009, AC-027.
    Injected: `now` as the reference point for elapsed time (NFR-17).
    """
    raise NotImplementedError


def list_escalations(supervisor: Person, campus: Campus) -> list[Escalation]:
    """Return active escalations for a supervisor's campus.

    Success: returns Escalation rows for `campus`, newest first.
    Failure: raises PermissionError if `supervisor` is not scoped to `campus`.
    Spec rule: FR-015 (alerts the campus supervisor); Decision 9 (every
    supervisor of the campus).
    Injected: none.
    """
    raise NotImplementedError
