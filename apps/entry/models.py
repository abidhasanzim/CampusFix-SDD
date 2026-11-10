"""Entry preferences, notices, and visit records (FR-004; NFR-08, NFR-17)."""
from django.db import models

from apps.accounts.models import Person
from apps.maintenance.models import MaintenanceRequest, WorkOrder


class EntryPreference(models.Model):
    PRESENT = "PRESENT"
    ALLOW_WHILE_AWAY = "ALLOW_ENTRY_WHILE_AWAY"
    PREFERRED_SLOTS = "PREFERRED_TIME_SLOTS"
    PREFERENCE_CHOICES = [
        (PRESENT, "Present"),
        (ALLOW_WHILE_AWAY, "Allow entry while away"),
        (PREFERRED_SLOTS, "Preferred time slots"),
    ]

    request = models.OneToOneField(MaintenanceRequest, on_delete=models.CASCADE, related_name="entry_preference")
    preference = models.CharField(max_length=30, choices=PREFERENCE_CHOICES)
    updated_at = models.DateTimeField()


class PreferredTimeSlot(models.Model):
    entry_preference = models.ForeignKey(EntryPreference, on_delete=models.CASCADE, related_name="time_slots")
    day_of_week = models.PositiveSmallIntegerField()
    start_time = models.TimeField()
    end_time = models.TimeField()


class EntryNotice(models.Model):
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, related_name="entry_notices")
    visit_window_start = models.DateTimeField()
    sent_at = models.DateTimeField()
    cancelled = models.BooleanField(default=False)
    repair_order_exception_used = models.BooleanField(default=False)


class VisitRecord(models.Model):
    OUTCOME_ENTERED = "ENTERED"
    OUTCOME_NO_ACCESS = "NO_ACCESS"
    OUTCOME_CHOICES = [(OUTCOME_ENTERED, "Entered"), (OUTCOME_NO_ACCESS, "No Access")]

    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, related_name="visit_records")
    person = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="visits_performed")
    occurred_at = models.DateTimeField()
    resident_present = models.BooleanField()
    knock_and_announce_confirmed = models.BooleanField(default=False)
    outcome = models.CharField(max_length=15, choices=OUTCOME_CHOICES)
