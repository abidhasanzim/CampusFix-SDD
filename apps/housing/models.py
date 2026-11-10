"""Read-only local copy of campuses, buildings, rooms, and room assignments.

Refreshed from the university housing export (architecture.md Decision 3).
No screen in CampusFix edits these tables (Non-goal 6).
"""
from django.db import models


class Campus(models.Model):
    DODGE = "DODGE"
    SCOTT = "SCOTT"
    CODE_CHOICES = [(DODGE, "Dodge"), (SCOTT, "Scott")]

    code = models.CharField(max_length=10, choices=CODE_CHOICES, unique=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Building(models.Model):
    campus = models.ForeignKey(Campus, on_delete=models.PROTECT, related_name="buildings")
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ("campus", "name")

    def __str__(self):
        return self.name


class Room(models.Model):
    building = models.ForeignKey(Building, on_delete=models.PROTECT, related_name="rooms")
    floor = models.CharField(max_length=20)
    room_number = models.CharField(max_length=20)

    class Meta:
        unique_together = ("building", "room_number")

    def __str__(self):
        return f"{self.building.name} {self.room_number}"


class RoomAssignment(models.Model):
    """A resident's housing assignment, keyed by SSO identity (not FK to
    accounts.Person, so a day-old refresh never blocks on local identity
    bookkeeping — see architecture.md Spec issue 2)."""

    resident_sso_subject = models.CharField(max_length=255, db_index=True)
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="assignments")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
