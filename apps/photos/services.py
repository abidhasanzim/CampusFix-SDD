"""Validate, store, and serve photographs privately. Hold uploads made
before submission until they are linked to a record, and delete photos
when retention ends (architecture Decision 13; FR-001, FR-010, FR-017).
"""
from __future__ import annotations

from datetime import datetime, timedelta

from apps.accounts.models import Person
from apps.housing.models import Campus
from apps.maintenance.models import MaintenanceRequest, WorkRecord
from apps.photos.models import Photograph


def upload_unattached(owner: Person, file_bytes: bytes, content_type: str, campus: Campus, now: datetime) -> Photograph:
    """Validate and store one photo as an unattached upload owned by `owner`.

    Success: returns the created Photograph with linked=False, stored under
    a random name outside the web root.
    Failure: raises ValueError if `content_type` is not JPG/PNG after a
    content check, or the file exceeds the campus's `maxPhotoBytes`.
    Spec rule: FR-001 (optional; respects size/count limits); Decision 13.
    Injected: `now` as uploaded_at; the campus's `maxPhotoBytes` (via `campus_settings`).
    """
    raise NotImplementedError


def link_to_request(photo: Photograph, request: MaintenanceRequest, campus: Campus, now: datetime) -> Photograph:
    """Attach a previously unattached photo to a submitted or existing request.

    Success: returns `photo` with linked=True and `request` set.
    Failure: raises ValueError if the request already has
    `maxPhotosPerRequest` linked photos for its campus.
    Spec rule: FR-001, FR-017; Decision 13.
    Injected: the campus's `maxPhotosPerRequest` (via `campus_settings`).
    """
    raise NotImplementedError


def link_to_work_record(photo: Photograph, work_record: WorkRecord) -> Photograph:
    """Attach a previously unattached photo to a technician's work record
    (before/after repair photos).

    Success: returns `photo` with linked=True and `work_record` set.
    Failure: none defined beyond photo already being linked (ValueError).
    Spec rule: FR-010 (optional before/after photographs).
    Injected: none.
    """
    raise NotImplementedError


def serve_photo(actor: Person, photo: Photograph, now: datetime) -> bytes:
    """Return the raw bytes of a photo the actor is permitted to view.

    Success: returns the file's bytes.
    Failure: raises LookupError if `actor` may not view the linked record
    (delegates to `access.get_viewable_photo`).
    Spec rule: NFR-01 (photos visible only to owner/supervisor/technician/recorder).
    Injected: `now` for the audit "VIEW" entry.
    """
    raise NotImplementedError


def purge_expired(retention_period: timedelta, now: datetime) -> int:
    """Archive or delete photographs past their campus's retention period.

    Success: returns the count of photographs purged.
    Failure: none defined.
    Spec rule: NFR-07 (archived or deleted after retentionPeriod).
    Injected: `now` as the reference point for computing age.
    """
    raise NotImplementedError
