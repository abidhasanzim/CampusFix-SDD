from __future__ import annotations

from django.http import JsonResponse

from campusfix.http import api_view

from . import services


@api_view
def operational(request):
    campus = getattr(request.person, "campus", None)
    report = services.get_operational_report(
        request.person, campus,
        request.GET.get("period_start"), request.GET.get("period_end"),
        request.GET.get("building"), request.GET.get("category"),
    )
    return JsonResponse(report)


@api_view
def replacement_candidates(request):
    from django.utils import timezone

    campus = getattr(request.person, "campus", None)
    candidates = services.get_replacement_candidates(request.person, campus, now=timezone.now())
    return JsonResponse({"candidates": candidates})
