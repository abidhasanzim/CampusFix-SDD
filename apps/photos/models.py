"""Photographs, stored on disk outside the web root under random names
(architecture Decision 13) and served only through an access-checked view."""
from django.db import models

from apps.accounts.models import Person
from apps.maintenance.models import MaintenanceRequest, WorkRecord


class Photograph(models.Model):
    owner = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="photographs")
    request = models.ForeignKey(
        MaintenanceRequest, on_delete=models.CASCADE, null=True, blank=True, related_name="photographs"
    )
    work_record = models.ForeignKey(
        WorkRecord, on_delete=models.CASCADE, null=True, blank=True, related_name="photographs"
    )
    stored_name = models.CharField(max_length=255, unique=True)
    content_type = models.CharField(max_length=50)
    byte_size = models.PositiveBigIntegerField()
    linked = models.BooleanField(default=False)  # false while held as an unattached upload
    uploaded_at = models.DateTimeField()
