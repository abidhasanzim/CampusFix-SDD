"""Append view and change entries. Entries are never updated or deleted
(NFR-02) — there is accordingly no update/delete function in this module.
"""
from __future__ import annotations

from datetime import datetime

from apps.accounts.models import Person
from apps.audit.models import AuditEntry


def record_view(actor: Person, record_type: str, record_id: str, now: datetime) -> AuditEntry:
    """Append one audit entry for a permitted view of a record.

    Success: returns the created AuditEntry (action="VIEW").
    Failure: none defined; writing the entry is expected to always succeed
    once called (the caller already decided the view is permitted).
    Spec rule: NFR-02 (every view is logged with user, time, action, record).
    Injected: `now` as the recorded time (server clock).
    """
    raise NotImplementedError


def record_change(actor: Person, record_type: str, record_id: str, changed_fields: list[str], now: datetime) -> AuditEntry:
    """Append one audit entry for a change to a record.

    Success: returns the created AuditEntry (action="CHANGE") listing
    `changed_fields`, including suggestion overrides.
    Failure: none defined here.
    Spec rule: NFR-02; FR-006, FR-014 (suggestion overrides are logged).
    Injected: `now` as the recorded time (server clock).
    """
    raise NotImplementedError
