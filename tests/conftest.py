"""Shared fixtures for the Project 2 acceptance tests (AC-001, AC-003,
AC-004, AC-012). Arrange-phase setup uses the Django ORM directly, since
the contract functions that would normally create this data
(`maintenance.create_request`, `maintenance.create_work_order`, ...) are
not implemented yet in Project 2 — only the action under test goes
through a contract route/function.
"""
from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Person, StaffRole
from apps.housing.models import Building, Campus, Room, RoomAssignment


def make_person(sso_subject: str, email: str, name: str) -> Person:
    User = get_user_model()
    user = User.objects.create_user(username=sso_subject, email=email)
    return Person.objects.create(user=user, sso_subject=sso_subject, uno_email=email, display_name=name)


def auth_headers(person: Person) -> dict:
    """Dev/test stub login (architecture C5): AttachPersonMiddleware reads
    this header. See contracts.md section 2, "Authentication note"."""
    return {"HTTP_X_DEBUG_PERSON_ID": str(person.id)}


@pytest.fixture
def dodge_campus(db):
    return Campus.objects.create(code=Campus.DODGE, name="Dodge")


@pytest.fixture
def maverick_village(dodge_campus):
    return Building.objects.create(campus=dodge_campus, name="Maverick Village")


@pytest.fixture
def room_101(maverick_village):
    return Room.objects.create(building=maverick_village, floor="1", room_number="101")


@pytest.fixture
def alice(room_101):
    person = make_person("alice-sso", "alice@unomaha.edu", "Alice Resident")
    RoomAssignment.objects.create(
        resident_sso_subject=person.sso_subject, room=room_101, start_date=date.today() - timedelta(days=30)
    )
    return person


@pytest.fixture
def bob(room_101):
    person = make_person("bob-sso", "bob@unomaha.edu", "Bob Resident")
    RoomAssignment.objects.create(
        resident_sso_subject=person.sso_subject, room=room_101, start_date=date.today() - timedelta(days=30)
    )
    return person


@pytest.fixture
def dana(dodge_campus):
    person = make_person("dana-sso", "dana@unomaha.edu", "Dana Supervisor")
    StaffRole.objects.create(person=person, role_type=StaffRole.SUPERVISOR, campus=dodge_campus)
    return person


@pytest.fixture
def eli(dodge_campus):
    person = make_person("eli-sso", "eli@unomaha.edu", "Eli Technician")
    StaffRole.objects.create(person=person, role_type=StaffRole.TECHNICIAN, campus=dodge_campus, trade="PLUMBING")
    return person
