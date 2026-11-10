"""Append-only view/change log (NFR-02). Rows are never updated or deleted
through CampusFix; there is no update/delete entry point in services.py."""
from django.db import models


class AuditEntry(models.Model):
    VIEW = "VIEW"
    CHANGE = "CHANGE"
    ACTION_CHOICES = [(VIEW, "View"), (CHANGE, "Change")]

    actor_sso_subject = models.CharField(max_length=255)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    record_type = models.CharField(max_length=100)
    record_id = models.CharField(max_length=100)
    changed_fields = models.JSONField(default=list, blank=True)
    occurred_at = models.DateTimeField()

    class Meta:
        indexes = [models.Index(fields=["record_type", "record_id"])]
