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
from zoneinfo import ZoneInfo

from django.db import connection
from django.db import transaction as db_transaction

from apps.accounts.models import Person
from apps.audit import services as audit_services
from apps.housing.models import Building, Room
from campusfix.exceptions import ConcurrencyError
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

CENTRAL_TIME = ZoneInfo("America/Chicago")

# spec.md "Status lifecycle" table, T1-T15. T1 is (new)->Submitted — handled
# directly by create_request, since transition() only operates on an
# existing record. Self-transitions that don't change status (reassignment
# or a new window while Scheduled, FR-008; entry-preference changes, FR-004)
# are not T-numbered and are not part of this table.
_VALID_TRANSITIONS = {
    (MaintenanceRequest.STATE_SUBMITTED, "T2", MaintenanceRequest.STATE_ACKNOWLEDGED),
    (MaintenanceRequest.STATE_SUBMITTED, "T3", MaintenanceRequest.STATE_CLOSED),
    (MaintenanceRequest.STATE_REOPENED, "T3", MaintenanceRequest.STATE_CLOSED),
    (WorkOrder.STATUS_ACKNOWLEDGED, "T4", WorkOrder.STATUS_SCHEDULED),
    (WorkOrder.STATUS_SCHEDULED, "T5", WorkOrder.STATUS_IN_PROGRESS),
    (WorkOrder.STATUS_SCHEDULED, "T6", WorkOrder.STATUS_NO_ACCESS),
    (WorkOrder.STATUS_NO_ACCESS, "T7", WorkOrder.STATUS_SCHEDULED),
    (WorkOrder.STATUS_IN_PROGRESS, "T8", WorkOrder.STATUS_ON_HOLD),
    (WorkOrder.STATUS_ON_HOLD, "T9", WorkOrder.STATUS_IN_PROGRESS),
    (WorkOrder.STATUS_ON_HOLD, "T10", WorkOrder.STATUS_SCHEDULED),
    (WorkOrder.STATUS_IN_PROGRESS, "T11", WorkOrder.STATUS_COMPLETED),
    (WorkOrder.STATUS_SCHEDULED, "T12", WorkOrder.STATUS_ACKNOWLEDGED),
    (WorkOrder.STATUS_IN_PROGRESS, "T12", WorkOrder.STATUS_ACKNOWLEDGED),
    (WorkOrder.STATUS_ON_HOLD, "T12", WorkOrder.STATUS_ACKNOWLEDGED),
    (WorkOrder.STATUS_NO_ACCESS, "T12", WorkOrder.STATUS_ACKNOWLEDGED),
    (MaintenanceRequest.STATE_COMPLETED, "T13", MaintenanceRequest.STATE_REOPENED),
    (MaintenanceRequest.STATE_REOPENED, "T14", MaintenanceRequest.STATE_ACKNOWLEDGED),
    (MaintenanceRequest.STATE_COMPLETED, "T15", MaintenanceRequest.STATE_CLOSED),
}


def next_tracking_number(year: int) -> str:
    """Draw the next tracking number for a calendar year, e.g. CF-2026-00482.

    Success: returns a unique "CF-<year>-<5-digit sequence>" string.
    Failure: none defined; the underlying sequence cannot collide.
    Spec rule: Domain Model (MaintenanceRequest.trackingNumber format/uniqueness).
    Injected: the per-year PostgreSQL sequence (Decision 11); `year` is
    computed by the caller from the server clock in Central time.
    """
    sequence_name = f"cf_tracking_seq_{year}"
    with connection.cursor() as cursor:
        cursor.execute(f'CREATE SEQUENCE IF NOT EXISTS "{sequence_name}"')
        cursor.execute("SELECT nextval(%s)", [sequence_name])
        (sequence_value,) = cursor.fetchone()
    return f"CF-{year}-{sequence_value:05d}"


def next_work_order_number() -> str:
    """Draw the next work-order number, e.g. WO-1187.

    Success: returns a unique "WO-<n>" string.
    Failure: none defined; the underlying sequence cannot collide.
    Spec rule: Domain Model (WorkOrder.workOrderNumber uniqueness).
    Injected: a dedicated PostgreSQL sequence (Decision 11).
    """
    with connection.cursor() as cursor:
        cursor.execute('CREATE SEQUENCE IF NOT EXISTS "cf_work_order_seq"')
        cursor.execute("SELECT nextval(%s)", ["cf_work_order_seq"])
        (sequence_value,) = cursor.fetchone()
    return f"WO-{sequence_value}"


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
    if not area_type or not exact_location or not description:
        raise ValueError("area_type, exact_location, and description are required")

    year = now.astimezone(CENTRAL_TIME).year
    tracking_number = next_tracking_number(year)

    request = MaintenanceRequest.objects.create(
        tracking_number=tracking_number,
        owner=owner,
        recorded_by=recorded_by,
        building=building,
        room=room,
        area_type=area_type,
        exact_location=exact_location,
        description=description,
        onset=onset,
        resident_urgency=resident_urgency,
        request_state=MaintenanceRequest.STATE_SUBMITTED,
        version=1,
        created_at=now,
        updated_at=now,
    )
    StatusHistoryEntry.objects.create(
        record_type=StatusHistoryEntry.REQUEST,
        record_id=request.id,
        from_status="",
        to_status=MaintenanceRequest.STATE_SUBMITTED,
        transition_id="T1",
        changed_at=now,
    )
    return request


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
    if not requests:
        raise ValueError("at least one request is required to create a work order")

    buildings = {request.building_id for request in requests}
    if len(buildings) > 1:
        raise ValueError("all requests must belong to the same building")

    work_order = WorkOrder.objects.create(
        work_order_number=next_work_order_number(),
        category=category,
        priority=priority,
        status=WorkOrder.STATUS_ACKNOWLEDGED,
        prior_work_order=prior_work_order,
        version=1,
        created_at=now,
        updated_at=now,
    )
    work_order.requests.set(requests)

    StatusHistoryEntry.objects.create(
        record_type=StatusHistoryEntry.WORK_ORDER,
        record_id=work_order.id,
        from_status="",
        to_status=WorkOrder.STATUS_ACKNOWLEDGED,
        transition_id="T14" if prior_work_order is not None else "T2",
        changed_at=now,
    )
    return work_order


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
    model = type(record)
    status_field = "request_state" if isinstance(record, MaintenanceRequest) else "status"
    record_type = StatusHistoryEntry.REQUEST if isinstance(record, MaintenanceRequest) else StatusHistoryEntry.WORK_ORDER

    with db_transaction.atomic():
        locked = model.objects.select_for_update().get(pk=record.pk)

        if locked.version != expected_version:
            raise ConcurrencyError(f"{model.__name__} {locked.pk} has changed since it was read")

        from_status = getattr(locked, status_field)
        if (from_status, transition_id, to_status) not in _VALID_TRANSITIONS:
            raise ValueError(
                f"{from_status} -> {to_status} via {transition_id} is not a valid transition"
            )

        setattr(locked, status_field, to_status)
        locked.version = expected_version + 1
        locked.updated_at = now
        locked.save(update_fields=[status_field, "version", "updated_at"])

        StatusHistoryEntry.objects.create(
            record_type=record_type,
            record_id=locked.id,
            from_status=from_status,
            to_status=to_status,
            transition_id=transition_id,
            changed_at=now,
        )

        audit_services.record_change(actor, model.__name__, str(locked.id), [status_field], now)

    return locked


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
    if not diagnosis or not work_performed or not tested_confirmed:
        raise ValueError("diagnosis, work_performed, and tested_confirmed are required")

    work_record = WorkRecord.objects.create(
        work_order=work_order,
        technician=technician,
        diagnosis=diagnosis,
        work_performed=work_performed,
        labor_hours=labor_hours,
        repair_tested_confirmed=tested_confirmed,
        completed_at=now,
        created_at=now,
    )
    Part.objects.bulk_create(
        Part(work_record=work_record, name=name, quantity=quantity) for name, quantity in parts
    )
    return work_record


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
    return Suggestion.objects.create(
        request=request,
        suggested_category=suggested_category,
        suggested_priority=suggested_priority,
        duplicate_candidate_tracking_numbers=list(duplicate_candidate_tracking_numbers),
    )


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
    if not final_category or not final_priority:
        raise ValueError("final_category and final_priority are required")

    suggestion.final_category = final_category
    suggestion.final_priority = final_priority
    suggestion.reviewer = reviewer
    suggestion.decided_at = now
    suggestion.save(update_fields=["final_category", "final_priority", "reviewer", "decided_at"])
    return suggestion


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
