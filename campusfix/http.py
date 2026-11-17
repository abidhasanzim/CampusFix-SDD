"""Thin plumbing shared by every app's views.py: turn the exceptions the
contract functions in contracts.md are documented to raise into HTTP
responses. Not a spec module — this has no business logic of its own.
"""
from __future__ import annotations

import json
from functools import wraps

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from campusfix.exceptions import ValidationError


def parse_json_body(request: HttpRequest) -> dict:
    if not request.body:
        return {}
    return json.loads(request.body)


def api_view(fn=None, *, public: bool = False):
    """Call a view and translate contract functions' documented failure
    modes into HTTP responses, per Task 1 step 3.

    `public=True` exempts a route from the NFR-10 "authentication
    required" check (AC-043) — only the SSO login/callback routes
    themselves need this, since every other route is a *protected* view.

    CSRF-exempt: these routes authenticate via the `X-Debug-Person-Id` stub
    header (or, once implemented, an SSO-issued bearer token), not a
    cookie-backed HTML form, so Django's cookie CSRF check does not apply.
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(request, *args, **kwargs):
            if not public and getattr(request, "person", None) is None:
                return JsonResponse({"error": "authentication_required"}, status=401)
            try:
                return fn(request, *args, **kwargs)
            except NotImplementedError as exc:
                message = str(exc) or f"{fn.__module__}.{fn.__name__} is not implemented yet"
                return JsonResponse({"error": "not_implemented", "message": message}, status=501)
            except ValidationError as exc:
                return JsonResponse(
                    {"error": "validation_error", "missing_fields": exc.missing_fields}, status=422
                )
            except PermissionError as exc:
                return JsonResponse({"error": "forbidden", "message": str(exc)}, status=403)

        return csrf_exempt(wrapper)

    if fn is not None:
        return decorator(fn)
    return decorator
