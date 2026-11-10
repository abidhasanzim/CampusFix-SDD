"""Per-campus configuration values (spec.md "Configuration values" table).

NFR-13: every value is set separately per campus; editable only by
authorized administrators (enforced in services.py, not here).
"""
from django.db import models


class CampusConfig(models.Model):
    campus = models.OneToOneField("housing.Campus", on_delete=models.CASCADE, related_name="config")

    urgent_response_limit = models.DurationField(null=True, blank=True)
    hold_limit = models.DurationField(null=True, blank=True)
    min_entry_notice = models.DurationField()  # defaults enforced in services.py; cannot be set below 24h
    repair_order_notice = models.DurationField(null=True, blank=True)
    repeat_repair_count = models.PositiveIntegerField(null=True, blank=True)
    repeat_repair_window = models.DurationField(null=True, blank=True)
    closure_confirmation_period = models.DurationField(null=True, blank=True)
    retention_period = models.DurationField(null=True, blank=True)
    max_photo_bytes = models.PositiveBigIntegerField(null=True, blank=True)
    max_photos_per_request = models.PositiveIntegerField(null=True, blank=True)
    emergency_contacts = models.JSONField(default=dict, blank=True)
    suggestions_enabled = models.BooleanField(default=False)
