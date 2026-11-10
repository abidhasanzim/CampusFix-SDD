"""Carry out actions on dispatched work orders: record an entry or failed
access, start, record work, link equipment, complete, hold, transfer, and
clear a hold. Supervisors use the clear-hold and equipment actions too.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from apps.accounts.models import Person
from apps.entry.models import VisitRecord
from apps.maintenance.models import Equipment, HoldRecord, WorkOrder, WorkRecord


def list_my_assignments(technician: Person) -> list[WorkOrder]:
    """Return only the work orders assigned to `technician`.

    Success: returns WorkOrder rows with location, priority, entry
    permission/notice, description, and past repair history preloaded.
    Failure: none defined; a technician with no assignments gets an empty list.
    Spec rule: FR-009; NFR-01, AC-033 (only this technician's own assignments).
    Injected: none.
    """
    raise NotImplementedError


def start_work(technician: Person, work_order_number: str, now: datetime, expected_version: int) -> WorkOrder:
    """Start an assigned Scheduled work order (T5).

    Success: returns the WorkOrder, status="IN_PROGRESS".
    Failure: raises PermissionError if `technician` is not the assigned
    technician; raises ConcurrencyError on a stale `expected_version`.
    Spec rule: FR-010; T5.
    Injected: `now` as the T5 history timestamp.
    """
    raise NotImplementedError


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
    raise NotImplementedError


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
    """
    raise NotImplementedError


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
    raise NotImplementedError


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
