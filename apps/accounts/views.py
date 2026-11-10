from __future__ import annotations

from django.http import JsonResponse
from django.utils import timezone

from campusfix.http import api_view, parse_json_body

from . import services


@api_view
def login(request):
    return_url = request.GET.get("return_url", "/")
    url = services.start_sso_login(return_url)
    return JsonResponse({"redirect_url": url})


@api_view
def login_callback(request):
    assertion = parse_json_body(request)
    person = services.complete_sso_login(assertion, now=timezone.now())
    return JsonResponse({"person_id": person.id}, status=200)
