from __future__ import annotations

from django.http import JsonResponse
from django.utils import timezone

from campusfix.http import api_view, parse_json_body

from . import services


@api_view
def assign(request, work_order_number: str):
    body = parse_json_body(request)
    wo = services.assign_and_schedule(
        request.person,
        work_order_number,
        body.get("technician_id"),
        body.get("visit_window_start"),
        body.get("visit_window_end"),
        body.get("notice_given_at"),
        body.get("repair_order_exception_used", False),
        now=timezone.now(),
        expected_version=body.get("expected_version"),
    )
    return JsonResponse({"work_order_number": wo.work_order_number, "status": wo.status})
