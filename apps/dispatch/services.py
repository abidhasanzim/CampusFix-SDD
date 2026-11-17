"""Assign and reassign a technician together with a visit window."""
from __future__ import annotations

from datetime import datetime, timedelta

from django.db import transaction as db_transaction
from django.utils.dateparse import parse_datetime

from apps.accounts.models import Person
from apps.campus_settings import services as campus_settings_services
from apps.campus_settings.models import CampusConfig
from apps.entry import services as entry_services
from apps.entry.models import EntryNotice
from apps.maintenance import services as maintenance_services
from apps.maintenance.models import WorkOrder
from apps.notifications import services as notifications_services
from apps.notifications.models import Notification
from campusfix.exceptions import ConcurrencyError

# Status lifecycle table: which transition this action applies for a given
# starting status. SCHEDULED is handled separately below as the FR-008
# self-transition (reassignment/new window while already Scheduled).
_ASSIGNABLE_FROM = {
    WorkOrder.STATUS_ACKNOWLEDGED: "T4",
    WorkOrder.STATUS_NO_ACCESS: "T7",
}


def _as_datetime(value):
    return parse_datetime(value) if isinstance(value, str) else value


def _reassign_without_status_change(work_order: WorkOrder, now: datetime, expected_version: int) -> WorkOrder:
    """FR-008's self-transition: reassignment or a new visit window while
    already Scheduled does not change status, so it does not go through
    `maintenance.transition()`'s T1-T15 table — but it still needs the same
    row lock and version check (NFR-15)."""
    locked = WorkOrder.objects.select_for_update().get(pk=work_order.pk)
    if locked.version != expected_version:
        raise ConcurrencyError(f"WorkOrder {locked.pk} has changed since it was read")
    locked.version = expected_version + 1
    locked.updated_at = now
    locked.save(update_fields=["version", "updated_at"])
    return locked


def assign_and_schedule(
    supervisor: Person,
    work_order_number: str,
    technician: Person,
    visit_window_start: datetime,
    visit_window_end: datetime,
    notice_given_at: datetime,
    repair_order_exception_used: bool,
    now: datetime,
    expected_version: int,
) -> WorkOrder:
    """Assign (or reassign) a work order to a technician with a visit
    window, atomically (T4, or a self-transition if already Scheduled).

    Success: returns the WorkOrder, status="SCHEDULED", with
    `assigned_technician` and visit window set; produces one resident
    notification (trade + window) and one technician assignment notice;
    a changed window cancels the old entry notice and sends a new one.
    Failure: raises ValueError if `entry.check_window` rejects the
    proposed window for the campus's notice rule (neither the technician
    nor the window is committed — all-or-nothing); raises ConcurrencyError
    on a stale `expected_version`.
    Spec rule: FR-008 (atomic; neither committed without both technician
    and window); NFR-15; AC-003, AC-006, AC-020, AC-034, AC-048.
    Injected: `now` for the T4 history/notification timestamps;
    `notice_given_at` for the entry-notice calculation.
    """
    visit_window_start = _as_datetime(visit_window_start)
    visit_window_end = _as_datetime(visit_window_end)
    notice_given_at = _as_datetime(notice_given_at)

    try:
        work_order = WorkOrder.objects.get(work_order_number=work_order_number)
    except WorkOrder.DoesNotExist:
        raise LookupError("not found")

    if not isinstance(technician, Person):
        technician = Person.objects.get(pk=technician)

    from_status = work_order.status
    if from_status not in _ASSIGNABLE_FROM and from_status != WorkOrder.STATUS_SCHEDULED:
        raise ValueError(f"cannot assign a work order that is {from_status}")

    linked_request = work_order.requests.select_related("building__campus").first()
    campus = linked_request.building.campus if linked_request else None
    try:
        campus_config = campus_settings_services.get_config(campus)
    except CampusConfig.DoesNotExist:
        campus_config = CampusConfig(min_entry_notice=timedelta(hours=24), repair_order_notice=None)

    if not entry_services.check_window(campus_config, visit_window_start, notice_given_at, repair_order_exception_used):
        raise ValueError("visit window does not satisfy the campus notice rule (FR-004, NFR-08)")

    with db_transaction.atomic():
        if from_status in _ASSIGNABLE_FROM:
            work_order = maintenance_services.transition(
                record=work_order,
                transition_id=_ASSIGNABLE_FROM[from_status],
                to_status=WorkOrder.STATUS_SCHEDULED,
                trigger="supervisor_assigns_and_schedules",
                actor=supervisor,
                now=now,
                expected_version=expected_version,
            )
        else:
            work_order = _reassign_without_status_change(work_order, now, expected_version)

        old_technician = work_order.assigned_technician
        work_order.assigned_technician = technician
        work_order.visit_window_start = visit_window_start
        work_order.visit_window_end = visit_window_end
        work_order.save(update_fields=["assigned_technician", "visit_window_start", "visit_window_end"])

        old_notice = EntryNotice.objects.filter(work_order=work_order, cancelled=False).first()
        if old_notice is not None:
            entry_services.cancel_notice(old_notice, now)
        entry_services.send_notice(work_order, visit_window_start, notice_given_at, repair_order_exception_used, now)

        for linked in work_order.requests.all():
            notifications_services.record_notification(
                recipient=linked.owner,
                event="SCHEDULED",
                tracking_number=linked.tracking_number,
                channel=Notification.CHANNEL_EMAIL,
                content=f"Your request {linked.tracking_number} is scheduled for {work_order.category} on {visit_window_start}.",
                now=now,
            )

        notifications_services.record_notification(
            recipient=technician,
            event="ASSIGNED",
            tracking_number="",
            channel=Notification.CHANNEL_EMAIL,
            content=f"You have been assigned to {work_order.work_order_number}.",
            now=now,
        )
        if old_technician is not None and old_technician.pk != technician.pk:
            notifications_services.record_notification(
                recipient=old_technician,
                event="REASSIGNED",
                tracking_number="",
                channel=Notification.CHANNEL_EMAIL,
                content=f"You have been unassigned from {work_order.work_order_number}.",
                now=now,
            )

    return work_order
