"""Run time-based checks on a schedule: urgent and hold escalations,
automatic closure, retention, email retry, and housing refresh. One
management command, run by cron every 5 minutes (architecture Decision 9);
not exposed over HTTP.
"""
from __future__ import annotations

from datetime import datetime


def run_scheduled_checks(now: datetime) -> dict:
    """Run every periodic check once: escalations (`triage`), automatic
    closure (`intake`), photo/entry retention (`photos`, `entry`), and
    pending-email retry (`notifications`).

    Success: returns a dict summarizing what each sub-check did (counts).
    Failure: none defined; each sub-check's own failure mode applies, and
    one sub-check failing does not prevent the others from running.
    Spec rule: FR-015, FR-020; NFR-07, NFR-16; Decision 9 (uniqueness
    constraints make repeated runs raise only one escalation).
    Injected: `now`, passed unchanged to every sub-check so one run uses one clock reading.
    """
    raise NotImplementedError


def refresh_housing(now: datetime) -> dict:
    """Pull the nightly university housing export and apply it
    (delegates the write to `housing.refresh_from_export`).

    Success: returns the summary dict from `housing.refresh_from_export`.
    Failure: raises ValueError if the export cannot be read; the existing
    local copy is left unchanged (Known limits: can be up to a day old).
    Spec rule: Domain Model (external systems); Decision 3.
    Injected: `now`; the university housing export (format TBD, C7).
    """
    raise NotImplementedError
