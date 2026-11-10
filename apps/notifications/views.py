from __future__ import annotations

from django.http import JsonResponse

from campusfix.http import api_view

from . import services


@api_view
def my_notifications(request):
    notifications = services.list_my_notifications(request.person)
    return JsonResponse({"notifications": [n.id for n in notifications]})
