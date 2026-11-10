"""Store each campus's configuration values, editable only by authorized
administrators (NFR-13). No function here implements logic yet.
"""
from __future__ import annotations

from datetime import datetime

from apps.accounts.models import Person
from apps.campus_settings.models import CampusConfig
from apps.housing.models import Campus


def get_config(campus: Campus) -> CampusConfig:
    """Return the configuration row for one campus.

    Success: returns the campus's CampusConfig.
    Failure: raises CampusConfig.DoesNotExist if the campus has never been configured.
    Spec rule: Configuration values table; NFR-13 (separate per campus).
    Injected: none.
    """
    raise NotImplementedError


def update_config(administrator: Person, campus: Campus, changes: dict, now: datetime) -> CampusConfig:
    """Update one or more configuration values for a single campus.

    Success: returns the updated CampusConfig; changing one campus's value
    never changes the other campus's row.
    Failure: raises PermissionError if `administrator` is not authorized;
    raises ValueError if a change would set `min_entry_notice` below 24h.
    Spec rule: NFR-13; Decision 15 (minEntryNotice floor; required-before-launch values).
    Injected: `now` for the audit trail of the change (via `audit`).
    """
    raise NotImplementedError
