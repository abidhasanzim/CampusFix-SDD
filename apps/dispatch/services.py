"""Assign and reassign a technician together with a visit window."""
from __future__ import annotations

from datetime import datetime

from apps.accounts.models import Person
from apps.maintenance.models import WorkOrder


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
    raise NotImplementedError
