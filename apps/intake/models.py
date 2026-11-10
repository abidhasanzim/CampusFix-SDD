"""Server-side drafts (architecture Decision 14; NFR-11, AC-039)."""
from django.db import models

from apps.accounts.models import Person


class Draft(models.Model):
    user = models.OneToOneField(Person, on_delete=models.CASCADE, related_name="request_draft")
    form_data = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField()
