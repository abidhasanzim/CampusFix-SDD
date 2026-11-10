"""Sign users in through SSO and identify each user's staff role.

Every function below raises NotImplementedError. No business logic is
implemented in Project 2 — this file only fixes the calling contract that
other modules and the REST routes build against.
"""
from __future__ import annotations

from datetime import datetime

from apps.accounts.models import Person, StaffRole
from apps.housing.models import Campus


def start_sso_login(return_url: str) -> str:
    """Build the redirect URL to the university SSO provider.

    Success: returns the provider's authorization URL as a string.
    Failure: none defined here; a misconfigured provider is a deployment error.
    Spec rule: NFR-10 (university SSO authenticates every user).
    Injected: the SSO provider client (SAML/OIDC, whichever UNO ITS supplies; C5).
    """
    raise NotImplementedError


def complete_sso_login(sso_assertion: dict, now: datetime) -> Person:
    """Validate the SSO provider's assertion and return the signed-in Person,
    creating the Person record on first sign-in.

    Success: returns the Person for the asserted SSO identity.
    Failure: raises PermissionError if the assertion cannot be validated.
    Spec rule: NFR-10; AC-043 (SSO required before protected data is shown).
    Injected: the SSO provider client; `now` for recording first-seen time.
    """
    raise NotImplementedError


def get_staff_roles(person: Person) -> list[StaffRole]:
    """Return every staff role granted to `person`.

    Success: returns a (possibly empty) list of StaffRole rows.
    Failure: none defined here.
    Spec rule: Domain Model Actors (Supervisor, Technician, Administrator,
    Front-desk staff); consumed by `access` for permission checks.
    Injected: none.
    """
    raise NotImplementedError


def get_campus_for_supervisor(person: Person) -> Campus:
    """Return the single campus a facilities supervisor is scoped to.

    Success: returns the Campus tied to the supervisor's StaffRole.
    Failure: raises LookupError if `person` holds no supervisor role.
    Spec rule: NFR-13 (campus-scoped configuration and queues).
    Injected: none.
    """
    raise NotImplementedError
