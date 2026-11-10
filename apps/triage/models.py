"""Escalation records (FR-015). A uniqueness constraint per overdue period
makes repeated `jobs` runs raise only one escalation (architecture Decision 9;
AC-009, AC-027)."""
from django.db import models

from apps.maintenance.models import MaintenanceRequest, WorkOrder


class Escalation(models.Model):
    KIND_URGENT_SUBMITTED = "URGENT_SUBMITTED"
    KIND_HOLD_OVERDUE = "HOLD_OVERDUE"
    KIND_CHOICES = [
        (KIND_URGENT_SUBMITTED, "Urgent request overdue in Submitted"),
        (KIND_HOLD_OVERDUE, "Work order overdue On Hold"),
    ]

    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    request = models.ForeignKey(MaintenanceRequest, on_delete=models.CASCADE, null=True, blank=True)
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, null=True, blank=True)
    period_start = models.DateTimeField()
    raised_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["kind", "request", "work_order", "period_start"],
                name="one_escalation_per_overdue_period",
            )
        ]
