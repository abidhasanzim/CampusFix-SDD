from __future__ import annotations

from django.http import JsonResponse
from django.utils import timezone

from campusfix.http import api_view, parse_json_body

from . import services


@api_view
def triage_item(request, tracking_number: str):
    item = services.get_triage_item(request.person, tracking_number, now=timezone.now())
    return JsonResponse(item)


@api_view
def confirm(request, tracking_number: str):
    body = parse_json_body(request)
    wo = services.confirm_triage(
        request.person, tracking_number, body.get("category"), body.get("priority"),
        now=timezone.now(), expected_version=body.get("expected_version"),
    )
    return JsonResponse({"work_order_number": wo.work_order_number, "status": wo.status})


@api_view
def merge(request):
    body = parse_json_body(request)
    wo = services.merge_duplicates(
        request.person, body.get("tracking_numbers", []), body.get("category"), body.get("priority"),
        now=timezone.now(),
    )
    return JsonResponse({"work_order_number": wo.work_order_number}, status=201)


@api_view
def link(request, tracking_number: str):
    body = parse_json_body(request)
    wo = services.link_to_active_work_order(
        request.person, tracking_number, body.get("work_order_number"), now=timezone.now()
    )
    return JsonResponse({"work_order_number": wo.work_order_number})


@api_view
def close(request, tracking_number: str):
    body = parse_json_body(request)
    req = services.close_before_dispatch(request.person, tracking_number, body.get("reason"), now=timezone.now())
    return JsonResponse({"tracking_number": req.tracking_number, "status": req.request_state})


@api_view
def escalations(request):
    campus = getattr(request.person, "campus", None)
    items = services.list_escalations(request.person, campus)
    return JsonResponse({"escalations": [e.id for e in items]})
