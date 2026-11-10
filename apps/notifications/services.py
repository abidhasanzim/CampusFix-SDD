"""Record each notification in the same transaction as its event, and
deliver it by UNO email and the activity feed, retrying failed email
(architecture Decision 6; FR-002; NFR-16).
"""
from __future__ import annotations

from datetime import datetime

from apps.accounts.models import Person
from apps.notifications.models import Notification


def record_notification(recipient: Person, event: str, tracking_number: str, channel: str, content: str, now: datetime) -> Notification:
    """Write one notification row in the caller's open database transaction.

    Success: returns the created Notification with status="PENDING"; the
    row is visible to the activity feed at commit.
    Failure: none defined; the caller is responsible for calling this only
    after the event it reports has itself been saved (FR-002).
    Spec rule: FR-002 (sent only after saving the event; one message per
    owner, naming only that owner's tracking number).
    Injected: `now` as created_at.
    """
    raise NotImplementedError


def send_pending(now: datetime) -> int:
    """Claim pending notification rows with `SELECT ... FOR UPDATE SKIP
    LOCKED` and attempt delivery by UNO email.

    Success: returns the count of notifications sent; each row's
    status becomes "SENT" and sent_at is stamped.
    Failure: a row stays "PENDING" (not an exception) if UNO email is
    unavailable; it is retried on the next call, never sent twice
    (SKIP LOCKED prevents a concurrent sender from claiming the same row).
    Spec rule: NFR-16 (notifications are not lost; retries never duplicate);
    AC-047.
    Injected: `now` as sent_at; the UNO SMTP relay (C6; console backend in dev).
    """
    raise NotImplementedError


def list_my_notifications(person: Person) -> list[Notification]:
    """Return the activity feed for one person.

    Success: returns Notification rows addressed to `person`, newest first.
    Failure: none defined.
    Spec rule: FR-002 (activity feed); FR-003 (track request's own feed).
    Injected: none.
    """
    raise NotImplementedError
