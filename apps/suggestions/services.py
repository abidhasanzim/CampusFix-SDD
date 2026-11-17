"""Compute advisory category, priority, and duplicate candidates from a
request's text and location. Stores nothing and has no side effects
(architecture.md section 2; Decision 10: local keyword rules, no AI service).
"""
from __future__ import annotations

from apps.housing.models import Building, Room
from apps.maintenance.models import MaintenanceRequest, WorkOrder

# Decision 10: local keyword rules only, no AI service and no photo-based
# suggestion (`photo_count` is accepted per the contract but unused).
_CATEGORY_KEYWORDS = [
    ("PLUMBING", ("leak", "faucet", "toilet", "drain", "pipe", "sink", "water", "clog")),
    ("ELECTRICAL", ("outlet", "electrical", "wire", "wiring", "breaker", "power", "spark")),
    ("HVAC", ("heat", "furnace", "thermostat", "hvac", "vent", "air condition", "radiator")),
    ("CARPENTRY", ("door", "window frame", "cabinet", "drawer", "wood", "hinge")),
    ("LOCKS_GLASS", ("lock", "key", "glass", "broken window", "deadbolt")),
    ("APPLIANCE", ("fridge", "refrigerator", "stove", "oven", "dishwasher", "microwave", "appliance", "washer", "dryer")),
]

_EMERGENCY_KEYWORDS = ("flood", "fire", "smoke", "gas smell", "sparking", "burst", "no heat")
_HIGH_KEYWORDS = ("no power", "no water", "no hot water", "security", "broken lock")
_LOW_KEYWORDS = ("cosmetic", "scratch", "scuff", "paint")


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
    if not description or not description.strip():
        raise ValueError("description is required to suggest a category and priority")

    text = description.lower()

    category = "OTHER"
    for name, keywords in _CATEGORY_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            category = name
            break

    if any(keyword in text for keyword in _EMERGENCY_KEYWORDS):
        priority = WorkOrder.PRIORITY_EMERGENCY
    elif any(keyword in text for keyword in _HIGH_KEYWORDS):
        priority = WorkOrder.PRIORITY_HIGH
    elif any(keyword in text for keyword in _LOW_KEYWORDS):
        priority = WorkOrder.PRIORITY_LOW
    else:
        priority = WorkOrder.PRIORITY_NORMAL

    return category, priority


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
    return [
        candidate
        for candidate in open_requests
        if candidate.building_id == building.id
        and (candidate.room_id == room.id or candidate.room.floor == room.floor)
    ]
