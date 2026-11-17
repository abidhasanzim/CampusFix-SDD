"""Shared exception types that contracts.md's docstrings reference across
multiple modules without redefining per function (see contracts.md's
section 1 intro: "Two cross-cutting types recur below..."). `LookupError`
and `PermissionError` are Python builtins and need no definition here.
"""
from __future__ import annotations


class ValidationError(Exception):
    """Raised when a submission is missing required fields.

    Carries the missing field names so campusfix/http.py:api_view can
    report them under `missing_fields` (AC-012).
    """

    def __init__(self, missing_fields: list[str]):
        self.missing_fields = list(missing_fields)
        super().__init__(f"missing required fields: {', '.join(self.missing_fields)}")


class ConcurrencyError(Exception):
    """Raised when a record's stored version no longer matches the
    caller's `expected_version` (NFR-15)."""
