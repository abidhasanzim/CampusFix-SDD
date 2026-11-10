"""One row per notification, written in the same transaction as its event
(architecture Decision 6). The activity feed reads these same rows."""
from django.db import models

from apps.accounts.models import Person


class Notification(models.Model):
    CHANNEL_EMAIL = "EMAIL"
    CHANNEL_FEED = "FEED"
    CHANNEL_CHOICES = [(CHANNEL_EMAIL, "UNO email"), (CHANNEL_FEED, "Activity feed")]

    STATUS_PENDING = "PENDING"
    STATUS_SENT = "SENT"
    STATUS_CHOICES = [(STATUS_PENDING, "Pending"), (STATUS_SENT, "Sent")]

    recipient = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="notifications")
    event = models.CharField(max_length=50)
    tracking_number = models.CharField(max_length=20, blank=True)
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    content = models.TextField()
    created_at = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
