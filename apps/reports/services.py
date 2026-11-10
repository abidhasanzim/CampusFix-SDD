"""Compute administrator reports and replacement candidates from stored
history (architecture Decision 18: on-demand SQL, no summary store).
"""
from __future__ import annotations

from datetime import date, datetime

from apps.accounts.models import Person
from apps.housing.models import Building, Campus


def get_operational_report(administrator: Person, campus: Campus, period_start: date, period_end: date, building: Building | None, category: str | None) -> dict:
    """Compute open/completed work-order counts, technician workload, and
    submission-to-acknowledgment/completion times, filtered by period,
    building, and category.

    Success: returns a dict of counts/workloads/averages; no resident
    names, entry records, or photographs appear in the result.
    Failure: raises PermissionError if `administrator` holds no
    administrator role.
    Spec rule: FR-012; NFR-01 (administrators see aggregates only); AC-011.
    Injected: none; computed live from existing tables (Decision 18).
    """
    raise NotImplementedError


def get_replacement_candidates(administrator: Person, campus: Campus, now: datetime) -> list[dict]:
    """List equipment with at least `repeatRepairCount` work orders within
    `repeatRepairWindow` for the campus, with accessible repair history.

    Success: returns a list of {equipment, location, repair_count,
    work_history} dicts.
    Failure: raises ConfigurationError (a dict stating "rule not
    configured", not an exception that hides the screen) if
    `repeatRepairCount`/`repeatRepairWindow` is unset for the campus — no
    equipment is flagged in that case.
    Spec rule: FR-013 (states when the rule is not configured rather than
    guessing); AC-025, AC-026.
    Injected: `now` as the reference point for the repair window.
    """
    raise NotImplementedError
