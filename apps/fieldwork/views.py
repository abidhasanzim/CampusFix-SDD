from __future__ import annotations

from django.http import JsonResponse
from django.utils import timezone

from campusfix.http import api_view, parse_json_body

from . import services


@api_view
def my_assignments(request):
    items = services.list_my_assignments(request.person)
    return JsonResponse({"work_orders": [wo.work_order_number for wo in items]})


@api_view
def start(request, work_order_number: str):
    body = parse_json_body(request)
    wo = services.start_work(request.person, work_order_number, now=timezone.now(), expected_version=body.get("expected_version"))
    return JsonResponse({"work_order_number": wo.work_order_number, "status": wo.status})


@api_view
def record_entry(request, work_order_number: str):
    body = parse_json_body(request)
    visit = services.record_entry(
        request.person, work_order_number, body.get("resident_present"),
        body.get("knock_and_announce_confirmed"), body.get("outcome"), now=timezone.now(),
    )
    return JsonResponse({"visit_id": visit.id}, status=201)


@api_view
def complete(request, work_order_number: str):
    body = parse_json_body(request)
    record = services.complete_work_order(
        request.person, work_order_number, body.get("diagnosis"), body.get("work_performed"),
        body.get("labor_hours"), body.get("parts", []), body.get("tested_confirmed"),
        now=timezone.now(), expected_version=body.get("expected_version"),
    )
    return JsonResponse({"work_record_id": record.id}, status=201)


@api_view
def hold(request, work_order_number: str):
    body = parse_json_body(request)
    record = services.place_on_hold(
        request.person, work_order_number, body.get("reason"), body.get("part_name", ""),
        body.get("next_action"), now=timezone.now(), expected_version=body.get("expected_version"),
    )
    return JsonResponse({"hold_id": record.id}, status=201)


@api_view
def no_access(request, work_order_number: str):
    body = parse_json_body(request)
    wo = services.record_no_access(
        request.person, work_order_number, body.get("resident_present"),
        now=timezone.now(), expected_version=body.get("expected_version"),
    )
    return JsonResponse({"work_order_number": wo.work_order_number, "status": wo.status})


@api_view
def transfer(request, work_order_number: str):
    body = parse_json_body(request)
    wo = services.request_transfer(
        request.person, work_order_number, body.get("target_trade"), body.get("reason"),
        now=timezone.now(), expected_version=body.get("expected_version"),
    )
    return JsonResponse({"work_order_number": wo.work_order_number, "status": wo.status})


@api_view
def clear_hold(request, work_order_number: str):
    body = parse_json_body(request)
    wo = services.clear_hold(
        request.person, work_order_number, body.get("resolution"),
        body.get("visit_window_start"), body.get("visit_window_end"),
        now=timezone.now(), expected_version=body.get("expected_version"),
    )
    return JsonResponse({"work_order_number": wo.work_order_number, "status": wo.status})


@api_view
def link_equipment(request, work_order_number: str):
    body = parse_json_body(request)
    wo = services.link_equipment(request.person, work_order_number, body.get("equipment_id"), now=timezone.now())
    return JsonResponse({"work_order_number": wo.work_order_number})
