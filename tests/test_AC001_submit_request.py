"""test_plan.md row AC-001 — Resident submits a valid request (FR-001, FR-014).

Contract under test: POST /api/requests -> apps.intake.views.submit ->
intake.submit_request (contracts.md section 1/2).
"""
import json
import re

import pytest

from apps.maintenance.models import MaintenanceRequest, Suggestion
from apps.notifications.models import Notification

from .conftest import auth_headers


@pytest.mark.django_db
def test_AC001(client, alice):
    payload = {
        "area_type": "PRIVATE_BEDROOM",
        "exact_location": "Under the bathroom sink",
        "description": "Faucet drips constantly",
        "entry_preference": {"preference": "PRESENT"},
        "photos": [],
    }

    response = client.post(
        "/api/requests", data=json.dumps(payload), content_type="application/json", **auth_headers(alice)
    )

    assert response.status_code == 201, response.content
    body = response.json()
    assert re.match(r"^CF-2026-\d{5}$", body["tracking_number"])
    assert body["status"] == "SUBMITTED"

    assert MaintenanceRequest.objects.count() == 1
    created = MaintenanceRequest.objects.get()
    assert created.owner_id == alice.id
    assert created.resident_urgency == MaintenanceRequest.URGENCY_NORMAL
    assert Suggestion.objects.filter(request=created).exists()
    assert Notification.objects.filter(recipient=alice, tracking_number=created.tracking_number).exists()
