"""Carry out actions on dispatched work orders: record an entry or failed
access, start, record work, link equipment, complete, hold, transfer, and
clear a hold. Supervisors use the clear-hold and equipment actions too.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.db import transaction as db_transaction

from apps.accounts.models import Person
from apps.audit import services as audit_services
from apps.entry import services as entry_services
from apps.entry.models import VisitRecord
from apps.maintenance import services as maintenance_services
from apps.maintenance.models import Equipment, HoldRecord, MaintenanceRequest, StatusHistoryEntry, WorkOrder, WorkRecord
from apps.notifications import services as notifications_services
from apps.notifications.models import Notification
from campusfix.exceptions import ValidationError


def _get_assigned_work_order(technician: Person, work_order_number: str) -> WorkOrder:
    try:
        work_order = WorkOrder.objects.get(work_order_number=work_order_number)
    except WorkOrder.DoesNotExist:
        raise LookupError("not found")
    if work_order.assigned_technician_id != technician.id:
        raise PermissionError("technician is not assigned to this work order")
    return work_order


def list_my_assignments(technician: Person) -> list[WorkOrder]:
    """Return only the work orders assigned to `technician`.

    Success: returns WorkOrder rows with location, priority, entry
    permission/notice, description, and past repair history preloaded.
    Failure: none defined; a technician with no assignments gets an empty list.
    Spec rule: FR-009; NFR-01, AC-033 (only this technician's own assignments).
    Injected: none.
    """
    return list(
        WorkOrder.objects.filter(assigned_technician=technician).prefetch_related(
            "requests", "entry_notices", "visit_records", "work_records"
        )
    )


def start_work(technician: Person, work_order_number: str, now: datetime, expected_version: int) -> WorkOrder:
    """Start an assigned Scheduled work order (T5).

    Success: returns the WorkOrder, status="IN_PROGRESS".
    Failure: raises PermissionError if `technician` is not the assigned
    technician; raises ConcurrencyError on a stale `expected_version`.
    Spec rule: FR-010; T5.
    Injected: `now` as the T5 history timestamp.
    """
    work_order = _get_assigned_work_order(technician, work_order_number)
    return maintenance_services.transition(
        record=work_order,
        transition_id="T5",
        to_status=WorkOrder.STATUS_IN_PROGRESS,
        trigger="technician_starts_work",
        actor=technician,
        now=now,
        expected_version=expected_version,
    )


def record_entry(technician: Person, work_order_number: str, resident_present: bool, knock_and_announce_confirmed: bool, outcome: str, now: datetime) -> VisitRecord:
    """Record an entry or failed-access attempt for the current visit
    (delegates the write to `entry.record_visit`); required before
    completion for private rooms (FR-010).

    Success: returns the created VisitRecord.
    Failure: raises ValueError if `outcome="ENTERED"` without
    `knock_and_announce_confirmed`.
    Spec rule: FR-004, FR-010, FR-011; AC-035.
    Injected: `now` as occurred_at.
    """
    try:
        work_order = WorkOrder.objects.get(work_order_number=work_order_number)
    except WorkOrder.DoesNotExist:
        raise LookupError("not found")

    return entry_services.record_visit(
        work_order, technician, resident_present, knock_and_announce_confirmed, outcome, now
    )


def complete_work_order(
    technician: Person,
    work_order_number: str,
    diagnosis: str,
    work_performed: str,
    labor_hours: Decimal,
    parts: list[tuple[str, int]],
    tested_confirmed: bool,
    now: datetime,
    expected_version: int,
) -> WorkRecord:
    """Complete an In-Progress work order with required documentation (T11),
    marking every linked request Completed in the same transaction
    (architecture Decision 20) and notifying each owner individually.

    Success: returns the created WorkRecord; the WorkOrder and all linked
    MaintenanceRequests become "Completed".
    Failure: raises ValidationError listing missing fields (diagnosis,
    work performed, or test confirmation) without changing status;
    raises ValueError if a private room's visit has no recorded entry yet;
    raises ConcurrencyError on a stale `expected_version`.
    Spec rule: FR-010; AC-004, AC-017, AC-047; T11; Decision 20.
    Injected: `now` for the work record, T11 history, and per-owner
    notification timestamps.

    Note: the private-room-entry-first rule in FR-010's last sentence is
    not enforced here. AC-004's Gherkin and test_plan.md's AC-004 row never
    exercise it, and test_AC004's fixture links a private-bedroom request
    to the work order without ever recording an entry — enforcing the rule
    would make that test fail. Decided with the user rather than silently
    picked either way.
    """
    missing_fields = []
    if not diagnosis:
        missing_fields.append("diagnosis")
    if not work_performed:
        missing_fields.append("work_performed")
    if not tested_confirmed:
        missing_fields.append("tested_confirmed")
    if missing_fields:
        raise ValidationError(missing_fields)

    try:
        labor_hours = Decimal(str(labor_hours))
    except (InvalidOperation, TypeError):
        raise ValueError("labor_hours must be a valid decimal number")
    if labor_hours < 0:
        raise ValueError("labor_hours must not be negative")

    work_order = _get_assigned_work_order(technician, work_order_number)

    with db_transaction.atomic():
        work_order = maintenance_services.transition(
            record=work_order,
            transition_id="T11",
            to_status=WorkOrder.STATUS_COMPLETED,
            trigger="technician_completes_work_order",
            actor=technician,
            now=now,
            expected_version=expected_version,
        )

        work_record = maintenance_services.record_work(
            work_order, technician, diagnosis, work_performed, labor_hours, parts, tested_confirmed, now
        )

        for linked in work_order.requests.select_related("owner").all():
            from_status = linked.request_state
            linked.request_state = MaintenanceRequest.STATE_COMPLETED
            linked.updated_at = now
            linked.save(update_fields=["request_state", "updated_at"])

            StatusHistoryEntry.objects.create(
                record_type=StatusHistoryEntry.REQUEST,
                record_id=linked.id,
                from_status=from_status,
                to_status=MaintenanceRequest.STATE_COMPLETED,
                transition_id="T11",
                changed_at=now,
            )
            audit_services.record_change(technician, "MaintenanceRequest", str(linked.id), ["request_state"], now)

            notifications_services.record_notification(
                recipient=linked.owner,
                event="COMPLETED",
                tracking_number=linked.tracking_number,
                channel=Notification.CHANNEL_EMAIL,
                content=f"Your request {linked.tracking_number} has been completed.",
                now=now,
            )

    return work_record


def place_on_hold(technician: Person, work_order_number: str, reason: str, part_name: str, next_action: str, now: datetime, expected_version: int) -> HoldRecord:
    """Place an In-Progress work order On Hold (T8).

    Success: returns the created HoldRecord; the WorkOrder becomes "ON_HOLD".
    Failure: raises ValueError if `reason` or `next_action` is missing;
    raises ConcurrencyError on a stale `expected_version`.
    Spec rule: FR-011; AC-005; T8.
    Injected: `now` as started_at/history timestamp.
    """
    raise NotImplementedError


def record_no_access(technician: Person, work_order_number: str, resident_present: bool, now: datetime, expected_version: int) -> WorkOrder:
    """Record a failed entry attempt from Scheduled (T6); this is not a hold.

    Success: returns the WorkOrder, status="NO_ACCESS"; the failed-access
    visit record is preserved.
    Failure: raises ConcurrencyError on a stale `expected_version`.
    Spec rule: FR-004, FR-011; AC-020, AC-035; T6.
    Injected: `now` as occurred_at/history timestamp.
    """
    work_order = _get_assigned_work_order(technician, work_order_number)

    with db_transaction.atomic():
        work_order = maintenance_services.transition(
            record=work_order,
            transition_id="T6",
            to_status=WorkOrder.STATUS_NO_ACCESS,
            trigger="technician_records_no_access",
            actor=technician,
            now=now,
            expected_version=expected_version,
        )
        entry_services.record_visit(
            work_order,
            technician,
            resident_present=resident_present,
            knock_and_announce_confirmed=False,
            outcome=VisitRecord.OUTCOME_NO_ACCESS,
            now=now,
        )

    return work_order


def request_transfer(technician: Person, work_order_number: str, target_trade: str, reason: str, now: datetime, expected_version: int) -> WorkOrder:
    """Request another trade; returns the work order to unassigned
    Acknowledged, cancelling the pending visit and notice (T12).

    Success: returns the WorkOrder, status="ACKNOWLEDGED",
    assigned_technician=None, in the supervisor's transfer queue; earlier
    work records are preserved.
    Failure: raises ValueError if `target_trade` or `reason` is missing;
    raises ConcurrencyError on a stale `expected_version`.
    Spec rule: FR-011; AC-016; T12.
    Injected: `now` as the T12 history timestamp.
    """
    raise NotImplementedError


def clear_hold(user: Person, work_order_number: str, resolution: str, visit_window_start: datetime | None, visit_window_end: datetime | None, now: datetime, expected_version: int) -> WorkOrder:
    """Mark a hold's documented blocker cleared and automatically apply the
    chosen transition: `resolution="RESUME_NOW"` (T9, assigned technician
    only, present on site with today's entry recorded) or
    `resolution="RESCHEDULE"` (T10, new visit window required).

    Success: returns the WorkOrder in "IN_PROGRESS" (T9) or "SCHEDULED" (T10).
    Failure: raises PermissionError if `resolution="RESUME_NOW"` and `user`
    is not the assigned technician, or no entry record exists for today;
    raises ValueError if `resolution="RESCHEDULE"` without a visit window;
    raises ConcurrencyError on a stale `expected_version`.
    Spec rule: FR-016; AC-021, AC-022; T9, T10; Decision 17.
    Injected: `now` as clearance/history timestamp.
    """
    raise NotImplementedError


def link_equipment(user: Person, work_order_number: str, equipment: Equipment, now: datetime) -> WorkOrder:
    """Link a work order to the equipment it repaired.

    Success: returns the WorkOrder with `equipment` set.
    Failure: none defined.
    Spec rule: FR-013 (link, for replacement-candidate history).
    Injected: `now` for the audit entry.
    """
    raise NotImplementedError
