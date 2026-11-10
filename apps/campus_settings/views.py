from __future__ import annotations

from django.http import JsonResponse
from django.utils import timezone

from apps.housing.models import Campus
from campusfix.http import api_view, parse_json_body

from . import services


@api_view
def config_detail(request, campus_code: str):
    campus = Campus(code=campus_code)
    if request.method == "PUT":
        changes = parse_json_body(request)
        config = services.update_config(request.person, campus, changes, now=timezone.now())
    else:
        config = services.get_config(campus)
    return JsonResponse({"campus": campus_code, "config": str(config)})
