"""Carry out supervisor decisions before dispatch: confirm category and
priority, link or merge duplicates, close without a work order, and
re-categorize transferred work orders. Raise and show escalations.
"""
from __future__ import annotations

from datetime import datetime

from apps.accounts.models import Person
from apps.housing.models import Campus
from apps.maintenance.models import MaintenanceRequest, WorkOrder
from apps.triage.models import Escalation


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
    raise NotImplementedError


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
    raise NotImplementedError


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
