"""Thin plumbing shared by every app's views.py: turn the exceptions the
contract functions in contracts.md are documented to raise into HTTP
responses. Not a spec module — this has no business logic of its own.
"""
from __future__ import annotations

import json
from functools import wraps

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt


def parse_json_body(request: HttpRequest) -> dict:
    if not request.body:
        return {}
    return json.loads(request.body)


def api_view(fn):
    """Call a view and translate a not-yet-implemented contract function
    into HTTP 501, per Task 1 step 3.

    CSRF-exempt: these routes authenticate via the `X-Debug-Person-Id` stub
    header (or, once implemented, an SSO-issued bearer token), not a
    cookie-backed HTML form, so Django's cookie CSRF check does not apply.
    """

    @wraps(fn)
    def wrapper(request, *args, **kwargs):
        try:
            return fn(request, *args, **kwargs)
        except NotImplementedError as exc:
            message = str(exc) or f"{fn.__module__}.{fn.__name__} is not implemented yet"
            return JsonResponse({"error": "not_implemented", "message": message}, status=501)

    return csrf_exempt(wrapper)
