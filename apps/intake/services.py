"""Carry out resident and front-desk actions on requests: submit, save
drafts, track, change entry preference, add information, reopen, and
confirm or expire closure. Render the emergency banner.
"""
from __future__ import annotations

from datetime import datetime

from django.db import transaction

from apps.accounts.models import Person, StaffRole
from apps.accounts import services as accounts_services
from apps.audit import services as audit_services
from apps.campus_settings import services as campus_settings_services
from apps.campus_settings.models import CampusConfig
from apps.entry import services as entry_services
from apps.housing import services as housing_services
from apps.intake.models import Draft
from apps.maintenance import services as maintenance_services
from apps.maintenance.models import MaintenanceRequest
from apps.notifications import services as notifications_services
from apps.notifications.models import Notification
from apps.suggestions import services as suggestions_services
from campusfix.exceptions import ValidationError


def _create_request_from_form(
    owner: Person, recorded_by: Person | None, form_data: dict, now: datetime
) -> MaintenanceRequest:
    """Shared validation/creation path for `submit_request` and
    `submit_phone_report`: both resolve an owner and a recorder, then run
    the identical required-field check and submission transaction.
    """
    assignment = housing_services.get_current_assignment(owner.sso_subject, now.date())
    if assignment is None:
        raise PermissionError("no_current_assignment")

    area_type = form_data.get("area_type")
    exact_location = form_data.get("exact_location")
    description = form_data.get("description")
    entry_preference_data = form_data.get("entry_preference") or {}

    missing_fields = []
    if not area_type:
        missing_fields.append("area_type")
    if not exact_location:
        missing_fields.append("exact_location")
    if not description:
        missing_fields.append("description")
    if area_type != MaintenanceRequest.AREA_COMMON and not entry_preference_data.get("preference"):
        missing_fields.append("entry_preference")
    if missing_fields:
        raise ValidationError(missing_fields)

    room = assignment.room
    building = room.building
    resident_urgency = form_data.get("resident_urgency") or MaintenanceRequest.URGENCY_NORMAL

    with transaction.atomic():
        request = maintenance_services.create_request(
            owner=owner,
            recorded_by=recorded_by,
            building=building,
            room=room,
            area_type=area_type,
            exact_location=exact_location,
            description=description,
            onset=form_data.get("onset"),
            resident_urgency=resident_urgency,
            now=now,
        )

        if entry_preference_data.get("preference"):
            entry_services.set_preference(
                request,
                entry_preference_data["preference"],
                entry_preference_data.get("time_slots", []),
                now,
            )

        try:
            suggestions_enabled = campus_settings_services.get_config(building.campus).suggestions_enabled
        except CampusConfig.DoesNotExist:
            suggestions_enabled = False

        suggested_category = suggested_priority = ""
        duplicate_tracking_numbers: list[str] = []
        if suggestions_enabled:
            try:
                suggested_category, suggested_priority = suggestions_services.suggest_category_and_priority(
                    description, photo_count=0
                )
                open_requests = list(
                    MaintenanceRequest.objects.filter(building=building)
                    .exclude(
                        request_state__in=[MaintenanceRequest.STATE_COMPLETED, MaintenanceRequest.STATE_CLOSED]
                    )
                    .exclude(pk=request.pk)
                )
                duplicates = suggestions_services.find_duplicate_candidates(building, room, open_requests)
                duplicate_tracking_numbers = [candidate.tracking_number for candidate in duplicates]
            except ValueError:
                suggested_category = suggested_priority = ""
                duplicate_tracking_numbers = []

        maintenance_services.save_suggestion(
            request, suggested_category, suggested_priority, duplicate_tracking_numbers, now
        )

        audit_services.record_change(owner, "MaintenanceRequest", str(request.id), ["request_state"], now)

        notifications_services.record_notification(
            recipient=owner,
            event="SUBMITTED",
            tracking_number=request.tracking_number,
            channel=Notification.CHANNEL_EMAIL,
            content=f"Your request {request.tracking_number} has been submitted.",
            now=now,
        )

        Draft.objects.filter(user=owner).delete()

    return request


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
    return _create_request_from_form(owner=person, recorded_by=None, form_data=form_data, now=now)


def submit_phone_report(staff: Person, resident: Person, form_data: dict, now: datetime) -> MaintenanceRequest:
    """Record a phone-reported request on behalf of a verified resident.

    Success: returns the created MaintenanceRequest, owner=`resident`,
    recorded_by=`staff`.
    Failure: same validation failures as `submit_request`, plus
    PermissionError if `staff` holds no front-desk role.
    Spec rule: FR-019 (resident remains owner; staff identity saved as recordedBy).
    Injected: `now` for every timestamp in the transaction.
    """
    if not any(role.role_type == StaffRole.FRONT_DESK for role in accounts_services.get_staff_roles(staff)):
        raise PermissionError("staff member does not hold a front-desk role")

    owner = resident if isinstance(resident, Person) else Person.objects.get(sso_subject=resident)
    return _create_request_from_form(owner=owner, recorded_by=staff, form_data=form_data, now=now)


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
