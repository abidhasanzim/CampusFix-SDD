"""Requests, work orders, holds, work records, parts, equipment, and
suggestion records with their final decisions (architecture.md section 2).

Only `maintenance.transition()` in services.py changes `request_state` or
`work_order_status` (architecture Decision 5); these classes hold no
transition logic themselves.
"""
from django.db import models

from apps.accounts.models import Person
from apps.housing.models import Building, Room


class Equipment(models.Model):
    building = models.ForeignKey(Building, on_delete=models.PROTECT, related_name="equipment")
    room = models.ForeignKey(Room, on_delete=models.PROTECT, null=True, blank=True, related_name="equipment")
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=50)


class MaintenanceRequest(models.Model):
    AREA_PRIVATE_BEDROOM = "PRIVATE_BEDROOM"
    AREA_SHARED_SUITE = "SHARED_SUITE"
    AREA_COMMON = "COMMON_AREA"
    AREA_CHOICES = [
        (AREA_PRIVATE_BEDROOM, "Private bedroom"),
        (AREA_SHARED_SUITE, "Shared suite"),
        (AREA_COMMON, "Common area"),
    ]

    URGENCY_LOW = "LOW"
    URGENCY_NORMAL = "NORMAL"
    URGENCY_URGENT = "URGENT"
    URGENCY_CHOICES = [
        (URGENCY_LOW, "Low"),
        (URGENCY_NORMAL, "Normal"),
        (URGENCY_URGENT, "Urgent"),
    ]

    STATE_SUBMITTED = "SUBMITTED"
    STATE_ACKNOWLEDGED = "ACKNOWLEDGED"
    STATE_REOPENED = "REOPENED"
    STATE_COMPLETED = "COMPLETED"
    STATE_CLOSED = "CLOSED"
    STATE_CHOICES = [
        (STATE_SUBMITTED, "Submitted"),
        (STATE_ACKNOWLEDGED, "Acknowledged"),
        (STATE_REOPENED, "Reopened"),
        (STATE_COMPLETED, "Completed"),
        (STATE_CLOSED, "Closed"),
    ]

    tracking_number = models.CharField(max_length=20, unique=True)
    owner = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="owned_requests")
    recorded_by = models.ForeignKey(
        Person, on_delete=models.PROTECT, null=True, blank=True, related_name="recorded_requests"
    )
    building = models.ForeignKey(Building, on_delete=models.PROTECT)
    room = models.ForeignKey(Room, on_delete=models.PROTECT)
    area_type = models.CharField(max_length=20, choices=AREA_CHOICES)
    exact_location = models.CharField(max_length=300)
    description = models.TextField()
    onset = models.DateField(null=True, blank=True)
    resident_urgency = models.CharField(max_length=10, choices=URGENCY_CHOICES, default=URGENCY_NORMAL)
    notes = models.TextField(blank=True)
    request_state = models.CharField(max_length=20, choices=STATE_CHOICES, default=STATE_SUBMITTED)
    closed_reason = models.CharField(max_length=300, blank=True)
    version = models.PositiveIntegerField(default=1)  # optimistic concurrency, Decision 5 / NFR-15
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()


class WorkOrder(models.Model):
    STATUS_ACKNOWLEDGED = "ACKNOWLEDGED"
    STATUS_SCHEDULED = "SCHEDULED"
    STATUS_IN_PROGRESS = "IN_PROGRESS"
    STATUS_ON_HOLD = "ON_HOLD"
    STATUS_NO_ACCESS = "NO_ACCESS"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_CHOICES = [
        (STATUS_ACKNOWLEDGED, "Acknowledged"),
        (STATUS_SCHEDULED, "Scheduled"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_ON_HOLD, "On Hold"),
        (STATUS_NO_ACCESS, "No Access"),
        (STATUS_COMPLETED, "Completed"),
    ]

    PRIORITY_EMERGENCY = "EMERGENCY"
    PRIORITY_HIGH = "HIGH"
    PRIORITY_NORMAL = "NORMAL"
    PRIORITY_LOW = "LOW"
    PRIORITY_CHOICES = [
        (PRIORITY_EMERGENCY, "Emergency"),
        (PRIORITY_HIGH, "High"),
        (PRIORITY_NORMAL, "Normal"),
        (PRIORITY_LOW, "Low"),
    ]

    work_order_number = models.CharField(max_length=20, unique=True)
    requests = models.ManyToManyField(MaintenanceRequest, related_name="work_orders")
    category = models.CharField(max_length=50)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES)
    assigned_technician = models.ForeignKey(
        Person, on_delete=models.PROTECT, null=True, blank=True, related_name="assigned_work_orders"
    )
    visit_window_start = models.DateTimeField(null=True, blank=True)
    visit_window_end = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACKNOWLEDGED)
    equipment = models.ForeignKey(Equipment, on_delete=models.PROTECT, null=True, blank=True)
    prior_work_order = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True)
    version = models.PositiveIntegerField(default=1)  # optimistic concurrency, Decision 5 / NFR-15
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()


class StatusHistoryEntry(models.Model):
    """One row per transition in the T1-T15 table (status lifecycle)."""

    REQUEST = "REQUEST"
    WORK_ORDER = "WORK_ORDER"
    RECORD_TYPE_CHOICES = [(REQUEST, "Request"), (WORK_ORDER, "Work Order")]

    record_type = models.CharField(max_length=12, choices=RECORD_TYPE_CHOICES)
    record_id = models.PositiveIntegerField()
    from_status = models.CharField(max_length=20)
    to_status = models.CharField(max_length=20)
    transition_id = models.CharField(max_length=5)  # e.g. "T1".."T15"
    changed_at = models.DateTimeField()


class Part(models.Model):
    work_record = models.ForeignKey("WorkRecord", on_delete=models.CASCADE, related_name="parts")
    name = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)


class WorkRecord(models.Model):
    work_order = models.ForeignKey(WorkOrder, on_delete=models.PROTECT, related_name="work_records")
    technician = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="work_records")
    diagnosis = models.TextField()
    work_performed = models.TextField()
    labor_hours = models.DecimalField(max_digits=6, decimal_places=2)
    repair_tested_confirmed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField()


class HoldRecord(models.Model):
    REASON_WAITING_PART = "WAITING_FOR_PART"
    REASON_WAITING_APPROVAL = "WAITING_FOR_APPROVAL"
    REASON_OTHER = "OTHER"
    REASON_CHOICES = [
        (REASON_WAITING_PART, "Waiting for part"),
        (REASON_WAITING_APPROVAL, "Waiting for approval"),
        (REASON_OTHER, "Other"),
    ]

    work_order = models.ForeignKey(WorkOrder, on_delete=models.PROTECT, related_name="hold_records")
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    part_name = models.CharField(max_length=200, blank=True)
    next_action = models.TextField()
    started_at = models.DateTimeField()
    cleared_at = models.DateTimeField(null=True, blank=True)
    cleared_by = models.ForeignKey(
        Person, on_delete=models.PROTECT, null=True, blank=True, related_name="cleared_holds"
    )


class Suggestion(models.Model):
    """A Project 2 refinement: advisory output plus the supervisor's final
    decision (FR-014). `suggestions` computes the advisory values; this
    table is owned and persisted by `maintenance`."""

    request = models.OneToOneField(MaintenanceRequest, on_delete=models.CASCADE, related_name="suggestion")
    suggested_category = models.CharField(max_length=50, blank=True)
    suggested_priority = models.CharField(max_length=10, blank=True)
    duplicate_candidate_tracking_numbers = models.JSONField(default=list, blank=True)
    final_category = models.CharField(max_length=50, blank=True)
    final_priority = models.CharField(max_length=10, blank=True)
    reviewer = models.ForeignKey(
        Person, on_delete=models.PROTECT, null=True, blank=True, related_name="triage_decisions"
    )
    decided_at = models.DateTimeField(null=True, blank=True)
