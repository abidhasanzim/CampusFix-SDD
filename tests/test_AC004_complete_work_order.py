"""test_plan.md row AC-004 — Technician completes a documented repair
(FR-009, FR-010, FR-002).

Contract under test: POST /api/work-orders/{wo}/complete ->
apps.fieldwork.views.complete -> fieldwork.complete_work_order
(contracts.md section 1/2). Setup (an In-Progress work order linked to
two residents' requests) is arranged directly via the ORM.
"""
import json

import pytest
from django.utils import timezone

from apps.maintenance.models import MaintenanceRequest, WorkOrder, WorkRecord
from apps.notifications.models import Notification

from .conftest import auth_headers


@pytest.fixture
def in_progress_work_order(alice, bob, eli, maverick_village, room_101):
    now = timezone.now()
    request_alice = MaintenanceRequest.objects.create(
        tracking_number="CF-2026-00010",
        owner=alice,
        building=maverick_village,
        room=room_101,
        area_type=MaintenanceRequest.AREA_PRIVATE_BEDROOM,
        exact_location="Under the bathroom sink",
        description="Faucet drips constantly",
        request_state=MaintenanceRequest.STATE_ACKNOWLEDGED,
        version=1,
        created_at=now,
        updated_at=now,
    )
    request_bob = MaintenanceRequest.objects.create(
        tracking_number="CF-2026-00011",
        owner=bob,
        building=maverick_village,
        room=room_101,
        area_type=MaintenanceRequest.AREA_SHARED_SUITE,
        exact_location="Kitchen faucet",
        description="Same faucet, other side",
        request_state=MaintenanceRequest.STATE_ACKNOWLEDGED,
        version=1,
        created_at=now,
        updated_at=now,
    )
    work_order = WorkOrder.objects.create(
        work_order_number="WO-1187",
        category="PLUMBING",
        priority=WorkOrder.PRIORITY_NORMAL,
        status=WorkOrder.STATUS_IN_PROGRESS,
        assigned_technician=eli,
        version=2,
        created_at=now,
        updated_at=now,
    )
    work_order.requests.add(request_alice, request_bob)
    return work_order


@pytest.mark.django_db
def test_AC004(client, eli, in_progress_work_order):
    payload = {
        "diagnosis": "Washer worn",
        "work_performed": "Replaced washer",
        "labor_hours": "1.50",
        "parts": [["Washer", 1]],
        "tested_confirmed": True,
        "expected_version": 2,
    }

    response = client.post(
        f"/api/work-orders/{in_progress_work_order.work_order_number}/complete",
        data=json.dumps(payload),
        content_type="application/json",
        **auth_headers(eli),
    )

    assert response.status_code == 201, response.content

    assert WorkRecord.objects.filter(work_order=in_progress_work_order).count() == 1
    in_progress_work_order.refresh_from_db()
    assert in_progress_work_order.status == WorkOrder.STATUS_COMPLETED

    for request in in_progress_work_order.requests.all():
        request.refresh_from_db()
        assert request.request_state == MaintenanceRequest.STATE_COMPLETED
        assert Notification.objects.filter(
            recipient=request.owner, event="COMPLETED", tracking_number=request.tracking_number
        ).count() == 1
