"""Compute advisory category, priority, and duplicate candidates from a
request's text and location. Stores nothing and has no side effects
(architecture.md section 2; Decision 10: local keyword rules, no AI service).
"""
from __future__ import annotations

from apps.housing.models import Building, Room
from apps.maintenance.models import MaintenanceRequest


def suggest_category_and_priority(description: str, photo_count: int) -> tuple[str, str]:
    """Suggest a maintenance category and priority from free text.

    Success: returns (category, priority) as advisory strings.
    Failure: raises ValueError if `description` is blank; callers must
    treat any raised error as "suggestions unavailable" and continue
    without them (NFR-03, FR-014).
    Spec rule: FR-014 (text and optional photos; keyword rules only,
    Decision 10 — no photo-based suggestion); NFR-03.
    Injected: none; pure function of its arguments.
    """
    raise NotImplementedError


def find_duplicate_candidates(building: Building, room: Room, open_requests: list[MaintenanceRequest]) -> list[MaintenanceRequest]:
    """Flag open requests that may describe the same problem.

    Success: returns the subset of `open_requests` in the same room, or on
    the same floor of `building`, as advisory duplicate candidates.
    Failure: none defined; an empty `open_requests` list returns an empty list.
    Spec rule: FR-014 (same room, floor/building, or equipment — equipment
    matching is out of scope at submission per Spec issue 3); NFR-03
    (never merges automatically).
    Injected: none; pure function of its arguments.
    """
    raise NotImplementedError
