"""Development/test stub login (architecture C5: "Development uses a stub
login"). Attaches `request.person` from a header so routes have something
to pass into their contract functions before real SSO session handling
(`accounts.services.complete_sso_login`) is implemented. This is not the
production authentication path and contains no domain business logic.
"""
from __future__ import annotations

from apps.accounts.models import Person


class AttachPersonMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        person_id = request.headers.get("X-Debug-Person-Id")
        request.person = Person.objects.filter(id=person_id).first() if person_id else None
        return self.get_response(request)
