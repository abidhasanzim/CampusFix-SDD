"""test_plan.md row AC-012 — Incomplete submission does not create a ticket
(FR-001). The control sits in the same file, right after the rejection:
the identical request shape with every required field present is AC-001's
own payload, repeated here so the two cases are directly comparable.

Contract under test: POST /api/requests -> apps.intake.views.submit ->
intake.submit_request (contracts.md section 1/2).
"""
import json

import pytest

from apps.maintenance.models import MaintenanceRequest

from .conftest import auth_headers


@pytest.mark.django_db
def test_AC012(client, alice):
    payload = {
        "area_type": "PRIVATE_BEDROOM",
        "entry_preference": {"preference": "PRESENT"},
        # exact_location and description are both missing: the one way
        # this request is wrong.
    }

    response = client.post(
        "/api/requests", data=json.dumps(payload), content_type="application/json", **auth_headers(alice)
    )

    assert response.status_code == 422, response.content
    body = response.json()
    assert set(body["missing_fields"]) == {"exact_location", "description"}

    assert MaintenanceRequest.objects.count() == 0


@pytest.mark.django_db
def test_AC012_control(client, alice):
    """Control for AC-012: the same shape, with the two missing fields
    supplied, is accepted (mirrors AC-001)."""
    payload = {
        "area_type": "PRIVATE_BEDROOM",
        "exact_location": "Under the bathroom sink",
        "description": "Faucet drips constantly",
        "entry_preference": {"preference": "PRESENT"},
    }

    response = client.post(
        "/api/requests", data=json.dumps(payload), content_type="application/json", **auth_headers(alice)
    )

    assert response.status_code == 201, response.content
    assert MaintenanceRequest.objects.count() == 1
