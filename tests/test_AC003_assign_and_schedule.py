"""test_plan.md row AC-003 — Supervisor assigns a visit by trade and
workload (FR-008, FR-002).

Contract under test: POST /api/work-orders/{wo}/assign ->
apps.dispatch.views.assign -> dispatch.assign_and_schedule
(contracts.md section 1/2). Setup (an Acknowledged work order with no
technician) is arranged directly via the ORM, since the functions that
would normally create it are not implemented yet.
"""
import json
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.maintenance.models import MaintenanceRequest, WorkOrder
from apps.notifications.models import Notification

from .conftest import auth_headers


@pytest.fixture
def acknowledged_work_order(alice, maverick_village, room_101):
    now = timezone.now()
    request = MaintenanceRequest.objects.create(
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
    work_order = WorkOrder.objects.create(
        work_order_number="WO-1187",
        category="PLUMBING",
        priority=WorkOrder.PRIORITY_NORMAL,
        status=WorkOrder.STATUS_ACKNOWLEDGED,
        version=1,
        created_at=now,
        updated_at=now,
    )
    work_order.requests.add(request)
    return work_order


@pytest.mark.django_db
def test_AC003(client, dana, eli, acknowledged_work_order):
    now = timezone.now()
    payload = {
        "technician_id": eli.id,
        "visit_window_start": (now + timedelta(hours=30)).isoformat(),
        "visit_window_end": (now + timedelta(hours=31)).isoformat(),
        "notice_given_at": now.isoformat(),
        "repair_order_exception_used": False,
        "expected_version": 1,
    }

    response = client.post(
        f"/api/work-orders/{acknowledged_work_order.work_order_number}/assign",
        data=json.dumps(payload),
        content_type="application/json",
        **auth_headers(dana),
    )

    assert response.status_code == 200, response.content
    body = response.json()
    assert body["status"] == "SCHEDULED"

    owner = acknowledged_work_order.requests.get().owner
    assert Notification.objects.filter(recipient=owner, event="SCHEDULED").count() == 1
    assert Notification.objects.filter(recipient=eli).exists()
