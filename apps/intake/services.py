"""Carry out resident and front-desk actions on requests: submit, save
drafts, track, change entry preference, add information, reopen, and
confirm or expire closure. Render the emergency banner.
"""
from __future__ import annotations

from datetime import datetime

from apps.accounts.models import Person
from apps.intake.models import Draft
from apps.maintenance.models import MaintenanceRequest


def save_draft(person: Person, form_data: dict, now: datetime) -> Draft:
    """Save (or replace) the resident's one server-side draft.

    Success: returns the upserted Draft for `person`.
    Failure: none defined.
    Spec rule: NFR-11 (unfinished forms are saved as drafts); AC-039.
    Injected: `now` as updated_at.
    """
    raise NotImplementedError


def get_draft(person: Person) -> Draft | None:
    """Return the resident's saved draft, if any.

    Success: returns the Draft, or None if none exists.
    Failure: none defined.
    Spec rule: NFR-11; AC-039 (restores the saved draft and text fields).
    Injected: none.
    """
    raise NotImplementedError


def submit_request(person: Person, form_data: dict, now: datetime) -> MaintenanceRequest:
    """Validate and submit a resident's maintenance request in one
    transaction: tracking number, T1 creation, entry preference, linking
    unattached photo uploads, suggestion record, confirmation notification,
    draft deletion.

    Success: returns the created MaintenanceRequest ("Submitted") with its
    tracking number; the draft is deleted.
    Failure: raises ValidationError listing every missing required field
    (areaType, exactLocation, description) if the submission is incomplete,
    or NFR-14's rule if `person` has no current room assignment; on any
    failure nothing is created and the draft is kept.
    Spec rule: FR-001; FR-014 (suggestions attached when enabled, skipped
    on error without blocking submission); NFR-14; AC-001, AC-012, AC-015, AC-039.
    Injected: `now` for every timestamp in the transaction; the housing
    lookup and suggestion call happen through their own modules.
    """
    raise NotImplementedError


def submit_phone_report(staff: Person, resident: Person, form_data: dict, now: datetime) -> MaintenanceRequest:
    """Record a phone-reported request on behalf of a verified resident.

    Success: returns the created MaintenanceRequest, owner=`resident`,
    recorded_by=`staff`.
    Failure: same validation failures as `submit_request`, plus
    PermissionError if `staff` holds no front-desk role.
    Spec rule: FR-019 (resident remains owner; staff identity saved as recordedBy).
    Injected: `now` for every timestamp in the transaction.
    """
    raise NotImplementedError


def get_request_detail(person: Person, tracking_number: str, now: datetime) -> dict:
    """Return a request's full timestamped status history, hold reason,
    next action, and resident-visible notes for its owner.

    Success: returns a dict with the request, its status history, and
    resident-visible notes only (internal staff notes excluded).
    Failure: raises LookupError for both a nonexistent tracking number and
    one belonging to another resident (delegates to `access`).
    Spec rule: FR-003; NFR-01; AC-003, AC-010.
    Injected: `now` for the audit "VIEW" entry (via `access`).
    """
    raise NotImplementedError


def add_information(person: Person, tracking_number: str, comment: str, photo_bytes: bytes | None, now: datetime) -> MaintenanceRequest:
    """Add a comment or photo to the resident's own active request without
    changing its state or tracking number.

    Success: returns the unchanged MaintenanceRequest; the comment/photo is
    appended to its history.
    Failure: raises PermissionError if `tracking_number` is not owned by
    `person`; raises ValueError if the request is "Closed".
    Spec rule: FR-017.
    Injected: `now` for the history entry's timestamp.
    """
    raise NotImplementedError


def reopen_request(person: Person, tracking_number: str, description: str, photo_bytes: bytes | None, now: datetime) -> MaintenanceRequest:
    """Reopen the resident's own Completed request (T13) under its
    original tracking number, without affecting other linked residents'
    requests or the completed work order.

    Success: returns the request with request_state="REOPENED".
    Failure: raises ValueError if the request is "Closed" (cannot reopen)
    or not owned by `person`.
    Spec rule: FR-005; AC-007, AC-045; T13.
    Injected: `now` as the T13 history timestamp.
    """
    raise NotImplementedError


def confirm_closure(person: Person, tracking_number: str, now: datetime) -> MaintenanceRequest:
    """Close the resident's own Completed request by explicit confirmation (T15).

    Success: returns the request with request_state="CLOSED".
    Failure: raises ValueError if the request is not "Completed" or not
    owned by `person`.
    Spec rule: FR-020; AC-031; T15.
    Injected: `now` as the T15 history timestamp.
    """
    raise NotImplementedError


def expire_closure(now: datetime) -> list[MaintenanceRequest]:
    """Auto-close every Completed request whose campus has a configured
    `closureConfirmationPeriod` that has elapsed (T15, system-triggered).

    Success: returns the list of requests closed by this run.
    Failure: none defined; a campus with no configured period closes nothing.
    Spec rule: FR-020 (closes automatically only if configured; otherwise
    stays Completed until the resident confirms); AC-032; T15.
    Injected: `now` as the reference point for elapsed time (NFR-17).
    """
    raise NotImplementedError


def change_entry_preference(person: Person, tracking_number: str, preference: str, time_slots: list, now: datetime) -> MaintenanceRequest:
    """Change the entry preference on the resident's own active request.

    Success: returns the unchanged-state MaintenanceRequest (self-transition);
    delegates the preference save and notice cancellation to `entry.set_preference`.
    Failure: raises PermissionError if not owned by `person`.
    Spec rule: FR-004; AC-014.
    Injected: `now`, forwarded to `entry.set_preference`.
    """
    raise NotImplementedError
