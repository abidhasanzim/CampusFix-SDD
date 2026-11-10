"""Keep entry preferences, send and cancel entry notices, record entries and
failed attempts, enforce the notice rule, and delete entry records when
retention ends (FR-004; NFR-07, NFR-08, NFR-17).
"""
from __future__ import annotations

from datetime import datetime, time, timedelta

from apps.accounts.models import Person
from apps.campus_settings.models import CampusConfig
from apps.entry.models import EntryNotice, EntryPreference, VisitRecord
from apps.maintenance.models import MaintenanceRequest, WorkOrder


def set_preference(request: MaintenanceRequest, preference: str, time_slots: list[tuple[int, time, time]], now: datetime) -> EntryPreference:
    """Save a resident's entry preference, cancelling any pending notice.

    Success: returns the EntryPreference; any pending EntryNotice for the
    request's work order becomes cancelled=True as part of the same save.
    Failure: raises ValueError if preference="PREFERRED_TIME_SLOTS" and
    `time_slots` is empty (at least one slot is required).
    Spec rule: FR-004 (changed preference cancels pending notice and
    requires a new visit window and notice); AC-014.
    Injected: `now` as updated_at.
    """
    raise NotImplementedError


def check_window(campus_config: CampusConfig, visit_window_start: datetime, notice_given_at: datetime, repair_order_filed: bool) -> bool:
    """Check whether a proposed visit window satisfies the notice rule.

    Success: returns True if elapsed time from `notice_given_at` to
    `visit_window_start` is >= `campus_config.min_entry_notice`, or >=
    `campus_config.repair_order_notice` when `repair_order_filed` is True
    and that value is configured; a duration exactly at the limit passes.
    Failure: returns False (does not raise) when the elapsed time is short;
    the caller turns that into a rejected save.
    Spec rule: FR-004; NFR-08; NFR-17 (elapsed time from the server clock,
    exact-limit passes); Decision 8; AC-006, AC-034, AC-048.
    Injected: none; both timestamps are passed in by the caller.
    """
    raise NotImplementedError


def send_notice(work_order: WorkOrder, visit_window_start: datetime, notice_given_at: datetime, repair_order_exception_used: bool, now: datetime) -> EntryNotice:
    """Create and record an entry notice for a visit window that has
    already passed `check_window`.

    Success: returns the created EntryNotice.
    Failure: raises ValueError if `check_window` would fail for these
    inputs (callers must check first; this is not re-validated here).
    Spec rule: FR-004; NFR-08; Decision 8 (`check_window` runs on T4, T7,
    T10, and reassignment).
    Injected: `now` as the notice's creation stamp (distinct from `sent_at`
    email delivery, owned by `notifications`).
    """
    raise NotImplementedError


def cancel_notice(entry_notice: EntryNotice, now: datetime) -> EntryNotice:
    """Cancel a pending entry notice.

    Success: returns `entry_notice` with cancelled=True.
    Failure: raises ValueError if already cancelled.
    Spec rule: FR-004 (a changed window or preference cancels the old notice); AC-014.
    Injected: `now` for record keeping.
    """
    raise NotImplementedError


def record_visit(work_order: WorkOrder, person: Person, resident_present: bool, knock_and_announce_confirmed: bool, outcome: str, now: datetime) -> VisitRecord:
    """Record an entry or a failed access attempt for a visit.

    Success: returns the created VisitRecord.
    Failure: raises ValueError if `outcome="ENTERED"` and
    `knock_and_announce_confirmed` is False (staff must knock and announce).
    Spec rule: FR-004 (knock-and-announce; Present+absent -> No Access,
    not an unauthorized entry); FR-011; NFR-08; AC-035.
    Injected: `now` as occurred_at.
    """
    raise NotImplementedError


def purge_expired(retention_period: timedelta, now: datetime) -> int:
    """Archive or delete entry records past their campus's retention period.

    Success: returns the count of VisitRecord/EntryNotice rows purged.
    Failure: none defined.
    Spec rule: NFR-07.
    Injected: `now` as the reference point for computing age.
    """
    raise NotImplementedError
