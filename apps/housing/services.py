"""Keep a read-only local copy of campuses, buildings, rooms, and current
room assignments, refreshed from the university export (architecture
Decision 3). No function here writes a status; none implement logic yet.
"""
from __future__ import annotations

from datetime import date, datetime

from apps.housing.models import Building, Room, RoomAssignment


def get_current_assignment(sso_subject: str, as_of_date: date) -> RoomAssignment | None:
    """Return the resident's current room assignment, if any, as of a date.

    Success: returns the RoomAssignment covering `as_of_date`, or None.
    Failure: none; absence of a current assignment is a normal result, not
    an error (callers decide what that means, e.g. FR-001 refusal).
    Spec rule: FR-001, FR-019 (building/room are read-only from housing
    data); NFR-14 (a user whose assignment ended cannot submit new requests).
    Injected: none; this reads the local copy, not the university system.
    """
    raise NotImplementedError


def get_room(building: Building, room_number: str) -> Room:
    """Look up a room by building and room number.

    Success: returns the matching Room.
    Failure: raises Room.DoesNotExist if no such room exists.
    Spec rule: FR-001, FR-019 (building/room come from housing data).
    Injected: none.
    """
    raise NotImplementedError


def refresh_from_export(export_rows: list[dict], now: datetime) -> dict:
    """Replace campuses/buildings/rooms/assignments from one university
    export snapshot.

    Success: returns a summary dict of rows created/updated/ended.
    Failure: raises ValueError if the export is malformed.
    Spec rule: Domain Model (external systems); Non-goal 6 (CampusFix only
    reads housing data, never edits it).
    Injected: the university housing export (format TBD per C7); `now` for
    stamping the refresh and ending assignments no longer present.
    """
    raise NotImplementedError
