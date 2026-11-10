"""University SSO identity and staff role records.

Architecture Decision 1: CampusFix stores no passwords. Decision 2: storing
staff roles in CampusFix is a preference (Spec issue 1); a system operator
maintains them.
"""
from django.conf import settings
from django.db import models


class Person(models.Model):
    """One row per university identity, keyed by SSO subject (NFR-10)."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="person")
    sso_subject = models.CharField(max_length=255, unique=True)
    uno_email = models.EmailField()
    display_name = models.CharField(max_length=200)

    def __str__(self):
        return self.display_name


class StaffRole(models.Model):
    SUPERVISOR = "SUPERVISOR"
    TECHNICIAN = "TECHNICIAN"
    ADMINISTRATOR = "ADMINISTRATOR"
    FRONT_DESK = "FRONT_DESK"
    ROLE_CHOICES = [
        (SUPERVISOR, "Facilities Supervisor"),
        (TECHNICIAN, "Maintenance Technician"),
        (ADMINISTRATOR, "Housing Administrator"),
        (FRONT_DESK, "Front-desk / RA staff"),
    ]

    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="staff_roles")
    role_type = models.CharField(max_length=20, choices=ROLE_CHOICES)
    campus = models.ForeignKey("housing.Campus", on_delete=models.PROTECT, null=True, blank=True)
    trade = models.CharField(max_length=50, blank=True)

    class Meta:
        unique_together = ("person", "role_type", "campus")
