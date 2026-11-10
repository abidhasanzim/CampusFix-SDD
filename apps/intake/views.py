from __future__ import annotations

from django.http import JsonResponse
from django.utils import timezone

from campusfix.http import api_view, parse_json_body

from . import services


@api_view
def draft(request):
    form_data = parse_json_body(request)
    if request.method == "GET":
        saved = services.get_draft(request.person)
        return JsonResponse({"form_data": saved.form_data if saved else None})
    saved = services.save_draft(request.person, form_data, now=timezone.now())
    return JsonResponse({"saved_at": str(saved.updated_at)})


@api_view
def submit(request):
    form_data = parse_json_body(request)
    req = services.submit_request(request.person, form_data, now=timezone.now())
    return JsonResponse({"tracking_number": req.tracking_number, "status": req.request_state}, status=201)


@api_view
def phone_intake(request):
    body = parse_json_body(request)
    req = services.submit_phone_report(request.person, body.get("resident"), body, now=timezone.now())
    return JsonResponse({"tracking_number": req.tracking_number, "status": req.request_state}, status=201)


@api_view
def request_detail(request, tracking_number: str):
    detail = services.get_request_detail(request.person, tracking_number, now=timezone.now())
    return JsonResponse(detail)


@api_view
def entry_preference(request, tracking_number: str):
    body = parse_json_body(request)
    req = services.change_entry_preference(
        request.person, tracking_number, body.get("preference"), body.get("time_slots", []), now=timezone.now()
    )
    return JsonResponse({"tracking_number": req.tracking_number})


@api_view
def reopen(request, tracking_number: str):
    body = parse_json_body(request)
    req = services.reopen_request(
        request.person, tracking_number, body.get("description"), body.get("photo"), now=timezone.now()
    )
    return JsonResponse({"tracking_number": req.tracking_number, "status": req.request_state})


@api_view
def add_information(request, tracking_number: str):
    body = parse_json_body(request)
    req = services.add_information(
        request.person, tracking_number, body.get("comment"), body.get("photo"), now=timezone.now()
    )
    return JsonResponse({"tracking_number": req.tracking_number})


@api_view
def confirm_closure(request, tracking_number: str):
    req = services.confirm_closure(request.person, tracking_number, now=timezone.now())
    return JsonResponse({"tracking_number": req.tracking_number, "status": req.request_state})
