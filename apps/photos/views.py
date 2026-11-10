from __future__ import annotations

from django.http import JsonResponse
from django.utils import timezone

from campusfix.http import api_view

from . import services


@api_view
def upload(request):
    uploaded = request.FILES.get("file")
    content_type = uploaded.content_type if uploaded else ""
    file_bytes = uploaded.read() if uploaded else b""
    campus = getattr(request.person, "campus", None)
    photo = services.upload_unattached(request.person, file_bytes, content_type, campus, now=timezone.now())
    return JsonResponse({"photo_id": photo.id}, status=201)


@api_view
def detail(request, photo_id: int):
    data = services.serve_photo(request.person, photo_id, now=timezone.now())
    return JsonResponse({"photo_id": photo_id, "bytes": len(data)})
