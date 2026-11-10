"""Own the records for requests, work orders, holds, work, parts, equipment,
and suggestions with their final decisions. `transition()` is the only
function anywhere in CampusFix that changes `request_state` or
`work_order_status` (architecture.md Overview, Decision 5).

Every function raises NotImplementedError; this module writes no business
logic in Project 2.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from apps.accounts.models import Person
from apps.housing.models import Building, Room
from apps.maintenance.models import (
    Equipment,
    HoldRecord,
    MaintenanceRequest,
    Part,
    StatusHistoryEntry,
    Suggestion,
    WorkOrder,
    WorkRecord,
)


def next_tracking_number(year: int) -> str:
    """Draw the next tracking number for a calendar year, e.g. CF-2026-00482.

    Success: returns a unique "CF-<year>-<5-digit sequence>" string.
    Failure: none defined; the underlying sequence cannot collide.
    Spec rule: Domain Model (MaintenanceRequest.trackingNumber format/uniqueness).
    Injected: the per-year PostgreSQL sequence (Decision 11); `year` is
    computed by the caller from the server clock in Central time.
    """
    raise NotImplementedError


def next_work_order_number() -> str:
    """Draw the next work-order number, e.g. WO-1187.

    Success: returns a unique "WO-<n>" string.
    Failure: none defined; the underlying sequence cannot collide.
    Spec rule: Domain Model (WorkOrder.workOrderNumber uniqueness).
    Injected: a dedicated PostgreSQL sequence (Decision 11).
    """
    raise NotImplementedError


def create_request(
    owner: Person,
    recorded_by: Person | None,
    building: Building,
    room: Room,
    area_type: str,
    exact_location: str,
    description: str,
    onset,
    resident_urgency: str,
    now: datetime,
) -> MaintenanceRequest:
    """Create one request in `Submitted` (transition T1) with a fresh
    tracking number, and write its first status-history row.

    Success: returns the created MaintenanceRequest with request_state="SUBMITTED".
    Failure: raises ValueError if a required field is missing or `owner`
    has no current room assignment (checked by the caller, `intake`).
    Spec rule: FR-001 (resident), FR-019 (recordedBy set by staff); T1.
    Injected: `now` as created_at/updated_at and the T1 history timestamp.
    """
    raise NotImplementedError


def create_work_order(
    requests: list[MaintenanceRequest],
    category: str,
    priority: str,
    prior_work_order: WorkOrder | None,
    now: datetime,
) -> WorkOrder:
    """Create one actionable work order linked to one or more acknowledged
    requests, unassigned (transition T2 or T14).

    Success: returns the created WorkOrder, status="ACKNOWLEDGED", linked
    to every request in `requests`.
    Failure: raises ValueError if `requests` is empty or the requests do
    not all belong to the same building (FR-007 merge restriction).
    Spec rule: FR-006, FR-007, FR-014 (reopened requests link to the
    predecessor via `prior_work_order`); T2, T14.
    Injected: `now` as created_at/updated_at and the T2/T14 history timestamp.
    """
    raise NotImplementedError


def link_request_to_work_order(request: MaintenanceRequest, work_order: WorkOrder, now: datetime) -> WorkOrder:
    """Attach one more submitted request to an existing active work order
    without creating a second work order or visit.

    Success: returns `work_order` with `request` added to its linked requests.
    Failure: raises ValueError if the requests are not in the same building,
    or if `work_order` is already `Completed`.
    Spec rule: FR-007 (link newly submitted reports to an existing work order).
    Injected: `now` for the request's T2 history row.
    """
    raise NotImplementedError


def transition(
    record: MaintenanceRequest | WorkOrder,
    transition_id: str,
    to_status: str,
    trigger: str,
    actor: Person,
    now: datetime,
    expected_version: int,
) -> MaintenanceRequest | WorkOrder:
    """Apply one row of the T1-T15 transition table to a request or work
    order, writing its status history and an audit entry in the same
    database transaction (architecture Decision 5; NFR-15).

    Success: returns the record with its status updated and `version`
    incremented by one.
    Failure: raises ValueError if (`record.status`, `transition_id`,
    `to_status`) is not one of T1-T15; raises ConcurrencyError if
    `record.version != expected_version` (another user changed it first).
    Spec rule: Status lifecycle ("the system MUST reject other state
    changes"); NFR-15 (one transaction; exactly one concurrent writer wins).
    Injected: `now` as the status-history/audit timestamp; row locks via
    `SELECT ... FOR UPDATE` (work order first, then linked requests by id).
    """
    raise NotImplementedError


def record_work(
    work_order: WorkOrder,
    technician: Person,
    diagnosis: str,
    work_performed: str,
    labor_hours: Decimal,
    parts: list[tuple[str, int]],
    tested_confirmed: bool,
    now: datetime,
) -> WorkRecord:
    """Save a technician's work record for a work order (does not itself
    change status; callers pair this with `transition(..., "T11", ...)`).

    Success: returns the created WorkRecord with its Part rows.
    Failure: raises ValueError if `diagnosis`, `work_performed`, or
    `tested_confirmed` is missing when the caller intends completion.
    Spec rule: FR-010 (diagnosis, work performed, labor time, parts,
    repair-tested confirmation required to complete).
    Injected: `now` as created_at/completed_at.
    """
    raise NotImplementedError


def create_hold_record(
    work_order: WorkOrder,
    technician: Person,
    reason: str,
    part_name: str,
    next_action: str,
    now: datetime,
) -> HoldRecord:
    """Open a hold record for a work order (paired with
    `transition(..., "T8", "ON_HOLD", ...)` by the caller).

    Success: returns the created HoldRecord with `cleared_at` unset.
    Failure: raises ValueError if `reason == "WAITING_FOR_PART"` and
    `part_name` is blank.
    Spec rule: FR-011 (reason and expected next action required).
    Injected: `now` as started_at.
    """
    raise NotImplementedError


def clear_hold_record(hold_record: HoldRecord, cleared_by: Person, now: datetime) -> HoldRecord:
    """Mark a hold's blocker cleared, preserving who cleared it and when.

    Success: returns `hold_record` with `cleared_at`/`cleared_by` set.
    Failure: raises ValueError if `hold_record` is already cleared.
    Spec rule: FR-016 (preserves who cleared the hold, when, its reason).
    Injected: `now` as cleared_at.
    """
    raise NotImplementedError


def save_suggestion(
    request: MaintenanceRequest,
    suggested_category: str,
    suggested_priority: str,
    duplicate_candidate_tracking_numbers: list[str],
    now: datetime,
) -> Suggestion:
    """Persist the advisory output computed by `suggestions`, labeled as
    suggested (not final).

    Success: returns the created Suggestion row with final_* fields unset.
    Failure: none defined; called at most once per request, at submission.
    Spec rule: FR-014 (suggestions never set the final result); NFR-03.
    Injected: `now` for record keeping only (no decision time yet).
    """
    raise NotImplementedError


def confirm_triage_decision(
    suggestion: Suggestion, final_category: str, final_priority: str, reviewer: Person, now: datetime
) -> Suggestion:
    """Record the supervisor's final category/priority decision, keeping
    the original suggestion for comparison.

    Success: returns `suggestion` with final_category, final_priority,
    reviewer, and decided_at set.
    Failure: raises ValueError if `final_category` or `final_priority` is blank.
    Spec rule: FR-006 (category and priority both required); FR-014
    (suggestions, decisions, reviewer identity, and time are logged).
    Injected: `now` as decided_at.
    """
    raise NotImplementedError


def get_status_history(record_type: str, record_id: int) -> list[StatusHistoryEntry]:
    """Return the full timestamped status history for a request or work order.

    Success: returns StatusHistoryEntry rows ordered by `changed_at`.
    Failure: none defined; an unknown id returns an empty list.
    Spec rule: FR-003 (full timestamped status history).
    Injected: none.
    """
    raise NotImplementedError


def get_equipment_work_history(equipment: Equipment) -> list[WorkOrder]:
    """Return every work order linked to one piece of equipment.

    Success: returns WorkOrder rows ordered by creation time.
    Failure: none defined.
    Spec rule: FR-013 (equipment work history for replacement candidates).
    Injected: none.
    """
    raise NotImplementedError
