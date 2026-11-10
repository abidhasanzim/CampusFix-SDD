"""Decide whether a user may see or act on a request, work order, photo, or
report, and log each permitted view. A record the user may not see and one
that does not exist return the same not-found result (Decision 12).
"""
from __future__ import annotations

from datetime import datetime

from apps.accounts.models import Person
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
    raise NotImplementedError


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
